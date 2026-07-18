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
# dönmeli), "cevaplanamaz" (tamamen ilgisiz; reddedilmeli) veya
# "sinirda" (teknik ama belgelerde cevabı yok; yine reddedilmeli).
SORULAR = [
    # --- Cevaplanabilir sorular (15): her belgeden en az bir soru ---
    {"soru": "RAG'ın üç temel adımı nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["rag_kavrami.txt"]},
    {"soru": "SQLite nedir ve hangi projeler için uygundur?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["veritabani_temelleri.txt"]},
    {"soru": "Python'da temel veri tipleri nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["python_temelleri.txt"]},
    {"soru": "Makine öğrenmesinin üç temel yöntemi nedir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["yapay_zeka_temelleri.txt"]},
    {"soru": "Foundry Local kullanmanın avantajları nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["foundry_local_kullanimi.txt"]},
    {"soru": "Git'te branch (dal) nedir ve ne işe yarar?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["git_versiyon_kontrolu.txt"]},
    {"soru": "HTTP metotları nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["web_gelistirme_temelleri.txt"]},
    {"soru": "Phishing saldırısı nedir ve nasıl korunurum?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["siber_guvenlik_temelleri.txt"]},
    {"soru": "İkili arama (binary search) algoritması nasıl çalışır?",
     "tur": "cevaplanabilir",
     "beklenen_kaynaklar": ["veri_yapilari_algoritmalar.txt"]},
    {"soru": "DNS ne işe yarar?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["ag_temelleri.txt"]},
    {"soru": "İşlem (process) ile iş parçacığı (thread) arasındaki fark nedir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["isletim_sistemleri.txt"]},
    {"soru": "IaaS, PaaS ve SaaS arasındaki farklar nelerdir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["bulut_bilisim.txt"]},
    {"soru": "Aşırı öğrenme (overfitting) nedir ve nasıl önlenir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["derin_ogrenme.txt"]},
    {"soru": "Few-shot prompt tekniği nedir?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["prompt_muhendisligi.txt"]},
    {"soru": "Linux'ta dosyaları listelemek için hangi komut kullanılır?",
     "tur": "cevaplanabilir", "beklenen_kaynaklar": ["linux_komut_satiri.txt"]},
    # --- Tamamen ilgisiz sorular (10): reddedilmeli ---
    {"soru": "Mars'taki en yüksek dağın adı nedir?", "tur": "cevaplanamaz"},
    {"soru": "2022 Dünya Kupası'nı hangi ülke kazandı?", "tur": "cevaplanamaz"},
    {"soru": "En iyi kek tarifi nedir?", "tur": "cevaplanamaz"},
    {"soru": "Kuantum bilgisayarlar nasıl çalışır?", "tur": "cevaplanamaz"},
    {"soru": "İstanbul'da gezilecek en güzel yerler nerelerdir?",
     "tur": "cevaplanamaz"},
    {"soru": "D vitamini eksikliğinin belirtileri nelerdir?",
     "tur": "cevaplanamaz"},
    {"soru": "Gitar çalmayı öğrenmek ne kadar sürer?", "tur": "cevaplanamaz"},
    {"soru": "Osmanlı İmparatorluğu ne zaman kuruldu?", "tur": "cevaplanamaz"},
    {"soru": "Kahve demleme yöntemleri nelerdir?", "tur": "cevaplanamaz"},
    {"soru": "Maratona nasıl hazırlanılır?", "tur": "cevaplanamaz"},
    # --- Sınırda sorular (5): teknik ama belgelerde cevabı yok ---
    {"soru": "Rust dilinde ownership kavramı nedir?", "tur": "sinirda"},
    {"soru": "React ile bileşen (component) nasıl yazılır?", "tur": "sinirda"},
    {"soru": "MongoDB'de doküman nasıl sorgulanır?", "tur": "sinirda"},
    {"soru": "Kubernetes'te pod nedir?", "tur": "sinirda"},
    {"soru": "Regex ile e-posta adresi nasıl doğrulanır?", "tur": "sinirda"},
]


HEDEF_YUZDE = 90  # P7 tamamlanma ölçütü: her kategoride en az %90 başarı


def degerlendir(kaynaklar: dict, llm_kullan: bool) -> None:
    sonuc_satirlari = []
    kategori_sayilari = {}   # tur -> [basarili, toplam]

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

        sayilar = kategori_sayilari.setdefault(madde["tur"], [0, 0])
        sayilar[1] += 1
        if gecti:
            sayilar[0] += 1

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

    basarili = sum(s[0] for s in kategori_sayilari.values())
    print(f"\nToplam: {basarili}/{len(SORULAR)} soru basarili "
          f"(%{100 * basarili / len(SORULAR):.0f})")

    etiketler = {
        "cevaplanabilir": "Cevaplanabilir (retrieval isabeti)",
        "cevaplanamaz": "Ilgisiz (dogru reddetme)",
        "sinirda": "Sinirda (dogru reddetme)",
    }
    hepsi_hedefte = True
    for tur, etiket in etiketler.items():
        if tur not in kategori_sayilari:
            continue
        dogru, toplam = kategori_sayilari[tur]
        yuzde = 100 * dogru / toplam
        isaret = "OK   " if yuzde >= HEDEF_YUZDE else "DUSUK"
        if yuzde < HEDEF_YUZDE:
            hepsi_hedefte = False
        print(f"  {isaret} {etiket}: {dogru}/{toplam} (%{yuzde:.0f})")

    print(f"\nHedef: her kategoride en az %{HEDEF_YUZDE} -> "
          f"{'SAGLANDI' if hepsi_hedefte else 'SAGLANAMADI'}")


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
