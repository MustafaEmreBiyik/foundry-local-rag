"""retrieval.py birim testleri: cosine similarity, sıralama ve eşik."""

import numpy as np

import database as db
import retrieval
from conftest import SahteEmbeddingClient


class TestCosineSimilarity:
    def test_ayni_yondeki_vektorler_bir_verir(self):
        a = np.array([1.0, 2.0, 3.0])
        assert retrieval.cosine_similarity(a, a * 2) == 1.0

    def test_dik_vektorler_sifir_verir(self):
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        assert retrieval.cosine_similarity(a, b) == 0.0

    def test_zit_vektorler_eksi_bir_verir(self):
        a = np.array([1.0, 0.0])
        assert retrieval.cosine_similarity(a, -a) == -1.0

    def test_sifir_vektor_sifir_verir(self):
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 1.0])
        assert retrieval.cosine_similarity(a, b) == 0.0


def _chunklari_kaydet(vektorler: dict[str, list[float]]):
    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, [
            {"kaynak": f"{ad}.txt", "sira": 0, "icerik": ad, "embedding": v}
            for ad, v in vektorler.items()
        ])
    finally:
        conn.close()


class TestEnAlakaliChunklariBul:
    def test_skora_gore_azalan_siralar_ve_top_k_uygular(self, gecici_db):
        _chunklari_kaydet({
            "tam": [1.0, 0.0],
            "yakin": [0.9, 0.4359],
            "orta": [0.6, 0.8],
        })
        client = SahteEmbeddingClient({"soru": [1.0, 0.0]})

        sonuc = retrieval.en_alakali_chunklari_bul(client, "soru", top_k=2, min_skor=0.0)

        assert [c["kaynak"] for c in sonuc] == ["tam.txt", "yakin.txt"]
        assert sonuc[0]["skor"] >= sonuc[1]["skor"]

    def test_esik_altindaki_chunklar_elenir(self, gecici_db):
        _chunklari_kaydet({
            "alakali": [1.0, 0.0],
            "alakasiz": [0.0, 1.0],  # skor 0.0 < esik
        })
        client = SahteEmbeddingClient({"soru": [1.0, 0.0]})

        sonuc = retrieval.en_alakali_chunklari_bul(client, "soru", min_skor=0.35)

        assert [c["kaynak"] for c in sonuc] == ["alakali.txt"]

    def test_hicbir_chunk_esigi_gecemezse_bos_liste_doner(self, gecici_db):
        _chunklari_kaydet({
            "a": [0.0, 1.0],
            "b": [0.1, 0.995],
        })
        client = SahteEmbeddingClient({"ilgisiz soru": [1.0, 0.0]})

        sonuc = retrieval.en_alakali_chunklari_bul(client, "ilgisiz soru", min_skor=0.35)

        assert sonuc == []

    def test_sonuclar_icerik_kaynak_sira_ve_skor_icerir(self, gecici_db):
        _chunklari_kaydet({"tek": [1.0, 0.0]})
        client = SahteEmbeddingClient({"soru": [1.0, 0.0]})

        sonuc = retrieval.en_alakali_chunklari_bul(client, "soru")

        assert sonuc[0]["icerik"] == "tek"
        assert sonuc[0]["kaynak"] == "tek.txt"
        assert sonuc[0]["sira"] == 0
        assert sonuc[0]["skor"] == 1.0
