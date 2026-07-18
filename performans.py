"""
performans.py — RAG pipeline performans ölçümü.

Tek komutla tekrarlanabilir rapor üretir:
    python performans.py                 # temel ölçüm + rapor
    python performans.py --karsilastir   # batch / top_k / chunk karşılaştırması da ekle
    python performans.py --llm-ornek 3   # kaç soruda LLM süresi ölçüleceği (varsayılan 5)

Raporlar:
    performans-raporu.json
    performans-raporu.md

Üretim veritabanına dokunmaz; ingestion ölçümü geçici bir SQLite dosyasına
yazar. Retrieval ve LLM ölçümleri mevcut veritabani.db üzerinden yapılır
(önce `python main.py --yukle` çalıştırılmış olmalıdır).
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import config
import database as db
import generator
import ingestion
import main
import retrieval
from degerlendirme import SORULAR

RAPOR_JSON = config.PROJE_KOKU / "performans-raporu.json"
RAPOR_MD = config.PROJE_KOKU / "performans-raporu.md"


def _temizle(metin: str) -> str:
    """Foundry hata mesajlarındaki null baytları temizler."""
    return metin.replace("\x00", "").strip()


def _sn(saniye: float) -> str:
    return f"{saniye:.2f}s"


def _ozet(sureler: list[float]) -> dict:
    if not sureler:
        return {"adet": 0, "toplam_s": 0.0, "ortalama_s": 0.0,
                "medyan_s": 0.0, "en_kotu_s": 0.0, "en_iyi_s": 0.0}
    return {
        "adet": len(sureler),
        "toplam_s": round(sum(sureler), 3),
        "ortalama_s": round(statistics.mean(sureler), 3),
        "medyan_s": round(statistics.median(sureler), 3),
        "en_kotu_s": round(max(sureler), 3),
        "en_iyi_s": round(min(sureler), 3),
    }


def _belge_ve_chunk_sayisi() -> dict:
    belgeler = sorted(config.BELGELER_KLASORU.glob("*.txt"))
    conn = db.baglan()
    try:
        db.tablolari_olustur(conn)
        chunk = db.kayit_sayisi(conn)
    finally:
        conn.close()
    return {
        "belge_sayisi": len(belgeler),
        "belge_dosyalari": [b.name for b in belgeler],
        "chunk_sayisi": chunk,
        "chunk_boyutu": config.CHUNK_BOYUTU,
        "chunk_ortusme": config.CHUNK_ORTUSME,
        "embed_batch": config.EMBED_BATCH,
        "top_k": config.TOP_K,
        "min_skor": config.MIN_SKOR,
        "llm_model": config.LLM_MODEL,
        "embed_model": config.EMBED_MODEL,
    }


def model_yukleme_olc(chat_gerekli: bool) -> tuple[dict, dict]:
    """Model yükleme sürelerini ayrı ayrı ölçer; kaynaklar dict'i döner."""
    print("\n[1/4] Model yukleme olculuyor...")
    t0 = time.perf_counter()
    from foundry_local_sdk import Configuration, FoundryLocalManager

    FoundryLocalManager.initialize(Configuration(app_name=config.APP_NAME))
    manager = FoundryLocalManager.instance
    sdk_s = time.perf_counter() - t0

    t1 = time.perf_counter()
    embedding_model = main.modeli_hazirla(manager, config.EMBED_MODEL)
    embed_s = time.perf_counter() - t1

    chat_s = 0.0
    chat_model = None
    chat_client = None
    if chat_gerekli:
        t2 = time.perf_counter()
        chat_model = main.modeli_hazirla(manager, config.LLM_MODEL)
        chat_s = time.perf_counter() - t2
        chat_client = chat_model.get_chat_client()
        # Isınma: ilk chat çağrısı bazen geçici hata verir
        for _ in range(2):
            try:
                chat_client.complete_chat(
                    [{"role": "user", "content": "Merhaba"}]
                )
                break
            except Exception:
                continue

    kaynaklar = {
        "embedding_model": embedding_model,
        "embedding_client": embedding_model.get_embedding_client(),
        "chat_model": chat_model,
        "chat_client": chat_client,
    }
    sureler = {
        "sdk_baslatma_s": round(sdk_s, 3),
        "embedding_yukleme_s": round(embed_s, 3),
        "chat_yukleme_s": round(chat_s, 3),
        "toplam_s": round(sdk_s + embed_s + chat_s, 3),
    }
    print(f"  SDK: {_sn(sdk_s)} | Embedding: {_sn(embed_s)} | "
          f"Chat: {_sn(chat_s)} | Toplam: {_sn(sureler['toplam_s'])}")
    return kaynaklar, sureler


def ingestion_olc(embedding_client) -> dict:
    """
    Chunking + embedding + SQLite yazımını geçici DB'ye ölçer.
    Üretim veritabani.db dosyasına dokunmaz.
    """
    print("\n[2/4] Ingestion olculuyor (gecici DB)...", flush=True)
    with tempfile.TemporaryDirectory() as tmp:
        gecici_db = Path(tmp) / "olcum.db"
        eski_db = config.DB_YOLU
        config.DB_YOLU = gecici_db
        try:
            t_chunk = time.perf_counter()
            chunklar = ingestion.belgeleri_yukle()
            chunking_s = time.perf_counter() - t_chunk

            metinler = [c["icerik"] for c in chunklar]
            t_embed = time.perf_counter()
            try:
                # Performans olcumunde daha fazla deneme; gecici Foundry
                # iptallerine karsi dayanikli olsun.
                vektorler = ingestion.embeddingleri_uret(
                    embedding_client, metinler, deneme_sayisi=5
                )
                embedding_s = time.perf_counter() - t_embed
                yontem = "batch"
                hata = None
            except Exception as batch_hata:
                # Batch basarisizsa tek tek embedding ile olc (daha yavas ama
                # genelde daha kararli); uretim DB'ye yine dokunulmaz.
                print(f"  Batch embedding basarisiz, tek tek deneniyor: "
                      f"{_temizle(str(batch_hata))}", flush=True)
                t_embed = time.perf_counter()
                try:
                    vektorler = []
                    for i, metin in enumerate(metinler, start=1):
                        for deneme in range(5):
                            try:
                                yanit = embedding_client.generate_embedding(metin)
                                vektorler.append(yanit.data[0].embedding)
                                break
                            except Exception:
                                if deneme == 4:
                                    raise
                        if i % 5 == 0 or i == len(metinler):
                            print(f"  {i}/{len(metinler)} tamamlandi...",
                                  flush=True)
                    embedding_s = time.perf_counter() - t_embed
                    yontem = "tektek"
                    hata = None
                except Exception as exc:
                    embedding_s = time.perf_counter() - t_embed
                    return {
                        "chunk_sayisi": len(chunklar),
                        "chunking_s": round(chunking_s, 3),
                        "embedding_s": round(embedding_s, 3),
                        "sqlite_yazma_s": 0.0,
                        "toplam_s": round(chunking_s + embedding_s, 3),
                        "chunk_basina_embedding_s": round(
                            embedding_s / max(len(chunklar), 1), 3
                        ),
                        "yontem": "basarisiz",
                        "hata": _temizle(str(exc)),
                    }

            for chunk, vektor in zip(chunklar, vektorler):
                chunk["embedding"] = vektor

            t_db = time.perf_counter()
            conn = db.baglan()
            try:
                eklenen = db.chunklari_degistir(conn, chunklar)
            finally:
                conn.close()
            db_s = time.perf_counter() - t_db
        finally:
            config.DB_YOLU = eski_db

    toplam = chunking_s + embedding_s + db_s
    sonuc = {
        "chunk_sayisi": eklenen,
        "chunking_s": round(chunking_s, 3),
        "embedding_s": round(embedding_s, 3),
        "sqlite_yazma_s": round(db_s, 3),
        "toplam_s": round(toplam, 3),
        "chunk_basina_embedding_s": round(embedding_s / max(eklenen, 1), 3),
        "yontem": yontem,
        "hata": None,
    }
    print(f"  Chunking: {_sn(chunking_s)} ({eklenen} chunk) | "
          f"Embedding ({yontem}): {_sn(embedding_s)} | SQLite: {_sn(db_s)} | "
          f"Toplam: {_sn(toplam)}", flush=True)
    return sonuc


def retrieval_olc(embedding_client) -> dict:
    """Değerlendirme setindeki tüm sorular için retrieval sürelerini ölçer."""
    print("\n[3/4] Retrieval olculuyor...")
    sureler = []
    detaylar = []
    for madde in SORULAR:
        t0 = time.perf_counter()
        chunklar = retrieval.en_alakali_chunklari_bul(
            embedding_client, madde["soru"]
        )
        sure = time.perf_counter() - t0
        sureler.append(sure)
        detaylar.append({
            "soru": madde["soru"],
            "tur": madde["tur"],
            "sure_s": round(sure, 3),
            "bulunan": len(chunklar),
            "en_iyi_skor": round(chunklar[0]["skor"], 3) if chunklar else 0.0,
        })
        print(f"  {_sn(sure):>8}  {madde['soru'][:60]}")

    ozet = _ozet(sureler)
    print(f"  Ortalama: {_sn(ozet['ortalama_s'])} | "
          f"En kotu: {_sn(ozet['en_kotu_s'])} | "
          f"En iyi: {_sn(ozet['en_iyi_s'])}")
    return {"ozet": ozet, "sorular": detaylar}


def llm_olc(embedding_client, chat_client, ornek_sayisi: int) -> dict:
    """Cevaplanabilir sorulardan bir örneklemle uçtan uca cevap süresini ölçer."""
    print(f"\n[4/4] LLM cevap uretimi olculuyor ({ornek_sayisi} soru)...",
          flush=True)
    cevaplanabilir = [m for m in SORULAR if m["tur"] == "cevaplanabilir"]
    ornekler = cevaplanabilir[:ornek_sayisi]

    sureler = []
    detaylar = []
    for madde in ornekler:
        t0 = time.perf_counter()
        hata = None
        cevap_uzunluk = 0
        kaynak_sayisi = 0
        for deneme in range(3):
            try:
                sonuc = generator.cevap_uret(
                    embedding_client, chat_client, madde["soru"]
                )
                cevap_uzunluk = len(sonuc.get("cevap") or "")
                kaynak_sayisi = len(sonuc.get("kaynaklar") or [])
                hata = None
                break
            except Exception as exc:
                hata = _temizle(str(exc))
                if deneme == 2:
                    break
                print(f"  Gecici LLM hatasi, tekrar ({deneme + 2}/3)...",
                      flush=True)
        sure = time.perf_counter() - t0
        sureler.append(sure)
        detaylar.append({
            "soru": madde["soru"],
            "sure_s": round(sure, 3),
            "cevap_uzunluk": cevap_uzunluk,
            "kaynak_sayisi": kaynak_sayisi,
            "hata": hata,
        })
        durum = "HATA" if hata else "OK"
        print(f"  {_sn(sure):>8}  [{durum}] {madde['soru'][:55]}", flush=True)

    ozet = _ozet(sureler)
    print(f"  Ortalama: {_sn(ozet['ortalama_s'])} | "
          f"En kotu: {_sn(ozet['en_kotu_s'])}", flush=True)
    return {"ozet": ozet, "sorular": detaylar}


def karsilastirma_olc(embedding_client) -> dict:
    """
    EMBED_BATCH, TOP_K, CHUNK_BOYUTU ve CHUNK_ORTUSME ayarlarını karşılaştırır.

    Embedding batch karşılaştırması tüm chunk'lar üzerinde yapılır (yazma yok).
    Chunk ayarları yalnızca chunk sayısını ve chunking süresini ölçer
    (yeniden embedding pahalı olduğu için tam re-index yapılmaz).
    TOP_K yalnızca retrieval süresini etkiler (skor hesabı aynı).
    """
    print("\n[+] Ayar karsilastirmasi olculuyor...")
    import retrieval as retrieval_mod

    # --- Chunk ayarlari (yalnızca parçalama) ---
    dosyalar = sorted(config.BELGELER_KLASORU.glob("*.txt"))
    metinler = [d.read_text(encoding="utf-8") for d in dosyalar]
    chunk_sonuclari = []
    for boyut, ortusme in ((200, 30), (300, 50), (400, 80)):
        t0 = time.perf_counter()
        adet = sum(
            len(ingestion.metni_parcala(m, chunk_boyutu=boyut, ortusme=ortusme))
            for m in metinler
        )
        sure = time.perf_counter() - t0
        chunk_sonuclari.append({
            "chunk_boyutu": boyut,
            "ortusme": ortusme,
            "chunk_sayisi": adet,
            "chunking_s": round(sure, 4),
        })
        print(f"  Chunk {boyut}/{ortusme}: {adet} chunk, {_sn(sure)}")

    # --- Embedding batch (temsilî alt küme; tam re-index pahalı) ---
    chunklar = ingestion.belgeleri_yukle()
    ornek_metinler = [c["icerik"] for c in chunklar[:4]]
    batch_sonuclari = []
    for batch in (1, 2, 4, 8):
        t0 = time.perf_counter()
        try:
            ingestion.embeddingleri_uret(
                embedding_client, ornek_metinler,
                batch_boyutu=batch, deneme_sayisi=5,
            )
            sure = time.perf_counter() - t0
            hata = None
        except Exception as exc:
            sure = time.perf_counter() - t0
            hata = str(exc)
        batch_sonuclari.append({
            "embed_batch": batch,
            "sure_s": round(sure, 3),
            "chunk_sayisi": len(ornek_metinler),
            "hata": _temizle(hata) if hata else None,
        })
        durum = f"HATA: {_temizle(hata)}" if hata else _sn(sure)
        print(f"  EMBED_BATCH={batch} ({len(ornek_metinler)} chunk): {durum}",
              flush=True)

    # --- TOP_K (aynı sorular, farklı k) ---
    ornek_sorular = [
        m["soru"] for m in SORULAR if m["tur"] == "cevaplanabilir"
    ][:8]
    topk_sonuclari = []
    for k in (1, 3, 5):
        sureler = []
        for soru in ornek_sorular:
            t0 = time.perf_counter()
            retrieval_mod.en_alakali_chunklari_bul(
                embedding_client, soru, top_k=k
            )
            sureler.append(time.perf_counter() - t0)
        ozet = _ozet(sureler)
        topk_sonuclari.append({"top_k": k, **ozet})
        print(f"  TOP_K={k}: ortalama {_sn(ozet['ortalama_s'])}")

    return {
        "chunk_ayarlari": chunk_sonuclari,
        "embed_batch": batch_sonuclari,
        "top_k": topk_sonuclari,
    }


def rapor_yaz(rapor: dict) -> None:
    def _temiz_yap(obj):
        if isinstance(obj, str):
            return _temizle(obj)
        if isinstance(obj, list):
            return [_temiz_yap(x) for x in obj]
        if isinstance(obj, dict):
            return {k: _temiz_yap(v) for k, v in obj.items()}
        return obj

    rapor = _temiz_yap(rapor)
    RAPOR_JSON.write_text(
        json.dumps(rapor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ortam = rapor["ortam"]
    yapilandirma = rapor["yapilandirma"]
    model = rapor["model_yukleme"]
    ing = rapor["ingestion"]
    ret = rapor["retrieval"]["ozet"]
    llm = rapor["llm"]["ozet"]

    satirlar = [
        "# Performans Raporu",
        "",
        f"Olusturma: {rapor['zaman']}",
        "",
        "## Ortam",
        "",
        f"- Platform: `{ortam['platform']}`",
        f"- Python: `{ortam['python']}`",
        f"- LLM: `{yapilandirma['llm_model']}`",
        f"- Embedding: `{yapilandirma['embed_model']}`",
        f"- Belge sayisi: **{yapilandirma['belge_sayisi']}**",
        f"- Chunk sayisi (uretim DB): **{yapilandirma['chunk_sayisi']}**",
        f"- Ayarlar: chunk={yapilandirma['chunk_boyutu']}/"
        f"{yapilandirma['chunk_ortusme']}, "
        f"batch={yapilandirma['embed_batch']}, "
        f"top_k={yapilandirma['top_k']}, "
        f"min_skor={yapilandirma['min_skor']}",
        "",
        "## Model Yukleme",
        "",
        f"| Asama | Sure |",
        f"|---|---|",
        f"| SDK baslatma | {_sn(model['sdk_baslatma_s'])} |",
        f"| Embedding yukleme | {_sn(model['embedding_yukleme_s'])} |",
        f"| Chat yukleme | {_sn(model['chat_yukleme_s'])} |",
        f"| **Toplam** | **{_sn(model['toplam_s'])}** |",
        "",
        "## Ingestion (gecici DB)",
        "",
        f"| Asama | Sure |",
        f"|---|---|",
        f"| Chunking ({ing['chunk_sayisi']} chunk) | {_sn(ing['chunking_s'])} |",
        f"| Embedding uretimi | {_sn(ing['embedding_s'])} |",
        f"| SQLite yazma | {_sn(ing['sqlite_yazma_s'])} |",
        f"| **Toplam** | **{_sn(ing['toplam_s'])}** |",
        f"| Chunk basina embedding | {_sn(ing['chunk_basina_embedding_s'])} |",
        f"| Yontem | {ing.get('yontem', 'batch')} |",
        "",
    ]
    if ing.get("hata"):
        satirlar += [
            f"> Ingestion embedding tamamlanamadi: `{ing['hata']}`",
            "",
        ]
    satirlar += [
        "## Retrieval",
        "",
        f"- Soru adedi: {ret['adet']}",
        f"- Ortalama: **{_sn(ret['ortalama_s'])}**",
        f"- Medyan: {_sn(ret['medyan_s'])}",
        f"- En iyi: {_sn(ret['en_iyi_s'])}",
        f"- En kotu: **{_sn(ret['en_kotu_s'])}**",
        f"- Toplam: {_sn(ret['toplam_s'])}",
        "",
        "## LLM Cevap Uretimi",
        "",
        f"- Ornek adedi: {llm['adet']}",
        f"- Ortalama: **{_sn(llm['ortalama_s'])}**",
        f"- Medyan: {_sn(llm['medyan_s'])}",
        f"- En iyi: {_sn(llm['en_iyi_s'])}",
        f"- En kotu: **{_sn(llm['en_kotu_s'])}**",
        f"- Toplam: {_sn(llm['toplam_s'])}",
        "",
    ]

    if rapor.get("karsilastirma"):
        k = rapor["karsilastirma"]
        satirlar += [
            "## Ayar Karsilastirmasi",
            "",
            "### Chunk boyutu / ortusme",
            "",
            "| Chunk | Ortusme | Chunk sayisi | Chunking |",
            "|---|---|---|---|",
        ]
        for c in k["chunk_ayarlari"]:
            satirlar.append(
                f"| {c['chunk_boyutu']} | {c['ortusme']} | "
                f"{c['chunk_sayisi']} | {_sn(c['chunking_s'])} |"
            )
        satirlar += [
            "",
            "### EMBED_BATCH",
            "",
            "| Batch | Sure | Durum |",
            "|---|---|---|",
        ]
        for b in k["embed_batch"]:
            durum = "HATA" if b["hata"] else "OK"
            satirlar.append(
                f"| {b['embed_batch']} | {_sn(b['sure_s'])} | {durum} |"
            )
        satirlar += [
            "",
            "### TOP_K (retrieval ortalamasi)",
            "",
            "| top_k | Ortalama | En kotu |",
            "|---|---|---|",
        ]
        for t in k["top_k"]:
            satirlar.append(
                f"| {t['top_k']} | {_sn(t['ortalama_s'])} | "
                f"{_sn(t['en_kotu_s'])} |"
            )
        satirlar.append("")

    satirlar += [
        "## Notlar",
        "",
        "- Ingestion olcumu gecici bir SQLite dosyasina yazildi; "
        "`veritabani.db` degistirilmedi.",
        "- Retrieval ve LLM olcumleri mevcut uretim indeksini kullanir.",
        "- Ilk chat cagrisi icin isinma turu yapildi; raporlanan LLM "
        "sureleri isinma sonrasi degerlerdir.",
        "",
    ]

    RAPOR_MD.write_text("\n".join(satirlar), encoding="utf-8")
    print(f"\nRapor yazildi:\n  {RAPOR_MD}\n  {RAPOR_JSON}")


def ana() -> None:
    parser = argparse.ArgumentParser(description="RAG performans olcumu")
    parser.add_argument(
        "--karsilastir",
        action="store_true",
        help="EMBED_BATCH, TOP_K ve chunk ayarlarini karsilastir",
    )
    parser.add_argument(
        "--llm-ornek",
        type=int,
        default=5,
        help="LLM suresi icin olculecek cevaplanabilir soru sayisi (varsayilan 5)",
    )
    args = parser.parse_args()

    if not main.veritabani_hazir_mi():
        print("HATA: Uretim veritabani bos. Once su komutu calistirin:")
        print("  python main.py --yukle")
        sys.exit(1)

    yapilandirma = _belge_ve_chunk_sayisi()
    rapor = {
        "zaman": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "ortam": {
            "platform": platform.platform(),
            "python": platform.python_version(),
            "machine": platform.machine(),
        },
        "yapilandirma": yapilandirma,
    }

    kaynaklar, model_sureleri = model_yukleme_olc(chat_gerekli=True)
    try:
        rapor["model_yukleme"] = model_sureleri
        rapor["ingestion"] = ingestion_olc(kaynaklar["embedding_client"])
        if rapor["ingestion"].get("hata"):
            print(f"  UYARI: Ingestion olcumu kismi kaldi: "
                  f"{rapor['ingestion']['hata']}", flush=True)
            print("  Retrieval/LLM olcumune uretim DB ile devam ediliyor.",
                  flush=True)
        rapor["retrieval"] = retrieval_olc(kaynaklar["embedding_client"])
        rapor["llm"] = llm_olc(
            kaynaklar["embedding_client"],
            kaynaklar["chat_client"],
            ornek_sayisi=max(1, args.llm_ornek),
        )
        if args.karsilastir:
            rapor["karsilastirma"] = karsilastirma_olc(
                kaynaklar["embedding_client"]
            )
        else:
            rapor["karsilastirma"] = None
    finally:
        main.modelleri_bosalt(kaynaklar)

    rapor_yaz(rapor)
    print("\nOzet:")
    print(f"  Model yukleme : {_sn(rapor['model_yukleme']['toplam_s'])}")
    print(f"  Ingestion     : {_sn(rapor['ingestion']['toplam_s'])}")
    print(f"  Retrieval ort : {_sn(rapor['retrieval']['ozet']['ortalama_s'])}")
    print(f"  LLM ort       : {_sn(rapor['llm']['ozet']['ortalama_s'])}")


if __name__ == "__main__":
    ana()
