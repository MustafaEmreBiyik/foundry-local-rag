"""generator.py birim testleri: context, prompt, kaynaklar ve "bilgi yok"."""

import generator
import retrieval
from conftest import SahteChatClient, SahteEmbeddingClient


def test_context_olustur_kaynaklari_numaralandirir():
    chunklar = [
        {"kaynak": "a.txt", "icerik": "Birinci içerik", "skor": 0.9},
        {"kaynak": "b.txt", "icerik": "İkinci içerik", "skor": 0.8},
    ]

    context = generator.context_olustur(chunklar)

    assert "[Kaynak 1: a.txt]" in context
    assert "Birinci içerik" in context
    assert "[Kaynak 2: b.txt]" in context
    assert "İkinci içerik" in context


class TestKaynaklariOlustur:
    def test_retrieval_sirasi_korunur_ve_tekillestirilir(self):
        chunklar = [
            {"kaynak": "b.txt", "icerik": "En alakalı", "skor": 0.9},
            {"kaynak": "a.txt", "icerik": "İkinci", "skor": 0.8},
            {"kaynak": "b.txt", "icerik": "Tekrar b", "skor": 0.7},
        ]

        kaynaklar = generator.kaynaklari_olustur(chunklar)

        assert [k["kaynak"] for k in kaynaklar] == ["b.txt", "a.txt"]
        # Tekilleştirmede ilk (en yüksek skorlu) chunk esas alınır
        assert kaynaklar[0]["skor"] == 0.9
        assert kaynaklar[0]["alinti"] == "En alakalı"

    def test_uzun_icerik_kisaltilarak_alintilanir(self):
        chunklar = [{
            "kaynak": "a.txt",
            "icerik": "x" * 300,
            "skor": 0.9,
        }]

        kaynaklar = generator.kaynaklari_olustur(chunklar)

        assert kaynaklar[0]["alinti"] == "x" * generator.ALINTI_UZUNLUGU + "..."


def test_bos_retrieval_llm_cagirmadan_bilgi_yok_doner(monkeypatch):
    monkeypatch.setattr(
        retrieval, "en_alakali_chunklari_bul", lambda *a, **k: []
    )
    chat_client = SahteChatClient()

    sonuc = generator.cevap_uret(object(), chat_client, "İlgisiz soru?")

    assert sonuc["cevap"] == generator.BILGI_YOK_CEVABI
    assert sonuc["kaynaklar"] == []
    assert sonuc["chunklar"] == []
    assert chat_client.cagrilar == []  # LLM hiç çağrılmamalı


def test_cevap_uret_prompta_context_ve_soruyu_koyar(monkeypatch):
    chunklar = [{"kaynak": "a.txt", "icerik": "RAG üç adımdan oluşur.", "skor": 0.9}]
    monkeypatch.setattr(
        retrieval, "en_alakali_chunklari_bul", lambda *a, **k: chunklar
    )
    chat_client = SahteChatClient(cevap="RAG; retrieval, augmentation, generation.")

    sonuc = generator.cevap_uret(object(), chat_client, "RAG nedir?")

    assert len(chat_client.cagrilar) == 1
    mesajlar = chat_client.cagrilar[0]
    assert mesajlar[0]["role"] == "system"
    assert mesajlar[0]["content"] == generator.SISTEM_PROMPT
    assert mesajlar[1]["role"] == "user"
    assert "RAG üç adımdan oluşur." in mesajlar[1]["content"]
    assert "Soru: RAG nedir?" in mesajlar[1]["content"]

    assert sonuc["cevap"] == "RAG; retrieval, augmentation, generation."
    assert [k["kaynak"] for k in sonuc["kaynaklar"]] == ["a.txt"]
    assert sonuc["kaynaklar"][0]["skor"] == 0.9
    assert sonuc["chunklar"] == chunklar


def test_retrieval_gercek_zincirle_calisir(gecici_db, monkeypatch):
    """Embedding istemcisi mock'lanır ama retrieval + generator gerçek çalışır."""
    import database as db

    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, [
            {"kaynak": "dok.txt", "sira": 0, "icerik": "Önemli bilgi",
             "embedding": [1.0, 0.0]},
        ])
    finally:
        conn.close()

    embedding_client = SahteEmbeddingClient({"Soru?": [1.0, 0.0]})
    chat_client = SahteChatClient()

    sonuc = generator.cevap_uret(embedding_client, chat_client, "Soru?")

    assert [k["kaynak"] for k in sonuc["kaynaklar"]] == ["dok.txt"]
    assert sonuc["kaynaklar"][0]["alinti"] == "Önemli bilgi"
    assert embedding_client.cagrilar == ["Soru?"]
    assert len(chat_client.cagrilar) == 1
