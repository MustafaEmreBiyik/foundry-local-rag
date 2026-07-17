"""database.py birim testleri: serileştirme, değiştirme ve atomiklik."""

import sqlite3

import numpy as np
import pytest

import database as db


def _ornek_chunklar():
    return [
        {"kaynak": "a.txt", "sira": 0, "icerik": "Birinci metin",
         "embedding": [0.1, 0.2, 0.3]},
        {"kaynak": "b.txt", "sira": 0, "icerik": "İkinci metin",
         "embedding": [0.4, 0.5, 0.6]},
    ]


def test_embedding_serilestirme_gidis_donus(gecici_db):
    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, _ornek_chunklar())
        sonuc = db.tum_chunklari_getir(conn)
    finally:
        conn.close()

    assert len(sonuc) == 2
    assert sonuc[0]["kaynak"] == "a.txt"
    assert sonuc[0]["sira"] == 0
    assert isinstance(sonuc[0]["embedding"], np.ndarray)
    np.testing.assert_allclose(sonuc[0]["embedding"], [0.1, 0.2, 0.3])
    np.testing.assert_allclose(sonuc[1]["embedding"], [0.4, 0.5, 0.6])


def test_sira_numarasi_korunur(gecici_db):
    chunklar = [
        {"kaynak": "u.txt", "sira": i, "icerik": f"Parça {i}", "embedding": [float(i)]}
        for i in range(3)
    ]
    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, chunklar)
        sonuc = db.tum_chunklari_getir(conn)
    finally:
        conn.close()

    assert [c["sira"] for c in sonuc] == [0, 1, 2]


def test_chunklari_degistir_eski_kayitlari_yenileriyle_degistirir(gecici_db):
    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, _ornek_chunklar())
        db.chunklari_degistir(
            conn,
            [{"kaynak": "yeni.txt", "sira": 0, "icerik": "Yeni", "embedding": [1.0]}],
        )
        assert db.kayit_sayisi(conn) == 1
        assert db.tum_chunklari_getir(conn)[0]["kaynak"] == "yeni.txt"
    finally:
        conn.close()


def test_transaction_hatasi_eski_veriyi_korur(gecici_db):
    conn = db.baglan()
    try:
        db.chunklari_degistir(conn, _ornek_chunklar())

        # icerik=None NOT NULL kısıtını ihlal eder; transaction geri alınmalı
        bozuk = [{"kaynak": "c.txt", "sira": 0, "icerik": None, "embedding": [1.0]}]
        with pytest.raises(sqlite3.IntegrityError):
            db.chunklari_degistir(conn, bozuk)

        assert db.kayit_sayisi(conn) == 2
        kaynaklar = {c["kaynak"] for c in db.tum_chunklari_getir(conn)}
        assert kaynaklar == {"a.txt", "b.txt"}
    finally:
        conn.close()


def test_kayit_sayisi_bos_tabloda_sifir(gecici_db):
    conn = db.baglan()
    try:
        assert db.kayit_sayisi(conn) == 0
    finally:
        conn.close()
