# Local RAG Asistanı

Microsoft Foundry Local kullanan, tamamen offline çalışan belge tabanlı soru-cevap asistanı.

## Nasıl Çalışır?

```
[Kullanıcı sorusu]
       ↓
[Soru embedding'e dönüştürülür]
       ↓
[SQLite'taki belge vektörleriyle karşılaştırılır]
       ↓
[En ilgili 3 belge parçası seçilir]
       ↓
[Foundry Local LLM cevap üretir]
       ↓
[Cevap + kaynak belge gösterilir]
```

## Kurulum

### 1. Gereksinimler

- Windows 10/11
- Python 3.11 veya üzeri
- En az 8 GB RAM (16 GB önerilen)
- İlk model indirmesi için internet bağlantısı

Python sürümünü kontrol edin:

```bash
python --version
```

### 2. Sanal Ortamı ve Bağımlılıkları Hazırlayın

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Windows için `foundry-local-sdk-winml` kullanılır. Ayrı bir Foundry Local
CLI veya Ollama servisi kurmak gerekmez.

### 3. Belgelerinizi Ekleyin

`belgeler/` klasörüne `.txt` formatında belgelerinizi koyun. Klasörde zaten 5 örnek belge bulunmaktadır.

### 4. Belgeleri Sisteme Yükleyin

Bu adım belgeleri parçalar, embedding üretir ve SQLite'a kaydeder.

```bash
python main.py --yukle
```

İlk çalıştırmada Foundry Local, `qwen3-embedding-0.6b` embedding modelini
indirir ve yerel donanıma uygun çalışma ortamını hazırlar. Model dosyaları
için internet ve yeterli disk alanı gerekir.

### 5. Asistanı Başlatın

```bash
python main.py
```

İlk çalıştırmada ayrıca `qwen2.5-0.5b` sohbet modeli indirilir. Modeller
önbelleğe alındıktan sonra sorgular tamamen yerel çalışır.

`exit` yazarak programdan çıkabilirsiniz.

### 6. Kurulumu Doğrulayın

Kurulumun sağlıklı olduğundan emin olmak için sırasıyla:

```powershell
python -m pytest              # 33 birim testi geçmeli (model gerektirmez)
python degerlendirme.py       # 12/12 retrieval sonucu beklenir
python -m pytest -m smoke     # gerçek modellerle 2 uçtan uca test
```

Ayrıca CLI'da `RAG nedir?` gibi belgelerden cevaplanabilir bir soru sorup
kaynak listesinin geldiğini, `En iyi kek tarifi nedir?` gibi ilgisiz bir
soruya ise "Bu konuda elimde bilgi yok." cevabının döndüğünü kontrol edin.

## Offline Çalışma Sınırları

- **İnternet yalnızca ilk kurulumda gerekir:** `pip install` ve modellerin
  ilk indirilmesi (`qwen3-embedding-0.6b`, `qwen2.5-0.5b`) internet ister.
  Modeller önbelleğe alındıktan sonra yükleme, sorgulama ve cevap üretimi
  tamamen yerel çalışır.
- **Veri dışarı gönderilmez:** Belgeler, embedding'ler ve sorular yalnızca
  yerel diskteki `veritabani.db` dosyasında ve yerel model süreçlerinde
  işlenir.
- **Donanım sınırı:** Modeller CPU'da çalışabilir ancak cevap üretimi
  yavaştır; küçük `qwen2.5-0.5b` modelinin Türkçe cevap kalitesi de
  sınırlıdır. Daha iyi sonuç için `config.py` içinden daha büyük bir
  katalog modeli seçilebilir (daha fazla RAM/disk gerektirir).
- **Model kataloğu çevrimdışı genişletilemez:** Yeni bir model kullanmak
  isterseniz ilk indirme için tekrar internet gerekir.

## Proje Yapısı

```
.
├── main.py           # Ana giriş noktası ve CLI
├── config.py         # Merkezi yapılandırma (modeller, chunk, eşikler)
├── ingestion.py      # Belge yükleme, parçalama, embedding üretimi
├── retrieval.py      # Cosine similarity ile en alakalı chunk'ları bulma
├── generator.py      # Prompt oluşturma ve LLM cevabı alma
├── database.py       # SQLite bağlantı ve tablo yönetimi
├── degerlendirme.py  # Retrieval kalite değerlendirme seti
├── requirements.txt  # Python bağımlılıkları
├── pytest.ini        # Test yapılandırması
├── tests/            # Birim ve smoke testleri
├── belgeler/         # Kaynak belgeler (.txt)
└── veritabani.db     # SQLite veritabanı (otomatik oluşur)
```

## Yapılandırma

Tüm ayarlar `config.py` dosyasında toplanmıştır:

| Ayar | Varsayılan | Açıklama |
|---|---|---|
| `LLM_MODEL` | `qwen2.5-0.5b` | Sohbet modeli |
| `EMBED_MODEL` | `qwen3-embedding-0.6b` | Embedding modeli |
| `CHUNK_BOYUTU` | 300 kelime | Bir chunk'ın en fazla kelime sayısı |
| `CHUNK_ORTUSME` | 50 kelime | Ardışık chunk'ların paylaştığı örtüşme |
| `EMBED_BATCH` | 4 | Tek istekte embedding üretilecek chunk sayısı |
| `TOP_K` | 3 | Bağlam olarak kullanılacak chunk sayısı |
| `MIN_SKOR` | 0.45 | Bu skorun altındaki chunk'lar ilgisiz sayılır |

Ayar değişikliklerinden sonra `python main.py --yukle` ile belgeleri
yeniden yükleyin (özellikle chunk ayarları değiştiyse).

## Testler

Birim testleri (model gerektirmez, mock'lu):

```bash
python -m pytest
```

Gerçek modellerle uçtan uca smoke testleri (modeller indirilmiş ve
veritabanı yüklenmiş olmalı):

```bash
python -m pytest -m smoke
```

Retrieval kalitesi ve "bilgi yok" davranışını ölçen değerlendirme seti:

```bash
python degerlendirme.py          # yalnızca retrieval (hızlı)
python degerlendirme.py --llm    # LLM cevaplarıyla birlikte
```

## Belge Ekleme / Güncelleme

Yeni belge ekledikten sonra yeniden yükleme yapın:

```bash
python main.py --yukle
```

Bu komut mevcut veritabanını temizler ve tüm belgeleri yeniden işler.

## Sık Karşılaşılan Sorunlar

| Sorun | Çözüm |
|---|---|
| `ModuleNotFoundError` | `pip install -r requirements.txt` çalıştırın |
| `foundry_local_sdk` bulunamadı | Sanal ortamı etkinleştirip `python -m pip install -r requirements.txt` çalıştırın |
| Model indirilmiyor | İlk kurulumda internet bağlantısını ve boş disk alanını kontrol edin |
| `Veritabani bos` mesajı | `python main.py --yukle` ile belgeleri yükleyin |
| İlk çalıştırma yavaş | Modeller indiriliyor ve donanıma uygun yürütme sağlayıcısı hazırlanıyor olabilir |
| Alakasız sonuçlar | `config.py`'daki `CHUNK_BOYUTU` ve `MIN_SKOR` değerlerini ayarlayın |
| "Bilgi yok" cevabı çok sık geliyor | `config.py`'daki `MIN_SKOR` eşiğini düşürün |
| Embedding üretiminde `Operation was cancelled` | `config.py`'daki `EMBED_BATCH` değerini küçültün |

## Teknolojiler

- **Microsoft Foundry Local** — offline LLM ve embedding
- **SQLite** — vektör ve metin depolama
- **NumPy** — cosine similarity hesabı
- **Qwen 2.5 0.5B** — yerel sohbet modeli
- **Qwen3 Embedding 0.6B** — yerel embedding modeli
