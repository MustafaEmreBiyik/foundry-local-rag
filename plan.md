# 📘 Local RAG Yapay Zeka Asistanı — 4 Haftalık Çalışma Planı

---

## 🔍 Projeye Genel Bakış

### Ne Yapacaksın?

Tamamen **kendi bilgisayarında çalışan**, internete ihtiyaç duymayan bir **belge tabanlı soru-cevap asistanı** (chatbot) geliştirecesin.

Örneğin; 10 adet ders notu veya teknik doküman yüklersin, asistan bu belgeleri okur ve sana şu soruyu sorabilirsin: *"Vektör nedir?"* — chatbot ilgili belgeyi bulur, özetler ve cevaplar.

### Kullanılacak Teknolojiler

| Teknoloji | Açıklama |
|---|---|
| **Python 3.11+** | Projenin ana programlama dili |
| **Microsoft Foundry Local** | İnternetsiz, bilgisayarında LLM çalıştırmana olanak tanır |
| **RAG (Retrieval-Augmented Generation)** | Yapay zekanın belgelerden bilgi çekerek cevap üretmesi yöntemi |
| **Embeddings** | Metinleri sayısal vektörlere dönüştürme (anlam temsiline dayalı arama için) |
| **SQLite** | Hafif, kurulum gerektirmeyen yerel veritabanı |
| **Cosine Similarity** | İki vektör arasındaki benzerliği ölçen matematiksel yöntem |
| **Streamlit** (opsiyonel) | Python ile basit web arayüzü oluşturma |

### Nasıl Çalışır? (Basit Anlatım)

```
[Sen soru sorarsın]
       ↓
[Asistan soruyu vektöre çevirir]
       ↓
[Veritabanındaki belgelerle karşılaştırır]
       ↓
[En ilgili belge parçalarını bulur]
       ↓
[LLM (yerel yapay zeka) bu bilgiyle cevap üretir]
       ↓
[Cevabı sana gösterir]
```

---

## 🧱 Ön Hazırlık

Projeye başlamadan önce şu temel konulara bir göz at. Her biri için 1-2 saat ayırman yeterli.

### Öğrenilmesi Gereken Temel Konular

| Konu | Neden Önemli? | Kaynak |
|---|---|---|
| Python temelleri (fonksiyon, liste, döngü, modül import) | Tüm proje Python ile yazılacak | [Python.org resmi rehber (TR)](https://docs.python.org/tr/3/tutorial/) |
| `pip` ve `requirements.txt` kullanımı | Kütüphane kurulumu için | `pip install <paket>` komutunu dene |
| SQLite & SQL temelleri | Veri saklama için | [W3Schools SQL](https://www.w3schools.com/sql/) |
| Yapay Zeka ve LLM nedir? | Projenin temel kavramı | [Microsoft Learn – AI Temelleri](https://learn.microsoft.com/tr-tr/training/paths/get-started-with-artificial-intelligence-on-azure/) |
| RAG nedir? | Projenin çekirdeği | [Microsoft Blog (İngilizce)](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968) |
| Foundry Local kurulumu | Yerel LLM çalıştırmak için | [Microsoft Learn](https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local) |

### Araç Kurulumları (Hemen Yap!)

```bash
# 1. Python 3.11+ yüklü mü kontrol et
python --version

# 2. VS Code indir: https://code.visualstudio.com/

# 3. Windows için Foundry Local SDK ve temel kütüphaneleri kur
pip install foundry-local-sdk-winml numpy
```

---

## 📅 Haftalık Plan

---

### 📌 Hafta 1: RAG Kavramı & Ortam Kurulumu

**🎯 Hafta Hedefi:** Foundry Local çalışıyor, temel kavramlar anlaşıldı, ilk "Merhaba Model" testi yapıldı.

#### Öğrenilecek Konular

- RAG (Al-Büyüt-Üret) deseninin ne olduğu ve neden kullanıldığı
- Microsoft Foundry Local'ın ne işe yaradığı
- Python proje yapısı (`main.py`, `requirements.txt`, klasör düzeni)
- LLM (Büyük Dil Modeli) nedir, nasıl çalışır?

#### Yapılacaklar Listesi

- [x] **Gün 1–2:** RAG kavramını anla
  - Microsoft Tech Community blog yazısını oku (Giriş + "RAG Nedir?" bölümü)
  - Kağıda çiz: bir kullanıcı sorusu nasıl cevap olur?
  - Rol yapma egzersizi: bir arkadaşınla "insan RAG" simülasyonu yap — biri soruyu sorar, diğeri ilgili paragrafı bulur, üçüncüsü cevap üretir

- [x] **Gün 3:** Foundry Local'ı kur
  - [Resmi kurulum sayfasını](https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local) takip et
  - `pip install foundry-local-sdk-winml` komutunu çalıştır
  - Desteklenen model listesine bak

- [x] **Gün 4:** İlk Python testi
  - `main.py` dosyası oluştur
  - Küçük bir model yükle (örn. `qwen2.5-0.5b`) ve basit bir prompt ver
  - Çıktıyı terminalde gör → `"Merhaba Dünya!"` gibi bir şey üretmeli

  ```python
  # Örnek test kodu
  from foundry_local_sdk import Configuration, FoundryLocalManager

  FoundryLocalManager.initialize(Configuration(app_name="rag_asistani"))
  manager = FoundryLocalManager.instance
  model = manager.catalog.get_model("qwen2.5-0.5b")
  model.download(lambda _: None)
  model.load()
  client = model.get_chat_client()
  response = client.complete_chat([
      {"role": "user", "content": "Merhaba! Sen kimsin?"}
  ])
  print(response.choices[0].message.content)
  ```

- [x] **Gün 5:** Python proje iskeleti oluştur
  - Proje klasörünü şöyle düzenle:
    ```
    rag-asistan/
    ├── main.py
    ├── requirements.txt
    └── belgeler/
        └── ornek.txt
    ```
  - `requirements.txt` dosyasına `foundry-local-sdk-winml` yaz
  - `main.py` içinde temel işlemleri fonksiyonlara böl

**🏁 Hafta 1 Milestone:** `main.py` çalışıyor, Foundry Local yüklü, terminal çıktısında modelin ürettiği metin görünüyor.

---

### 📌 Hafta 2: Embeddings, Benzerlik Arama & SQLite

**🎯 Hafta Hedefi:** Metinleri vektöre çevirebiliyorsun, en benzer metni bulabiliyorsun ve SQLite veritabanı oluşturdun.

#### Öğrenilecek Konular

- Embedding (Gömme) nedir? Metin → sayı dönüşümü nasıl olur?
- Cosine Similarity (Kosinüs Benzerliği) mantığı
- SQLite veritabanı oluşturma, tablo açma, veri ekleme ve sorgulama
- Temel prompt mühendisliği: sistem ve kullanıcı prompt'ları

#### Yapılacaklar Listesi

- [x] **Gün 1–2:** Embedding kavramını öğren
  - Microsoft Learn'deki "Build a RAG application" başlığını oku
  - Beş cümle yaz, Foundry Local ile her biri için embedding üret
  - İki cümlenin ne kadar benzediğini sayısal olarak hesapla

  ```python
  import numpy as np

  def cosine_similarity(a, b):
      return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

  # qwen3-embedding-0.6b modeli yüklenip embedding_client oluşturulduktan sonra
  embed1 = embedding_client.generate_embedding("Kedi bir hayvandır.").data[0].embedding
  embed2 = embedding_client.generate_embedding("Köpek bir hayvandır.").data[0].embedding
  embed3 = embedding_client.generate_embedding("Python bir programlama dilidir.").data[0].embedding
  
  print(cosine_similarity(embed1, embed2))  # Yüksek benzerlik beklenir
  print(cosine_similarity(embed1, embed3))  # Düşük benzerlik beklenir
  ```

- [x] **Gün 3:** SQLite ile veritabanı kur
  - Python'ın yerleşik `sqlite3` modülünü kullan
  - `belgeler` adında bir tablo oluştur:
    - `id` (tam sayı, otomatik artan)
    - `icerik` (metin)
    - `embedding` (blob — JSON olarak saklanacak)
  - 3-5 örnek metin satırı ekle, ardından `SELECT` ile çek

  ```python
  import sqlite3, json

  conn = sqlite3.connect("veritabani.db")
  cur = conn.cursor()

  cur.execute("""
      CREATE TABLE IF NOT EXISTS belgeler (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          icerik TEXT,
          embedding TEXT
      )
  """)
  conn.commit()
  ```

- [x] **Gün 4:** Embedding'i veritabanına kaydet
  - Birkaç örnek metin için embedding üret
  - Her birini `embedding = json.dumps(vector.tolist())` ile JSON'a çevir
  - SQLite'a kaydet, geri oku, JSON'dan tekrar numpy dizisine çevir

- [x] **Gün 5:** Prompt mühendisliği deneyleri
  - Aynı soruyu iki farklı şekilde sor: contextsiz ve contextli
  - Farkı gözlemle
  - Sistem prompt'u yaz: `"Yalnızca verilen belgelerden yanıt ver. Bilmiyorsan 'Bu bilgiye sahip değilim.' de."`

**🏁 Hafta 2 Milestone:** Embedding üreten ve SQLite'a kaydeden kod çalışıyor. Sorgu için en benzer metni bulan basit fonksiyon yazıldı.

---

### 📌 Hafta 3: Belge Yükleme & Arama Pipeline'ı

**🎯 Hafta Hedefi:** 5-10 gerçek belgeyi sisteme yükledin, herhangi bir soru için en alakalı belge parçalarını otomatik olarak bulan kod çalışıyor.

#### Öğrenilecek Konular

- Büyük metinleri parçalara (chunk) bölme stratejileri
- Toplu embedding üretimi (batch processing)
- Retrieval (Arama) fonksiyonu tasarımı
- Küçük ölçekli vektör arama: brute-force yaklaşım

#### Yapılacaklar Listesi

- [x] **Gün 1:** Belge kümeni hazırla
  - 5-10 kısa metin belgesi topla (ders notları, teknik makale, SSS vs.)
  - Bunları `belgeler/` klasörüne `.txt` formatında kaydet
  - Her bir belgeyi paragraflara/bölümlere ayır (chunk boyutu: 200-400 kelime)

- [x] **Gün 2:** Veri yükleme (ingestion) scripti yaz

  ```python
  # ingestion.py
  import os

  def chunk_text(text, chunk_size=300):
      """Metni belirli kelime sayısına göre parçala"""
      words = text.split()
      return [" ".join(words[i:i+chunk_size]) 
              for i in range(0, len(words), chunk_size)]

  def load_documents(folder_path):
      chunks = []
      for filename in os.listdir(folder_path):
          if filename.endswith(".txt"):
              with open(os.path.join(folder_path, filename), "r") as f:
                  text = f.read()
              for chunk in chunk_text(text):
                  chunks.append({"kaynak": filename, "icerik": chunk})
      return chunks
  ```

- [x] **Gün 3:** Embedding üret ve veritabanına kaydet
  - Her chunk için embedding üret
  - Tüm chunk'ları ve embedding'leri SQLite'a kaydet
  - Son kontrol: veritabanında kaç satır var? Doğru mu?

- [x] **Gün 4:** Retrieval fonksiyonu yaz

  ```python
  def en_alakali_chunklari_bul(sorgu, top_k=3):
      yanit = embedding_client.generate_embedding(sorgu)
      sorgu_embedding = yanit.data[0].embedding
      
      cur.execute("SELECT id, icerik, embedding FROM belgeler")
      satirlar = cur.fetchall()
      
      sonuclar = []
      for satir_id, icerik, emb_json in satirlar:
          emb = np.array(json.loads(emb_json))
          skor = cosine_similarity(sorgu_embedding, emb)
          sonuclar.append((skor, icerik))
      
      sonuclar.sort(reverse=True)
      return [icerik for _, icerik in sonuclar[:top_k]]
  ```

- [x] **Gün 5:** Test et!
  - 5 farklı soru sor
  - Dönen chunk'ların gerçekten soruyla ilgili olup olmadığını kontrol et
  - Alakasız sonuçlar varsa chunk boyutunu veya embedding modelini değiştirmeyi dene

**🏁 Hafta 3 Milestone:** `ingestion.py` tüm belgeleri yüklüyor ve `en_alakali_chunklari_bul()` fonksiyonu doğru sonuçlar döndürüyor.

---

### 📌 Hafta 4: LLM Entegrasyonu & Arayüz

**🎯 Hafta Hedefi:** Çalışan, uçtan uca bir RAG asistanı: soru soruyorsun, sistem belgeleri tarıyor, LLM cevap üretiyor.

#### Öğrenilecek Konular

- Foundry Local ile chat tamamlama API'si
- Uçtan uca pipeline montajı (end-to-end)
- Basit kullanıcı arayüzü (CLI veya Streamlit)
- Sorumlu yapay zeka: "bilmiyorum" diyebilen sistem

#### Yapılacaklar Listesi

- [x] **Gün 1:** LLM cevap üretme fonksiyonu

  ```python
  def cevap_uret(kullanici_sorusu):
      # Adım 1: İlgili chunk'ları bul
      alakali_metinler = en_alakali_chunklari_bul(kullanici_sorusu)
      
      # Adım 2: Context oluştur
      context = "\n\n".join(alakali_metinler)
      
      # Adım 3: Prompt hazırla
      sistem_prompt = """
      Sen bir yardımcı asistansın. Yalnızca aşağıda verilen belgelerden
      faydalanarak cevap ver. Belgede bilgi yoksa 'Bu konuda bilgim yok.' de.
      """
      
      kullanici_prompt = f"""
      Belgeler:
      {context}
      
      Soru: {kullanici_sorusu}
      """
      
      # Adım 4: LLM'den cevap al
      cevap = chat_client.complete_chat([
          {"role": "system", "content": sistem_prompt},
          {"role": "user", "content": kullanici_prompt}
      ])
      
      return cevap
  ```

- [x] **Gün 2:** CLI arayüzü (Seçenek A — Zorunlu)

  ```python
  if __name__ == "__main__":
      print("🤖 RAG Asistanı hazır! Çıkmak için 'exit' yaz.\n")
      while True:
          soru = input("Sorunuz: ")
          if soru.lower() == "exit":
              break
          cevap = cevap_uret(soru)
          print(f"\nCevap: {cevap}\n")
  ```

- [ ] **Gün 3:** Streamlit arayüzü (Seçenek B — Opsiyonel; yapılmamasına karar verildi, bağımlılıklardan çıkarıldı)

  ```python
  # app.py
  import streamlit as st
  
  st.title("📚 Belge Asistanım")
  
  soru = st.text_input("Bir soru sor:")
  if st.button("Cevapla") and soru:
      with st.spinner("Düşünüyorum..."):
          cevap = cevap_uret(soru)
      st.success(cevap)
  ```

  ```bash
  streamlit run app.py
  ```

- [x] **Gün 4:** Uçtan uca test
  - 10 farklı soru sor — 7'si belgelerden cevaplanabilir, 3'ü cevaplanamaz olsun
  - Sistemin "bilmiyorum" diyebildiğini doğrula
  - Yavaş cevaplar için daha küçük model dene

- [x] **Gün 5:** Temizlik ve gözden geçirme
  - `print` debug satırlarını kaldır
  - Her fonksiyona Türkçe açıklama (docstring) ekle
  - README.md dosyası yaz: "Nasıl kurulur? Nasıl çalıştırılır?"

**🏁 Hafta 4 Milestone:** Asistan tamamen çalışıyor! Soru sorulduğunda belgeye dayalı cevap üretiyor ve bilmediğini kabul ediyor.

---

## 🏗️ Proje Mimarisi

### Klasör Yapısı

```
rag-asistan/
│
├── main.py              # Ana giriş noktası (CLI çalıştırma)
├── app.py               # Streamlit arayüzü (opsiyonel)
├── ingestion.py         # Belgeleri yükle, parçala, embedding üret, kaydet
├── retrieval.py         # Sorgu al, benzer chunk'ları bul
├── generator.py         # LLM'ye bağlan, prompt oluştur, cevap üret
├── database.py          # SQLite bağlantı ve tablo yönetimi
├── requirements.txt     # Gerekli Python kütüphaneleri
├── README.md            # Kurulum ve kullanım açıklamaları
│
├── belgeler/            # Kaynak belgelerin bulunduğu klasör
│   ├── belge1.txt
│   ├── belge2.txt
│   └── ...
│
└── veritabani.db        # SQLite veritabanı dosyası (otomatik oluşur)
```

### Bileşenler ve Görevleri

```
[Kullanıcı Sorusu]
       │
       ▼
[retrieval.py]  ──→  Soruyu embedding'e çevir
       │               SQLite'ta benzer chunk'ları bul
       │               Top-3 chunk döndür
       ▼
[generator.py]  ──→  Sistem prompt + context + soru birleştir
       │               Foundry Local LLM'e gönder
       │               Cevabı al
       ▼
[Kullanıcıya Cevap]
```

---

## 📚 Kaynaklar ve Önerilen Araçlar

### Resmi Kaynaklar

| Kaynak | Bağlantı | Ne Zaman Kullan? |
|---|---|---|
| Microsoft Learn – Foundry Local Nedir? | [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/foundry-local/what-is-foundry-local) | Hafta 1 |
| Microsoft Learn – RAG Uygulaması Oluştur | [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/foundry-local/tutorials/tutorial-build-rag-app) | Hafta 2-3 |
| Microsoft Tech Community Blog | [techcommunity.microsoft.com](https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968) | Hafta 1 |
| Prompt Mühendisliği Rehberi | [learn.microsoft.com](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/prompt-engineering) | Hafta 2 |
| SQLite Resmi Sitesi | [sqlite.org](https://sqlite.org/index.html) | Hafta 2 |
| Windows SQLite Veri Erişimi | [learn.microsoft.com](https://learn.microsoft.com/en-us/windows/apps/develop/data-access/sqlite-data-access) | Hafta 2 |

### Ek Öğrenme Kaynakları

| Kaynak | Açıklama |
|---|---|
| [W3Schools SQL Rehberi](https://www.w3schools.com/sql/) | SQL öğrenmek için eğlenceli ve hızlı |
| [Streamlit Docs](https://docs.streamlit.io/) | Arayüz yapmak istersen |
| [Python Resmi Rehberi (TR)](https://docs.python.org/tr/3/tutorial/) | Python tazelemek için |
| [NumPy Quickstart](https://numpy.org/doc/stable/user/quickstart.html) | Vektör işlemleri için |

### Önerilen Araçlar

| Araç | Açıklama | Ücretsiz mi? |
|---|---|---|
| **VS Code** | Kod editörü, en popüler seçim | ✅ Evet |
| **DB Browser for SQLite** | SQLite veritabanını görsel olarak incele | ✅ Evet |
| **Git + GitHub** | Kodunu kaydet ve yedekle | ✅ Evet |
| **Postman** | API testleri için (opsiyonel) | ✅ Evet |

---

## ✅ Teslim Kontrol Listesi

Projeyi teslim etmeden önce aşağıdaki her maddeyi kontrol et:

### Zorunlu

- [x] Foundry Local kurulu ve çalışıyor
- [x] En az 5 belge sisteme yüklendi
- [x] Belgeler parçalanıyor ve embedding üretiliyor
- [x] Embedding'ler SQLite'a kaydediliyor
- [x] Soru sorulduğunda en alakalı 3 chunk döndürülüyor
- [x] LLM bu chunk'ları kullanarak cevap üretiyor
- [x] Sistem "Bu bilgiye sahip değilim." diyebiliyor
- [x] CLI veya Streamlit arayüzü çalışıyor
- [x] `README.md` dosyası var (kurulum + kullanım açıklaması)

### Opsiyonel (Bonus)

- [ ] Streamlit ile görsel arayüz
- [x] Cevaplarda kaynak belge adı gösteriliyor
- [ ] Birden fazla soru sormak için oturum geçmişi tutuluyor
- [ ] 10+ belge ile test edildi
- [ ] Performans ölçüldü (sorgu başına kaç saniye?)

---

## 💡 Sık Karşılaşılan Sorunlar ve Çözümleri

| Sorun | Muhtemel Neden | Çözüm |
|---|---|---|
| Model indirmiyor | İnternet bağlantısı yok / hatalı model adı | Model adını kontrol et, WiFi'ı dene |
| Cevap çok yavaş geliyor | İlk model yüklemesi veya donanım yetersizliği | Model önbelleğini ve donanım yürütme sağlayıcısını kontrol et |
| "ModuleNotFoundError" | Kütüphane kurulmamış | `pip install <paket-adı>` çalıştır |
| Alakasız sonuçlar geliyor | Chunk çok büyük / küçük | Chunk boyutunu 200-400 kelimeye ayarla |
| SQLite hatası | Tablo yok | `CREATE TABLE IF NOT EXISTS` kullan |
| Embedding boyutu uyuşmuyor | Farklı model kullanıldı | Hem kaydetme hem aramada aynı modeli kullan |

---

> 💬 **Son Söz:** Bu proje, gerçek dünya yapay zeka mühendisliğinin temel yapı taşlarını içeriyor. Zorlandığın yerler olacak — bu çok normal! Her hata, öğrenmenin bir parçası. Takılırsan Microsoft Learn belgelerine ve blog yazısına dön. Başarılar! 🚀
