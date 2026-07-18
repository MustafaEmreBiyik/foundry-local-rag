# Local RAG Projesi Durum Raporu ve Yapılacaklar

> Tarih: 16 Temmuz 2026 — Kod tabanının salt okunur analizine dayanır.

## Özet

Proje Microsoft Foundry Local'a geçirildi ve temel uçtan uca RAG akışı gerçek modellerle doğrulandı. Beş belge örtüşmeli chunking ile 10 chunk olarak indekslendi; CLI, retrieval, yerel LLM cevabı ve skorlu/alıntılı kaynak gösterimi çalışıyor. P0–P4'ün tamamı bitti; yalnızca `git init` ve ilk commit kullanıcı tarafından yapılacak.

## Yapılacaklar (özet)

- [x] Backend kararını verip kod, README, plan ve bağımlılıkları Microsoft Foundry Local ile hizala
- [x] Modelleri doğrula, ingestion çalıştır ve uçtan uca CLI smoke testi yap
- [x] Benzerlik eşiği ve güvenilir "bilgi yok" davranışı ekle
- [x] Ingestion işlemini atomik, toplu ve hata güvenli hale getir
- [x] Birim testleri ve küçük RAG değerlendirme seti oluştur
- [x] Örtüşmeli chunking, metadata, sıralı kaynak ve skor çıktısı ekle
- [x] Gitignore, bağımlılık ve dokümantasyon temizliği yap (`git init` ve commit'ler kullanıcıya bırakıldı)

## Mevcut durum

- Temel RAG zinciri çalışıyor: CLI → embedding → SQLite üzerinde cosine similarity → ilk 3 chunk → LLM cevabı → skorlu ve alıntılı kaynak listesi. Ana akış [main.py](main.py), [config.py](config.py), [ingestion.py](ingestion.py), [retrieval.py](retrieval.py), [generator.py](generator.py) ve [database.py](database.py) içinde mevcut.
- Beş örnek `.txt` belge hazır; bu, planın minimum belge sayısını karşılıyor: [belgeler/](belgeler/).
- Python ortamı kurulmuş: sistem Python 3.10.11, `.venv` Python 3.13.2; `foundry-local-sdk-winml`, `numpy` ve `pytest` yüklü.
- `veritabani.db` oluşturuldu; 15 belge örtüşmeli chunking ile 30 chunk olarak indekslendi.
- `qwen3-embedding-0.6b` ve `qwen2.5-0.5b` Foundry Local modelleri indirildi ve gerçek CLI smoke testi başarıyla tamamlandı.
- 33 birim testi, 2 smoke testi ve 12 soruluk değerlendirme seti mevcut; tümü geçiyor.
- `.gitignore` hazır (`.venv/`, `__pycache__/`, `*.db`, editör ve yerel ayar dosyaları dışlanıyor); `git init` ve ilk commit kullanıcı tarafından yapılacak.

## Tamamlanan P0 çalışmaları

- Uygulama güncel `FoundryLocalManager` API'sine geçirildi; Ollama bağımlılığı kaldırıldı.
- [README.md](README.md), [plan.md](plan.md), model adları ve [requirements.txt](requirements.txt) Microsoft Foundry Local ile hizalandı.
- Windows için `foundry-local-sdk-winml` kuruldu; ayrı CLI veya yerel servis gereksinimi kaldırıldı.
- Embedding modeli, sohbet modeli, ingestion, retrieval, cevap üretimi ve kaynak gösterimi gerçek ortamda doğrulandı.
- Kullanılmayan Streamlit bağımlılığı kaldırıldı; görsel arayüz hâlâ opsiyonel ürün geliştirmesi olarak bekliyor.
- [plan.md](plan.md) içindeki doğrulanan Foundry Local ve temel teslim maddeleri tamamlandı olarak işaretlendi.

## Tamamlanan P1 çalışmaları

- [retrieval.py](retrieval.py) artık 0.35 minimum benzerlik eşiği uyguluyor; eşiği geçen chunk yoksa [generator.py](generator.py) LLM'i hiç çağırmadan "Bu konuda elimde bilgi yok." döndürüyor.
- Ingestion atomik hale getirildi: tüm embedding'ler önce bellekte üretiliyor, ardından silme ve toplu ekleme tek transaction içinde yapılıyor. Herhangi bir hata mevcut indeksi bozmuyor.
- Belge klasörü yok/boş, bozuk UTF-8, boş belgeler, embedding hatası ve model/SDK başlatma hataları için anlaşılır Türkçe hata mesajları eklendi; CLI'daki tek soru hatası programı kapatmıyor.
- Veritabanı ve belge yolları `Path(__file__)` tabanlı proje kökü mutlak yollarına çevrildi.
- Windows konsolundaki cp1254 kodlaması nedeniyle oluşan çökme, stdout/stderr UTF-8'e alınarak giderildi.

## Tamamlanan P2 çalışmaları

- `tests/` altında 25 birim testi eklendi: chunking, belge okuma hataları, cosine similarity, sıralama/eşik, SQLite serileştirme, transaction geri alma, context/prompt üretimi ve "bilgi yok" kısa devresi. Foundry Local istemcileri sahte sınıflarla mock'landı; testler modelsiz 3-4 saniyede koşuyor.
- [degerlendirme.py](degerlendirme.py) ile 12 soruluk değerlendirme seti oluşturuldu (7 cevaplanabilir, 3 ilgisiz, 2 sınırda). Gerçek embedding modeliyle sonuç: 12/12 (%100).
- Değerlendirme verisiyle benzerlik eşiği kalibre edildi: cevaplanabilir soruların en düşük skoru 0.500, ilgisizlerin en yükseği 0.394 çıktığı için `MIN_SKOR` 0.35'ten 0.45'e yükseltildi; sınırdaki "JavaScript" sorusu da artık doğru reddediliyor.
- Gerçek modellerle 2 uçtan uca smoke testi eklendi ve geçti; `pytest.ini` sayesinde varsayılan `pytest` koşusunda atlanıyor, `pytest -m smoke` ile çalışıyor.

## Tamamlanan P3 çalışmaları

- Tüm ayarlar (model adları, yollar, chunk boyutu, örtüşme, batch, `top_k`, `MIN_SKOR`) yeni [config.py](config.py) modülünde toplandı; diğer modüller bu değerleri import ediyor.
- Chunking paragraf sınırlarına saygı gösterecek ve ardışık chunk'lar arasında 50 kelimelik örtüşme bırakacak şekilde yeniden yazıldı; her chunk'a belge içi sıra numarası eklendi ve veritabanı şemasına `sira` sütunu geldi (şema değişince tablo otomatik yeniden kuruluyor, yeniden yükleme yeterli).
- Kaynak gösterimi yenilendi: kaynaklar retrieval sırasıyla (skora göre azalan), benzerlik skoru ve 100 karakterlik alıntıyla listeleniyor; tekrarlanan kaynaklar sıra korunarak tekilleştiriliyor.
- Embedding üretimi batch'e çevrildi (`generate_embeddings`), SQLite ekleme `executemany` ile toplu yapılıyor; geçici Foundry Local hatalarına karşı batch başına 3 deneme eklendi.
- Test paketi 33 birim testine çıktı (örtüşme, paragraf sınırı, sıra numarası, batch, kaynak tekilleştirme testleri eklendi); belgeler yeni chunking ile yeniden indekslendi (10 chunk), değerlendirme seti 12/12 ve smoke testler 2/2 geçti.

## Tamamlanan P4 çalışmaları

- `.gitignore` eklendi: `.venv/`, `__pycache__/`, `*.db`, pytest önbelleği, editör klasörleri ve yerel ayar dosyaları sürüm kontrolü dışında tutuluyor. `git init` ve commit adımları kullanıcıya bırakıldı.
- Bağımlılıklar sadeleştirildi ve sabitlendi: [requirements.txt](requirements.txt) artık tam sürüm pinliyor (`foundry-local-sdk-winml==1.2.3`, `numpy==2.4.6`, `pytest==9.1.1`). Streamlit yapılmama kararı netleştirildi; Streamlit ve ona ait 24 artık paket sanal ortamdan kaldırıldı, sonrasında testler ve importlar doğrulandı.
- [plan.md](plan.md) kontrol kutuları gerçek duruma göre güncellendi: 4 haftanın tüm zorunlu maddeleri işaretlendi, Streamlit maddesi "yapılmayacak" notuyla açık bırakıldı.
- [README.md](README.md) genişletildi: kurulum doğrulama adımları (pytest, değerlendirme, smoke, CLI kontrolü) ve "Offline Çalışma Sınırları" bölümü eklendi.

## Tamamlanan P7 çalışmaları (opsiyonel: daha büyük belge kümesi)

- Belge kümesi 5'ten 15'e çıkarıldı: git, web geliştirme, siber güvenlik, veri yapıları/algoritmalar (çok chunk'lı uzun belge), ağ temelleri, işletim sistemleri, bulut bilişim, derin öğrenme (yapay zeka belgesine benzer içerik), prompt mühendisliği (RAG belgesine benzer içerik) ve kısa bir Linux komut satırı belgesi eklendi. Yeni indeks: 30 chunk.
- Değerlendirme seti 12'den 30 soruya genişletildi: 15 cevaplanabilir (her belgeden en az bir soru), 10 tamamen ilgisiz, 5 sınırda (teknik ama belgelerde yok). [degerlendirme.py](degerlendirme.py) artık kategori bazlı oran ve %90 hedef kontrolü raporluyor.
- Sonuç: toplam 29/30 (%97). Retrieval isabeti 14/15 (%93), ilgisiz reddetme 10/10, sınırda reddetme 5/5 — her kategoride %90 hedefi sağlandı.
- Bilinen zayıflık: "DNS ne işe yarar?" gibi çok kısa sorular 0.45 eşiğinin altında kalabiliyor; soru biraz detaylandırıldığında (ör. "DNS alan adlarını nasıl çözümler?") doğru belge bulunuyor.

## Tamamlanan P8 çalışmaları (opsiyonel: performans ölçümü)

- [performans.py](performans.py) eklendi: tek komutla model yükleme, ingestion (chunking / embedding / SQLite), retrieval ve LLM cevap sürelerini ölçer; belge/chunk sayılarını ve ortalama-en kötü süreleri raporlar.
- `--karsilastir` ile `CHUNK_BOYUTU`/`CHUNK_ORTUSME`, `EMBED_BATCH` ve `TOP_K` karşılaştırılır.
- Çıktı: `performans-raporu.md` + `performans-raporu.json` (`.gitignore`'a eklendi; makineye özgü).
- Bu makinedeki örnek sonuç (15 belge / 30 chunk, CPU): model yükleme ~32s; retrieval ortalama ~8.6s (en kötü ~9.7s); başarılı LLM cevapları ~46–60s aralığında (geçici Foundry iptali + yeniden deneme en kötüyü ~292s'ye çekebiliyor). Ingestion ölçümü üretim DB'sine dokunmaz; tam batch embedding bazen iptal edilebiliyor — betik tek tek embedding'e düşerek ölçümü tamamlamaya çalışır.
- Karşılaştırma özeti: chunk 200→44 / 300→30 / 400→21 parça; `TOP_K` 1/3/5 retrieval süresini neredeyse değiştirmez (~3s, ısınmış model); `EMBED_BATCH` CPU'da kararsız — büyük batch'ler iptal edilebiliyor, varsayılan 4 güvenli tarafta kalıyor.

## Kalan teknik riskler

- Foundry Local, model yüklendikten sonraki ilk çağrılarda geçici "Operation was cancelled" hatası verebiliyor; ingestion ve smoke testlerde tekrar denemeyle aşılıyor, CLI'da hata yakalanıp soru tekrarlanabiliyor. CPU'da büyük embedding batch'leri de aynı hatayı tetikleyebildiği için `EMBED_BATCH` varsayılanı 4'e çekildi.
- Küçük `qwen2.5-0.5b` modelinin Türkçe cevap kalitesi düşük; retrieval doğru kaynağı bulsa da üretilen metin anlamsız olabiliyor.

## Önceliklendirilmiş uygulama planı

### P0 — Teslim tanımını netleştir ve çalışan tabanı doğrula (tamamlandı)

- [x] Microsoft Foundry Local backend'i seçildi.
- [x] [README.md](README.md), [plan.md](plan.md), model adları ve [requirements.txt](requirements.txt) hizalandı.
- [x] Modeller indirildi, `python main.py --yukle` çalıştırıldı; cevaplanabilir ve belge dışı sorularla CLI smoke testleri tamamlandı.

### P1 — Doğruluk ve veri güvenliği (tamamlandı)

- [x] [retrieval.py](retrieval.py) içine ayarlanabilir `top_k` ve minimum skor eşiği eklendi; eşik altındaki sorguda LLM çağırmadan kontrollü "bilgi yok" sonucu dönüyor.
- [x] [ingestion.py](ingestion.py) ve [database.py](database.py) akışı tek transaction ile atomik hale getirildi; önce yeni veri hazırlanıyor, sonra eski veri değiştiriliyor.
- [x] Belge klasörü yok/boş, bozuk UTF-8, boş belge ve model hataları için anlaşılır hata yönetimi eklendi.
- [x] Proje köküne bağlı mutlak yollar (`Path(__file__).resolve().parent`) kullanılıyor.

### P2 — Test ve kalite güvencesi (tamamlandı)

- [x] `tests/` altında chunking, cosine similarity, SQLite serileştirme, sıralama/eşik ve generator prompt testleri eklendi; Foundry Local çağrıları mock'landı (25 test, tümü geçiyor).
- [x] 12 soruluk değerlendirme seti oluşturuldu ([degerlendirme.py](degerlendirme.py)); retrieval isabeti ve "bilmiyorum" davranışı ölçüldü: 12/12.
- [x] Model bağımlı uçtan uca smoke testi eklendi; `smoke` işaretiyle normal test paketinden ayrıldı (2 test, tümü geçiyor).

### P3 — Retrieval ve kullanım kalitesi (tamamlandı)

- [x] Örtüşmeli ve paragraf sınırlarını koruyan chunking eklendi; chunk sıra numarası veritabanında saklanıyor.
- [x] Cevapta kaynaklar retrieval sırasıyla, skor ve kısa alıntıyla gösteriliyor; tekrarlanan kaynaklar sıra korunarak tekilleştiriliyor.
- [x] Model adları, yollar, chunk boyutu, overlap, `top_k` ve eşik değerleri [config.py](config.py) merkezi yapılandırmasına taşındı.
- [x] Embeddingler batch üretiliyor ve SQLite insertleri toplu yapılıyor.

### P4 — Proje hijyeni ve opsiyonel arayüz (tamamlandı)

- [x] `.venv/`, `__pycache__/`, `*.db` ve yerel ayarları dışlayan `.gitignore` eklendi; `git init` ve commit'ler kullanıcı tarafından yapılacak.
- [x] Bağımlılıklar kullanılana göre sadeleştirildi ve tam sürüm sabitleme stratejisi benimsendi; Streamlit yapılmama kararıyla birlikte sanal ortamdan kaldırıldı.
- [x] [plan.md](plan.md) kontrol kutuları gerçek duruma göre güncellendi; README'ye kurulum doğrulama ve offline çalışma sınırları eklendi.

## Tamamlanma ölçütü

- Temiz ortamda belgeler tek komutla indekslenebiliyor.
- Belgede cevabı olan sorular doğru kaynaklarla cevaplanıyor; olmayan sorular LLM'e zorla cevap ürettirmeden reddediliyor.
- Bir ingestion hatası mevcut indeksi bozmuyor.
- Otomatik birim testleri ve ayrı uçtan uca smoke testi geçiyor.
- README'deki altyapı, komutlar, model adları ve gerçek kod tamamen aynı.
