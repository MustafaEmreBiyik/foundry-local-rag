"""
main.py — RAG Asistanı ana giriş noktası (Microsoft Foundry Local).

Çalıştırma:
    python main.py              (etkileşimli CLI başlatır)
    python main.py --yukle      (belgeleri yeniden yükler ve çıkar)
"""

import argparse
import sys

# Windows konsolu varsayılan olarak cp1254 kullanır; modelin ürettiği
# Türkçe dışı karakterler programı çökertmesin diye UTF-8'e geçilir.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from foundry_local_sdk import Configuration, FoundryLocalManager

import config
import database as db
import ingestion
import generator


def _indirme_ilerlemesi(model_adi: str):
    def ilerleme(yuzde: float) -> None:
        print(f"\r{model_adi} indiriliyor: %{yuzde:.1f}", end="", flush=True)

    return ilerleme


def modeli_hazirla(manager, model_adi: str):
    model = manager.catalog.get_model(model_adi)
    model.download(_indirme_ilerlemesi(model_adi))
    print()
    model.load()
    return model


def foundry_hazirla(chat_gerekli: bool = True) -> dict:
    """Foundry Local SDK'yı başlatır ve gerekli yerel modelleri yükler."""
    try:
        FoundryLocalManager.initialize(Configuration(app_name=config.APP_NAME))
        manager = FoundryLocalManager.instance

        embedding_model = modeli_hazirla(manager, config.EMBED_MODEL)
        kaynaklar = {
            "embedding_model": embedding_model,
            "embedding_client": embedding_model.get_embedding_client(),
            "chat_model": None,
            "chat_client": None,
        }

        if chat_gerekli:
            chat_model = modeli_hazirla(manager, config.LLM_MODEL)
            kaynaklar["chat_model"] = chat_model
            kaynaklar["chat_client"] = chat_model.get_chat_client()
    except Exception as hata:
        print(f"HATA: Foundry Local hazırlanamadı: {hata}")
        print("Kontrol listesi:")
        print("  1. Bağımlılıklar kurulu mu? -> pip install -r requirements.txt")
        print("  2. İlk model indirmesi için internet bağlantısı var mı?")
        print(f"  3. Model adları katalogda mevcut mu? "
              f"({config.LLM_MODEL}, {config.EMBED_MODEL})")
        sys.exit(1)

    print("Foundry Local hazır!")
    return kaynaklar


def modelleri_bosalt(kaynaklar: dict) -> None:
    for anahtar in ("chat_model", "embedding_model"):
        model = kaynaklar.get(anahtar)
        if model is not None and model.is_loaded:
            model.unload()


def veritabani_hazir_mi() -> bool:
    conn = db.baglan()
    db.tablolari_olustur(conn)
    sayi = db.kayit_sayisi(conn)
    conn.close()
    return sayi > 0


def cli_calistir(embedding_client, chat_client) -> None:
    print("\nRAG Asistani hazir! Cikmak icin 'exit' yazin.\n")

    while True:
        try:
            soru = input("Sorunuz: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nCikiliyor...")
            break

        if soru.lower() in ("exit", "quit", "q"):
            print("Gorusuruz!")
            break

        if not soru:
            continue

        print("Dusunuyor...")
        try:
            sonuc = generator.cevap_uret(
                embedding_client,
                chat_client,
                soru,
            )
        except Exception as hata:
            print(f"\nHATA: Cevap uretilemedi: {hata}")
            print("Model yuklu ve calisiyor mu kontrol edin, sonra tekrar deneyin.\n")
            continue

        print(f"\nCevap:\n{sonuc['cevap']}")
        if sonuc["kaynaklar"]:
            print("\nKaynaklar:")
            for i, kaynak in enumerate(sonuc["kaynaklar"], start=1):
                print(f"  {i}. {kaynak['kaynak']} (benzerlik: {kaynak['skor']:.2f})")
                print(f"     \"{kaynak['alinti']}\"")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Local RAG Asistani")
    parser.add_argument(
        "--yukle",
        action="store_true",
        help="Belgeleri yeniden yukle (eski kayitlari siler)"
    )
    args = parser.parse_args()

    kaynaklar = foundry_hazirla(chat_gerekli=not args.yukle)
    try:
        if args.yukle:
            try:
                ingestion.belgeleri_isle_ve_kaydet(kaynaklar["embedding_client"])
            except ingestion.IngestionHatasi as hata:
                print(f"HATA: {hata}")
                sys.exit(1)
            return

        if not veritabani_hazir_mi():
            print("Veritabani bos. Once belgeleri yukleyin:")
            print("  python main.py --yukle")
            return

        cli_calistir(
            kaynaklar["embedding_client"],
            kaynaklar["chat_client"],
        )
    finally:
        modelleri_bosalt(kaynaklar)


if __name__ == "__main__":
    main()
