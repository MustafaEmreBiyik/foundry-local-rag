"""generator.py — Prompt oluştur, Foundry Local LLM'e gönder, cevap al."""

import config
import retrieval

SISTEM_PROMPT = """Sen bir yardımcı asistansın. Yalnızca aşağıda "Belgeler" bölümünde
verilen bilgilere dayanarak cevap ver. Belgede ilgili bilgi yoksa
"Bu konuda elimde bilgi yok." de. Asla tahmin yürütme veya uydurma bilgi verme."""

BILGI_YOK_CEVABI = "Bu konuda elimde bilgi yok."

ALINTI_UZUNLUGU = 100  # kaynak gösteriminde kullanılan alıntının karakter sayısı


def context_olustur(chunklar: list[dict]) -> str:
    parcalar = []
    for i, chunk in enumerate(chunklar, start=1):
        parcalar.append(f"[Kaynak {i}: {chunk['kaynak']}]\n{chunk['icerik']}")
    return "\n\n".join(parcalar)


def kaynaklari_olustur(chunklar: list[dict]) -> list[dict]:
    """
    Chunk'lardan kullanıcıya gösterilecek kaynak listesini üretir.

    Retrieval sırası (skora göre azalan) korunur; aynı belgeden gelen
    chunk'lar tekilleştirilir ve her kaynak için en yüksek skor ile
    kısa bir alıntı tutulur.
    """
    kaynaklar = []
    gorulen = set()
    for chunk in chunklar:
        if chunk["kaynak"] in gorulen:
            continue
        gorulen.add(chunk["kaynak"])

        alinti = chunk["icerik"][:ALINTI_UZUNLUGU].rstrip()
        if len(chunk["icerik"]) > ALINTI_UZUNLUGU:
            alinti += "..."

        kaynaklar.append({
            "kaynak": chunk["kaynak"],
            "skor": chunk["skor"],
            "alinti": alinti,
        })
    return kaynaklar


def cevap_uret(
    embedding_client,
    chat_client,
    sorgu: str,
    top_k: int = config.TOP_K,
) -> dict:
    """
    Uçtan uca RAG pipeline'ı.

    Parametreler:
        embedding_client : Foundry Local embedding istemcisi
        chat_client      : Foundry Local sohbet istemcisi
        sorgu            : Kullanıcının sorusu
        top_k            : Kaç chunk bağlam olarak kullanılacağı

    Dönüş: {'cevap': str,
            'kaynaklar': [{'kaynak', 'skor', 'alinti'}, ...],
            'chunklar': [...]}
    """
    ilgili_chunklar = retrieval.en_alakali_chunklari_bul(
        embedding_client,
        sorgu,
        top_k,
    )

    # Hiçbir chunk benzerlik eşiğini geçemediyse LLM'i hiç çağırma;
    # modele alakasız bağlam verip cevap uydurtmaktansa doğrudan reddet.
    if not ilgili_chunklar:
        return {
            "cevap": BILGI_YOK_CEVABI,
            "kaynaklar": [],
            "chunklar": []
        }

    context = context_olustur(ilgili_chunklar)
    kullanici_prompt = f"Belgeler:\n{context}\n\nSoru: {sorgu}"

    yanit = chat_client.complete_chat(
        [
            {"role": "system", "content": SISTEM_PROMPT},
            {"role": "user", "content": kullanici_prompt}
        ]
    )

    return {
        "cevap": yanit.choices[0].message.content,
        "kaynaklar": kaynaklari_olustur(ilgili_chunklar),
        "chunklar": ilgili_chunklar
    }
