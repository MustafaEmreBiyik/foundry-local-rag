"""
ingestion.py — Belge yükleme, parçalama ve embedding üretimi.

Chunking paragraf sınırlarına saygı gösterir ve ardışık chunk'lar
arasında kelime örtüşmesi bırakır; böylece bir bilginin chunk sınırında
ikiye bölünüp kaybolması engellenir.

Yeniden yükleme atomiktir: tüm embedding'ler başarıyla üretilmeden
mevcut veritabanı kayıtlarına dokunulmaz.
"""

import re
from pathlib import Path

import config
import database as db


class IngestionHatasi(Exception):
    """Belge yükleme sürecindeki kullanıcıya gösterilebilir hatalar."""


def metni_parcala(
    metin: str,
    chunk_boyutu: int = config.CHUNK_BOYUTU,
    ortusme: int = config.CHUNK_ORTUSME,
) -> list[str]:
    """
    Metni paragraf sınırlarını koruyarak örtüşmeli chunk'lara böler.

    Paragraflar chunk dolana kadar bir araya toplanır; sığmayan paragraf
    yeni chunk başlatır ve önceki chunk'ın son `ortusme` kelimesi bağlam
    kopmasın diye yeni chunk'ın başına eklenir. Tek başına chunk
    boyutunu aşan paragraflar kelime sınırından örtüşmeli bölünür.
    """
    paragraflar = [p for p in re.split(r"\n\s*\n", metin) if p.strip()]

    chunklar: list[str] = []
    aktif: list[str] = []

    for paragraf in paragraflar:
        kelimeler = paragraf.split()

        if aktif and len(aktif) + len(kelimeler) > chunk_boyutu:
            chunklar.append(" ".join(aktif))
            aktif = aktif[-ortusme:] if ortusme else []

        aktif.extend(kelimeler)

        while len(aktif) > chunk_boyutu:
            chunklar.append(" ".join(aktif[:chunk_boyutu]))
            aktif = aktif[chunk_boyutu - ortusme:] if ortusme else aktif[chunk_boyutu:]

    if aktif:
        son = " ".join(aktif)
        # Kuyruk yalnızca örtüşmeden ibaretse önceki chunk'ta zaten var
        if not chunklar or not chunklar[-1].endswith(son):
            chunklar.append(son)

    return chunklar


def belgeleri_yukle(klasor: Path = config.BELGELER_KLASORU) -> list[dict]:
    """
    Klasördeki .txt belgeleri okuyup chunk listesine dönüştürür.

    Her chunk'a kaynak dosya adı ve dosya içindeki sıra numarası eklenir.
    """
    if not klasor.is_dir():
        raise IngestionHatasi(
            f"Belge klasörü bulunamadı: {klasor}\n"
            f"Klasörü oluşturup içine .txt belgelerinizi koyun."
        )

    txt_dosyalari = sorted(klasor.glob("*.txt"))
    if not txt_dosyalari:
        raise IngestionHatasi(
            f"Belge klasöründe .txt dosyası yok: {klasor}\n"
            f"En az bir .txt belgesi ekleyip tekrar deneyin."
        )

    tum_chunklar = []
    for dosya in txt_dosyalari:
        try:
            metin = dosya.read_text(encoding="utf-8")
        except UnicodeDecodeError as hata:
            raise IngestionHatasi(
                f"'{dosya.name}' UTF-8 olarak okunamadı: {hata}\n"
                f"Dosyayı UTF-8 kodlamasıyla kaydedip tekrar deneyin."
            ) from hata
        except OSError as hata:
            raise IngestionHatasi(
                f"'{dosya.name}' okunamadı: {hata}"
            ) from hata

        for sira, parca in enumerate(metni_parcala(metin)):
            tum_chunklar.append({
                "kaynak": dosya.name,
                "sira": sira,
                "icerik": parca,
            })

    if not tum_chunklar:
        raise IngestionHatasi(
            f"Belgeler bulundu fakat hepsi boş: {klasor}\n"
            f"Belgelerin metin içerdiğinden emin olun."
        )

    return tum_chunklar


def embeddingleri_uret(
    embedding_client,
    metinler: list[str],
    batch_boyutu: int = config.EMBED_BATCH,
    deneme_sayisi: int = 3,
) -> list[list[float]]:
    """
    Metin listesinin embedding'lerini batch'ler halinde üretir.

    Foundry Local, model yüklendikten sonraki ilk çağrılarda geçici
    "Operation was cancelled" hatası verebildiği için her batch birkaç
    kez denenir.
    """
    vektorler: list[list[float]] = []
    for i in range(0, len(metinler), batch_boyutu):
        batch = metinler[i:i + batch_boyutu]

        for deneme in range(deneme_sayisi):
            try:
                yanit = embedding_client.generate_embeddings(batch)
                break
            except Exception:
                if deneme == deneme_sayisi - 1:
                    raise
                print(f"  Gecici hata, batch tekrar deneniyor "
                      f"({deneme + 2}/{deneme_sayisi})...")

        vektorler.extend(veri.embedding for veri in yanit.data)
        print(f"  {min(i + batch_boyutu, len(metinler))}/{len(metinler)} tamamlandi...")
    return vektorler


def belgeleri_isle_ve_kaydet(embedding_client) -> int:
    """
    Belgeleri okur, embedding üretir ve veritabanına kaydeder.

    Önce tüm embedding'ler bellekte hazırlanır; ancak hepsi başarılı
    olursa eski kayıtlar tek transaction içinde yenileriyle değiştirilir.
    Böylece işlem yarıda kesilirse mevcut indeks bozulmaz.
    """
    chunklar = belgeleri_yukle()
    print(f"{len(chunklar)} chunk bulundu. Embedding uretiliyor...")

    try:
        vektorler = embeddingleri_uret(
            embedding_client,
            [c["icerik"] for c in chunklar],
        )
    except Exception as hata:
        raise IngestionHatasi(
            f"Embedding üretilemedi: {hata}\n"
            f"Mevcut veritabanı kayıtları korundu."
        ) from hata

    for chunk, vektor in zip(chunklar, vektorler):
        chunk["embedding"] = vektor

    conn = db.baglan()
    try:
        eklenen = db.chunklari_degistir(conn, chunklar)
    finally:
        conn.close()

    print(f"Tamamlandi. {eklenen} chunk veritabanina kaydedildi.")
    return eklenen
