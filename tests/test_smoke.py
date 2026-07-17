"""
Gerçek Foundry Local modelleriyle uçtan uca smoke testi.

Normal test paketinden ayrıdır (pytest.ini: addopts = -m "not smoke").
Çalıştırmak için:
    python -m pytest -m smoke -v

Gereksinimler: modeller indirilmiş olmalı ve veritabanı dolu olmalı
(python main.py --yukle).
"""

import pytest

import database as db
import generator
import main

pytestmark = pytest.mark.smoke


@pytest.fixture(scope="module")
def foundry_kaynaklari():
    kaynaklar = main.foundry_hazirla(chat_gerekli=True)

    # Model yüklendikten sonraki ilk chat çağrısı bazen geçici olarak
    # "Operation was cancelled" hatası veriyor; ısınma turuyla aşılır.
    for _ in range(2):
        try:
            kaynaklar["chat_client"].complete_chat(
                [{"role": "user", "content": "Merhaba"}]
            )
            break
        except Exception:
            continue

    yield kaynaklar
    main.modelleri_bosalt(kaynaklar)


def _veritabani_dolu() -> bool:
    conn = db.baglan()
    try:
        db.tablolari_olustur(conn)
        return db.kayit_sayisi(conn) > 0
    finally:
        conn.close()


def _cevap_uret_denemeli(kaynaklar, soru, deneme_sayisi=3):
    """Foundry Local'ın geçici 'Operation was cancelled' hatasına karşı
    cevap üretimini birkaç kez dener."""
    for deneme in range(deneme_sayisi):
        try:
            return generator.cevap_uret(
                kaynaklar["embedding_client"],
                kaynaklar["chat_client"],
                soru,
            )
        except Exception:
            if deneme == deneme_sayisi - 1:
                raise


def test_cevaplanabilir_soru_kaynakla_cevaplanir(foundry_kaynaklari):
    if not _veritabani_dolu():
        pytest.skip("Veritabanı boş; önce 'python main.py --yukle' çalıştırın.")

    sonuc = _cevap_uret_denemeli(foundry_kaynaklari, "RAG nedir?")

    assert sonuc["cevap"].strip()
    assert sonuc["kaynaklar"], "Cevaplanabilir soru için kaynak dönmeli"
    kaynak_adlari = [k["kaynak"] for k in sonuc["kaynaklar"]]
    assert "rag_kavrami.txt" in kaynak_adlari


def test_belge_disi_soru_reddedilir(foundry_kaynaklari):
    if not _veritabani_dolu():
        pytest.skip("Veritabanı boş; önce 'python main.py --yukle' çalıştırın.")

    sonuc = generator.cevap_uret(
        foundry_kaynaklari["embedding_client"],
        foundry_kaynaklari["chat_client"],
        "2020 Olimpiyat Oyunları hangi şehirde yapıldı?",
    )

    assert sonuc["cevap"] == generator.BILGI_YOK_CEVABI
    assert sonuc["kaynaklar"] == []
