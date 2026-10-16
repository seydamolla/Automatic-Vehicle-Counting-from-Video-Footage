# Video Görüntülerinden Otomatik Araç Sayımı

Grup 31 (VisionFlow) için UA-DETRAC tabanlı araç sayım projesi. Sistem, hazır bir Ultralytics YOLO modeliyle araçları tespit eder, ByteTrack ile takip eder ve sanal çizgiyi geçen her aracı yönüne göre yalnızca bir kez sayar.

## İlk iki hafta çıktıları

- Problem, kapsam ve gereksinimler tanımlandı.
- UA-DETRAC veri seti için yerel klasör düzeni ve resmî indirme yönergesi eklendi.
- Sanal çizgi geçiş sayacı yazıldı.
- Düz geçiş, iki yön, çizgi titremesi, geri dönüş, çizgi dışı geçiş ve kimlik değişimi senaryoları için testler eklendi.
- YOLO + ByteTrack ile video üzerinde çalışıp işaretli MP4 ve CSV üreten başlangıç komutu eklendi.

## Kurulum

Python 3.11 veya daha yenisini kullanın.

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
pip install -e .
pytest
```

## Veri seti

Veri seti kurulumu için [data/README.md](data/README.md) dosyasını izleyin. Büyük görüntü/video arşivleri GitHub'a eklenmez; yalnızca yapılandırma, kod ve küçük lisansı uygun örnekler sürüm kontrolünde tutulur.

## Başlangıç demosu

```bash
python scripts/run_counter.py data/raw/example.mp4 --line 100 300 850 300
```

Çıktılar `outputs/annotated.mp4` ve `outputs/counts.csv` altında oluşur. İlk çalıştırmada Ultralytics seçili model ağırlığını indirebilir.

## Değerlendirme planı

Resmî UA-DETRAC 60/40 eğitim-test ayrımı korunur. Model, çözünürlük ve çizgi ayarları yalnızca eğitim videolarıyla seçilir; test videoları ayarlar dondurulduktan sonra bir kez çalıştırılır. Değerlendirme toplam ve video bazlı sayım hatası, eşleşme oranı ile üç koşunun ortanca FPS değerini raporlar.

## Kaynaklar

- [UA-DETRAC resmî proje sayfası](https://sites.google.com/view/daweidu/projects/ua-detrac)
- [Ultralytics](https://docs.ultralytics.com/)
Bilgisayar Mühendisliği Tasarım Dersi Projesi
