# UA-DETRAC veri seti

Bu depo, UA-DETRAC'in büyük görüntü ve etiket arşivlerini Git'e koymaz. Veri seti 100 video ve 140.000'den fazla kare içerdiği için GitHub dosya boyutu sınırlarına uygun değildir. Resmî indirme bağlantıları için [UA-DETRAC proje sayfasını](https://sites.google.com/view/daweidu/projects/ua-detrac) kullanın.

İndirme sonrası aşağıdaki klasör yapısını oluşturun. `data/raw/` `.gitignore` içindedir; kişisel makinenizde kalır.

```text
data/raw/
  Insight-MVT_Annotation_Train/   # XML etiket dosyaları
  Insight-MVT_Annotation_Test/
  Insight-MVT_Train/              # MVI_* kare klasörleri
  Insight-MVT_Test/
```

Eğitim/test ayrımı veri setinin resmî 60/40 ayrımıdır. Değerlendirmede yalnızca `car`, `bus` ve `van`/`truck` benzeri etiketlenmiş araç sınıflarını kullanın; raporda belirtildiği gibi motosikletler kapsam dışıdır. Video veya kareleri GitHub'a yüklemeyin. Küçük, paylaşılabilir test örnekleri gerekiyorsa lisansını doğrulayarak `data/sample/` içine ekleyin.

