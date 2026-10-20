# Video Görüntülerinden Otomatik Araç Sayımı

Grup 31 (VisionFlow) için geliştirilen bu uygulama, yüklenen trafik videolarındaki otomobil, otobüs ve kamyonları hazır YOLO modeliyle tespit eder, ByteTrack ile izler ve kullanıcı tarafından belirlenen sanal çizgiyi geçen araçları iki yönde ayrı ayrı sayar.

## Çalışan özellikler

- Aynı işlemde 1-5 video yükleme
- Video önizlemesi üzerinde sürüklenebilir sayım çizgisi
- YOLO11n, YOLO11s veya YOLO11m model seçimi
- ByteTrack ile araç kimliği takibi
- Her takip kimliğini yalnızca ilk çizgi geçişinde sayma
- Pozitif, negatif ve toplam sayaçlar
- İşaretli MP4 ve geçiş ayrıntılarını içeren CSV çıktısı
- Dosya türü, çizgi ve yükleme boyutu doğrulaması
- Komut satırı ve web arayüzü desteği

## Windows'ta hızlı başlangıç

Python 3.11 kurulu olmalıdır. PowerShell'de proje klasörüne geçip aşağıdaki komutu çalıştırın:

```powershell
.\start.ps1
```

İlk kurulumda Python paketleri ve ilk çalıştırmada seçilen model ağırlığı indirilir. Sunucu açıldığında tarayıcıdan `http://127.0.0.1:8000` adresine gidin.

## Elle kurulum

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m uvicorn vehicle_counter.app:app --host 127.0.0.1 --port 8000
```

## Kullanım

1. Bir veya birkaç trafik videosu seçin.
2. İlk videonun önizlemesindeki sarı çizginin uçlarını sürükleyin.
3. Gerekirse model ve güven eşiğini değiştirin.
4. **Araç sayımını başlat** düğmesine basın.
5. Her video için yön sayaçlarını inceleyin; işaretli videoyu ve CSV dosyasını indirin.

Çizgi koordinatları normalize edildiği için aynı konum, farklı çözünürlükteki tüm yüklü videolara ölçeklenir. En doğru sonuç için videoların benzer kamera açısından çekilmiş olması önerilir.

## Komut satırı

```powershell
.\.venv\Scripts\python.exe scripts\run_counter.py data\raw\ornek.mp4 --line 0.1 0.65 0.9 0.65
```

Komut satırındaki çizgi koordinatları 0 ile 1 arasındadır. Çıktılar varsayılan olarak `outputs/cli` klasörüne yazılır.

## Test ve kalite kontrolleri

Geliştirme bağımlılıklarını kurduktan sonra:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m black --check src tests scripts
.\.venv\Scripts\python.exe -m mypy src
```

Otomatik testlerde çizgi geçişinin altı kabul senaryosu ve iki videolu web iş akışı model indirmeden doğrulanır.

## Veri seti ve değerlendirme

UA-DETRAC'ın resmî 60 eğitim / 40 test video ayrımı korunur. Ayarlar eğitim videolarında belirlenir; test videoları ayarlar dondurulduktan sonra değerlendirilir. Kapsam otomobil, otobüs ve kamyondur; UA-DETRAC etiketlerinde bulunmayan motosikletler değerlendirme dışıdır.

Değerlendirmede toplam sayım hatası, video bazlı hata, eşleşen çizgi geçişlerinin kesinlik/duyarlılık/F1 değerleri ve üç çalıştırmanın ortanca FPS değeri raporlanacaktır.

## Proje yapısı

- `src/vehicle_counter/counter.py`: deterministik çizgi geçiş mantığı
- `src/vehicle_counter/processing.py`: YOLO, ByteTrack, video ve CSV üretimi
- `src/vehicle_counter/app.py`: web servisi ve yükleme API'si
- `web/`: kullanıcı arayüzü
- `tests/`: birim ve uçtan uca API testleri
- `data/README.md`: UA-DETRAC veri düzeni

## Notlar

- İlk model çalıştırması internet bağlantısı gerektirir; ağırlık dosyası daha sonra önbellekten kullanılır.
- GPU varsa Ultralytics otomatik olarak kullanabilir; CPU'da da çalışır ancak daha yavaştır.
- Büyük veri setleri ve model ağırlıkları GitHub deposuna eklenmez.

## Kaynaklar

- [UA-DETRAC resmî proje sayfası](https://sites.google.com/view/daweidu/projects/ua-detrac)
- [Ultralytics dokümantasyonu](https://docs.ultralytics.com/)
- [ByteTrack makalesi](https://arxiv.org/abs/2110.06864)
