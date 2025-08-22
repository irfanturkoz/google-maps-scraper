#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from dotenv import load_dotenv
from google_maps_scraper import GoogleMapsScraper
import sys

def main():
    """
    Google Maps İşletme Bilgisi Çekme Programı
    """
    print("=" * 60)
    print("🗺️  GOOGLE MAPS İŞLETME BİLGİSİ ÇEKME PROGRAMI")
    print("=" * 60)
    
    # .env dosyasını yükle
    load_dotenv()
    
    # API anahtarını al
    api_key = os.getenv('GOOGLE_MAPS_API_KEY')
    
    if not api_key:
        print("❌ HATA: Google Maps API anahtarı bulunamadı!")
        print("📝 Lütfen .env dosyası oluşturun ve GOOGLE_MAPS_API_KEY değişkenini ekleyin.")
        print("💡 Örnek: GOOGLE_MAPS_API_KEY=your_api_key_here")
        print("\n🔗 API anahtarı almak için: https://developers.google.com/maps/documentation/places/web-service/get-api-key")
        return
    
    try:
        # Scraper'ı başlat
        scraper = GoogleMapsScraper(api_key)
        
        # Kullanıcıdan bilgileri al
        print("\n📍 Arama Bilgilerini Girin:")
        print("-" * 30)
        
        location = input("🌍 Lokasyon (örn: 'Istanbul, Turkey' veya 'Ankara Çankaya'): ").strip()
        if not location:
            print("❌ Lokasyon boş olamaz!")
            return
            
        business_type = input("🏢 İşletme türü (örn: 'güzellik merkezi', 'restoran', 'eczane'): ").strip()
        if not business_type:
            print("❌ İşletme türü boş olamaz!")
            return
            
        try:
            radius_km = float(input("📏 Arama yarıçapı (km) (örn: 5): ").strip())
            if radius_km <= 0:
                print("❌ Yarıçap 0'dan büyük olmalıdır!")
                return
        except ValueError:
            print("❌ Geçerli bir sayı girin!")
            return
            
        filename = input("📄 Excel dosya adı (örn: 'guzellik_merkezleri.xlsx') [Enter: otomatik]: ").strip()
        if not filename:
            # Otomatik dosya adı oluştur
            safe_location = location.replace(" ", "_").replace(",", "")
            safe_business = business_type.replace(" ", "_")
            filename = f"{safe_location}_{safe_business}_{radius_km}km.xlsx"
        
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        print("\n🔍 Arama başlatılıyor...")
        print(f"📍 Lokasyon: {location}")
        print(f"🏢 İşletme türü: {business_type}")
        print(f"📏 Yarıçap: {radius_km} km")
        print("-" * 50)
        
        # Arama yap
        businesses = scraper.search_businesses(location, business_type, radius_km)
        
        if businesses:
            print(f"✅ {len(businesses)} işletme bulundu!")
            
            # Excel'e kaydet
            full_path = os.path.join(os.getcwd(), filename)
            scraper.save_to_excel(businesses, filename)
            
            print(f"📁 Dosya konumu: {full_path}")
            
            # Özet bilgi göster
            print("\n📊 ÖZET BİLGİLER:")
            print("-" * 20)
            
            # Puan ortalaması
            ratings = [b['Puan'] for b in businesses if b['Puan'] != 'N/A']
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                print(f"⭐ Ortalama puan: {avg_rating:.1f}")
            
            # Telefonu olan işletme sayısı
            with_phone = len([b for b in businesses if b['Telefon'] != 'N/A'])
            print(f"📞 Telefonu olan işletme: {with_phone}/{len(businesses)}")
            
            # Website'si olan işletme sayısı
            with_website = len([b for b in businesses if b['Website'] != 'N/A'])
            print(f"🌐 Website'si olan işletme: {with_website}/{len(businesses)}")
            
        else:
            print("❌ Hiç işletme bulunamadı!")
            print("💡 Farklı arama terimleri veya daha geniş yarıçap deneyin.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Program kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {str(e)}")
        print("🔧 Lütfen API anahtarınızı ve internet bağlantınızı kontrol edin.")

if __name__ == "__main__":
    main()
