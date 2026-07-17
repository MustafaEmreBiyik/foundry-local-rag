"""
degerlendirme.py — RAG kalite değerlendirme seti.

Gerçek embedding modeliyle retrieval isabetini ve "bilgi yok"
davranışını ölçer. Varsayılan olarak yalnızca embedding modeli kullanır
(hızlı); --llm bayrağıyla cevaplar da üretilir.

Çalıştırma:
    python degerlendirme.py          (yalnızca retrieval değerlendirmesi)
    python degerlendirme.py --llm    (LLM cevaplarıyla birlikte)
"""

import argparse
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import generator
import main
import retrieval

# Her soru: tur = "cevaplanabilir" (beklenen_kaynaklar'dan en az biri
# dönmeli) veya "cevaplanamaz" (retrieval boş dönmeli, sistem reddetmeli).
SORULAR = [
    # Belgelerden cevaplanabilir sorular
    {"soru": "RAG'ın üç temel adımı nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["rag_kavrami.txt"]},
    {"soru": "Cosine similarity hangi değer aralığında sonuç verir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["rag_kavrami.txt"]},
    {"soru": "SQLite nedir ve hangi projeler için uygundur?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["veritabani_temelleri.txt"]},
    {"soru": "Python'da temel veri tipleri nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["python_temelleri.txt"]},
    {"soru": "Makine öğrenmesinin üç temel yöntemi nedir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["yapay_zeka_temelleri.txt"]},
    {"soru": "Foundry Local kullanmanın avantajları nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["foundry_local_kullanimi.txt"]},
    {"soru": "Embedding nedir?",
     "tur": "cevaplanabilir",
     "beklenen_kaynaklar": ["yapay_zeka_temelleri.txt", "rag_kavrami.txt"]},
    # Belgelerde olmayan, tamamen ilgisiz sorular
    {"soru": "Mars'taki en yüksek dağın adı nedir?", "tur": "cevaplanamaz"},
    {"soru": "2022 Dünya Kupası'nı hangi ülke kazandı?", "tur": "cevaplanamaz"},
    {"soru": "En iyi kek tarifi nedir?", "tur": "cevaplanamaz"},
    # Sınırda sorular: teknik ama belgelerde cevabı yok
    {"soru": "JavaScript'te asenkron programlama nasıl yapılır?", "tur": "cevaplanamaz"},
    {"soru": "Kuantum bilgisayarlar nasıl çalışır?", "tur": "cevaplanamaz"},
]


def degerlendir(kaynaklar: dict, llm_kullan: bool) -> None:
    basarili = 0
    sonuc_satirlari = []

    for i, madde in enumerate(SORULAR, start=1):
        soru = madde["soru"]
        chunklar = retrieval.en_alakali_chunklari_bul(
            kaynaklar["embedding_client"], soru
        )
        bulunan_kaynaklar = [c["kaynak"] for c in chunklar]
        en_iyi_skor = chunklar[0]["skor"] if chunklar else 0.0

        if madde["tur"] == "cevaplanabilir":
            gecti = any(k in bulunan_kaynaklar for k in madde["beklenen_kaynaklar"])
            beklenti = f"kaynak: {'/'.join(madde['beklenen_kaynaklar'])}"
        else:
            gecti = not chunklar
            beklenti = "reddedilmeli"

        if gecti:
            basarili += 1

        durum = "GECTI " if gecti else "KALDI "
        sonuc_satirlari.append(
            f"{durum} [{i:2}] ({madde['tur'][:12]:<12}) skor={en_iyi_skor:.3f}  "
            f"{soru}\n"
            f"        beklenen: {beklenti} | bulunan: "
            f"{', '.join(dict.fromkeys(bulunan_kaynaklar)) or '(bos)'}"
        )

        if llm_kullan:
            cevap = generator.cevap_uret(
                kaynaklar["embedding_client"],
                kaynaklar["chat_client"],
                soru,
            )["cevap"]
            sonuc_satirlari.append(f"        cevap: {cevap[:150]}")

    print("\n=== Degerlendirme Sonuclari ===\n")
    print("\n".join(sonuc_satirlari))
    print(f"\nToplam: {basarili}/{len(SORULAR)} soru basarili "
          f"(%{100 * basarili / len(SORULAR):.0f})")

    cevaplanabilir = [m for m in SORULAR if m["tur"] == "cevaplanabilir"]
    print(f"  - Cevaplanabilir: {len(cevaplanabilir)} soru (retrieval isabeti)")
    print(f"  - Cevaplanamaz : {len(SORULAR) - len(cevaplanabilir)} soru "
          f"(dogru reddetme)")


def ana() -> None:
    parser = argparse.ArgumentParser(description="RAG kalite degerlendirmesi")
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Retrieval'a ek olarak LLM cevaplarini da uret"
    )
    args = parser.parse_args()

    kaynaklar = main.foundry_hazirla(chat_gerekli=args.llm)
    try:
        degerlendir(kaynaklar, llm_kullan=args.llm)
    finally:
        main.modelleri_bosalt(kaynaklar)


if __name__ == "__main__":
    ana()
