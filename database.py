"""
database.py — SQLite bağlantı ve tablo yönetimi.

Bu modül veritabanı bağlantısını açar, gerekli tabloları oluşturur
ve diğer modüllerin kullandığı temel CRUD işlevlerini sağlar.
"""

import sqlite3
import json
import numpy as np

import config

TABLO_SQL = """
    CREATE TABLE IF NOT EXISTS belgeler (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        kaynak    TEXT    NOT NULL,
        sira      INTEGER NOT NULL,
        icerik    TEXT    NOT NULL,
        embedding TEXT    NOT NULL
    )
"""


def baglan() -> sqlite3.Connection:
    """Veritabanına bağlantı döndürür; yoksa oluşturur."""
    conn = sqlite3.connect(config.DB_YOLU)
    conn.row_factory = sqlite3.Row  # Sonuçlara sütun adıyla erişim sağlar
    return conn


GEREKLI_KOLONLAR = {"id", "kaynak", "sira", "icerik", "embedding"}


def tablolari_olustur(conn: sqlite3.Connection) -> None:
    """
    Gerekli tabloları oluşturur; şeması eskimiş tabloyu yeniden kurar.

    Eski şemadaki veriler yeni kodla kullanılamayacağı için şema
    değişiminde tablo silinip boş olarak yeniden oluşturulur
    (yeniden yükleme gerekir).
    """
    conn.execute(TABLO_SQL)
    kolonlar = {satir[1] for satir in conn.execute("PRAGMA table_info(belgeler)")}
    if kolonlar != GEREKLI_KOLONLAR:
        conn.execute("DROP TABLE belgeler")
        conn.execute(TABLO_SQL)
    conn.commit()


def chunklari_degistir(conn: sqlite3.Connection, chunklar: list[dict]) -> int:
    """
    Mevcut kayıtları yeni chunk'larla tek transaction içinde değiştirir.

    Silme ve toplu ekleme aynı transaction'da yalnızca DML komutlarıyla
    yapılır (Python sqlite3, DDL komutlarını transaction dışında anında
    commit eder); işlem yarıda kesilirse eski veriler korunur.

    Parametreler:
        conn     : Açık SQLite bağlantısı
        chunklar : Her öğesi {'kaynak', 'sira', 'icerik', 'embedding'}
                   içeren liste

    Dönüş: Eklenen kayıt sayısı
    """
    tablolari_olustur(conn)
    satirlar = [
        (c["kaynak"], c["sira"], c["icerik"], json.dumps(c["embedding"]))
        for c in chunklar
    ]
    with conn:
        conn.execute("DELETE FROM belgeler")
        conn.executemany(
            "INSERT INTO belgeler (kaynak, sira, icerik, embedding) "
            "VALUES (?, ?, ?, ?)",
            satirlar
        )
    return len(satirlar)


def tum_chunklari_getir(conn: sqlite3.Connection) -> list[dict]:
    """
    Veritabanındaki tüm chunk'ları döndürür.

    Dönüş: Her öğe {'id', 'kaynak', 'sira', 'icerik', 'embedding'} içeren
           sözlük listesi. embedding alanı numpy dizisine dönüştürülmüş
           olarak gelir.
    """
    rows = conn.execute(
        "SELECT id, kaynak, sira, icerik, embedding FROM belgeler"
    ).fetchall()
    sonuc = []
    for row in rows:
        sonuc.append({
            "id": row["id"],
            "kaynak": row["kaynak"],
            "sira": row["sira"],
            "icerik": row["icerik"],
            "embedding": np.array(json.loads(row["embedding"]))
        })
    return sonuc


def kayit_sayisi(conn: sqlite3.Connection) -> int:
    """Veritabanındaki toplam chunk sayısını döndürür."""
    row = conn.execute("SELECT COUNT(*) FROM belgeler").fetchone()
    return row[0]
