# Google Maps İşletme Bilgisi Çekme Programı

Bu program Google Maps API kullanarak belirtilen lokasyon ve yarıçapta işletme bilgilerini çeker ve Excel dosyasına kaydeder.

## 🚀 Kurulum

### 1. Gerekli Paketleri Yükleyin
```bash
pip install -r requirements.txt
```

### 2. Google Maps API Anahtarı Alın
1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. Yeni bir proje oluşturun veya mevcut projeyi seçin
3. "APIs & Services" > "Library" bölümünden **Places API** ve **Geocoding API**'yi etkinleştirin
4. "APIs & Services" > "Credentials" bölümünden API anahtarı oluşturun

### 3. Çevre Değişkenlerini Ayarlayın
`.env.example` dosyasını `.env` olarak kopyalayın ve API anahtarınızı ekleyin:
```bash
copy .env.example .env
```

`.env` dosyasını düzenleyin:
```
GOOGLE_MAPS_API_KEY=buraya_api_anahtarinizi_yazin
```

## 📖 Kullanım

### Programı Çalıştırma
```bash
python main.py
```

### Adım Adım Kullanım
1. **Lokasyon girin**: "Istanbul, Kadıköy" veya "Ankara, Çankaya"
2. **İşletme türü girin**: "güzellik merkezi", "restoran", "eczane"
3. **Yarıçap girin**: Km cinsinden (örn: 3)
4. **Dosya adı**: İsteğe bağlı (boş bırakılırsa otomatik oluşur)

### Örnek Kullanım
```
🌍 Lokasyon: Istanbul, Beyoğlu
🏢 İşletme türü: güzellik merkezi
📏 Arama yarıçapı: 5
📄 Excel dosya adı: beyoglu_guzellik.xlsx
```

## 📊 Excel Çıktısı

Program şu bilgileri kaydeder:

| Sütun | Açıklama |
|-------|----------|
| İşletme Adı | İşletmenin tam adı |
| Adres | Tam adres bilgisi |
| Telefon | İletişim numarası |
| Website | Web sitesi adresi |
| Puan | Google puanı (1-5) |
| Değerlendirme Sayısı | Toplam değerlendirme |
| Fiyat Seviyesi | Fiyat kategorisi (1-4) |
| Çalışma Saatleri | Haftalık çalışma saatleri |
| Enlem/Boylam | GPS koordinatları |
| İşletme Türleri | Google kategorileri |
| Durum | İşletme durumu |

## 🔧 Teknik Özellikler

- **API Limitler**: Günlük kullanım limitleri geçerli
- **Sonuç Sayısı**: Maksimum 60 işletme (3 sayfa)
- **Bekleme Süresi**: API çağrıları arası 2 saniye
- **Hata Yönetimi**: Kapsamlı hata kontrolü

## 💡 Kullanım İpuçları

### Daha İyi Sonuçlar İçin:
- Spesifik lokasyon kullanın
- Türkçe arama terimleri tercih edin
- Uygun yarıçap seçin (2-5 km ideal)

### Maliyet Optimizasyonu:
- Gereksiz aramalardan kaçının
- Yarıçapı makul tutun
- Tekrar aramaları önleyin

## 🐛 Sorun Giderme

### Yaygın Hatalar:
- **"API key not found"** → `.env` dosyasını kontrol edin
- **"Location not found"** → Lokasyon adını netleştirin
- **"No results found"** → Arama terimini değiştirin

### Destek:
Sorunlarınız için issue açabilirsiniz.

---
**Hazır! Programınızı kullanmaya başlayabilirsiniz! 🚀**
