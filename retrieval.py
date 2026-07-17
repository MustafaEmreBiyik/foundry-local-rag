"""
retrieval.py — Sorgu al, benzer chunk'ları bul, döndür.
"""

import numpy as np

import config
import database as db


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    payda = np.linalg.norm(a) * np.linalg.norm(b)
    if payda == 0:
        return 0.0
    return float(np.dot(a, b) / payda)


def en_alakali_chunklari_bul(
    embedding_client,
    sorgu: str,
    top_k: int = config.TOP_K,
    min_skor: float = config.MIN_SKOR,
) -> list[dict]:
    """
    Sorguya en benzer top_k chunk'ı veritabanından bulur.

    Benzerlik skoru min_skor altında kalan chunk'lar elenir; hiçbir
    chunk eşiği geçemezse boş liste döner (soru belgelerle ilgisiz).

    Parametreler:
        embedding_client : Foundry Local embedding istemcisi
        sorgu            : Kullanıcı sorusu
        top_k            : En fazla kaç chunk döndürüleceği
        min_skor         : Kabul edilen en düşük benzerlik skoru
    """
    yanit = embedding_client.generate_embedding(sorgu)
    sorgu_vektoru = np.array(yanit.data[0].embedding)

    conn = db.baglan()
    try:
        chunklar = db.tum_chunklari_getir(conn)
    finally:
        conn.close()

    skorlar = []
    for chunk in chunklar:
        skor = cosine_similarity(sorgu_vektoru, chunk["embedding"])
        if skor < min_skor:
            continue
        skorlar.append({
            "icerik": chunk["icerik"],
            "kaynak": chunk["kaynak"],
            "sira": chunk["sira"],
            "skor": skor
        })

    skorlar.sort(key=lambda x: x["skor"], reverse=True)
    return skorlar[:top_k]
