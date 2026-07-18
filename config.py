"""
config.py — Projenin merkezi yapılandırması.

Model adları, dosya yolları, chunking ve retrieval ayarlarının tamamı
buradan yönetilir; diğer modüller bu değerleri import eder.
"""

from pathlib import Path

# Çalışma dizininden bağımsız olarak her zaman proje kökü kullanılır
PROJE_KOKU = Path(__file__).resolve().parent

# --- Foundry Local ---
APP_NAME = "local_rag_asistani"
LLM_MODEL = "qwen2.5-0.5b"
EMBED_MODEL = "qwen3-embedding-0.6b"

# --- Dosya yolları ---
DB_YOLU = PROJE_KOKU / "veritabani.db"
BELGELER_KLASORU = PROJE_KOKU / "belgeler"

# --- Chunking ---
CHUNK_BOYUTU = 300   # kelime; bir chunk'ın en fazla kaç kelime içereceği
CHUNK_ORTUSME = 50   # kelime; ardışık chunk'ların paylaştığı kuyruk uzunluğu
# Tek istekte kaç chunk'ın embedding'inin üretileceği. Büyük batch'ler
# CPU'da Foundry Local'ın istek zaman aşımına takılabiliyor; sorun
# yaşarsanız küçültün.
EMBED_BATCH = 4

# --- Retrieval ---
TOP_K = 3            # bağlam olarak kullanılacak en fazla chunk sayısı

# Bu skorun altındaki chunk'lar soruyla ilgisiz kabul edilir.
# 15 belge / 30 soruluk degerlendirme.py setiyle qwen3-embedding-0.6b
# üzerinde kalibre edildi: reddedilmesi gerekenlerin en yükseği 0.423,
# cevaplanabilir soruların çoğu 0.49+. Çok kısa sorular (ör. "DNS ne işe
# yarar?") eşiğin hemen altında kalabilir; soruyu detaylandırmak yeterli.
# Alakasız sonuçlar görürseniz yükseltin, "bilgi yok" cevabı çok sık
# geliyorsa düşürün.
MIN_SKOR = 0.45
