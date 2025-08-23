import googlemaps
import pandas as pd
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
import time

class GoogleMapsScraper:
    def __init__(self, api_key: str):
        """
        Google Maps API kullanarak işletme bilgilerini çeken sınıf
        
        Args:
            api_key (str): Google Maps API anahtarı
        """
        self.gmaps = googlemaps.Client(key=api_key)
        
    def search_businesses(self, location: str, business_type: str, radius_km: float) -> List[Dict]:
        """
        Belirtilen lokasyon ve yarıçapta işletmeleri arar
        
        Args:
            location (str): Arama yapılacak lokasyon
            business_type (str): İşletme türü
            radius_km (float): Arama yarıçapı (km)
            
        Returns:
            List[Dict]: İşletme listesi
        """
        try:
            # Lokasyonun koordinatlarını al
            geocode_result = self.gmaps.geocode(location)
            if not geocode_result:
                print(f"Lokasyon bulunamadı: {location}")
                return []
            
            lat = geocode_result[0]['geometry']['location']['lat']
            lng = geocode_result[0]['geometry']['location']['lng']
            
            businesses = []
            seen_place_ids = set()
            
            # 1. Nearby Search - Google Places type ile
            place_type = self._get_place_type(business_type)
            places_result = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=int(radius_km * 1000),
                type=place_type
            )
            
            # İlk sayfa sonuçları
            for place in places_result.get('results', []):
                place_id = place.get('place_id')
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    business_details = self._get_business_details(place_id)
                    if business_details and self._is_in_target_location(business_details, location):
                        businesses.append(business_details)
            
            # 2. Nearby Search - keyword ile (ek arama)
            places_result2 = self.gmaps.places_nearby(
                location=(lat, lng),
                radius=int(radius_km * 1000),
                keyword=business_type
            )
            
            for place in places_result2.get('results', []):
                place_id = place.get('place_id')
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    business_details = self._get_business_details(place_id)
                    if business_details and self._is_in_target_location(business_details, location):
                        businesses.append(business_details)
            
            # 3. Text Search - daha geniş arama
            text_search_results = self._text_search(location, business_type, radius_km)
            for result in text_search_results[:20]:  # Daha fazla sonuç
                place_id = result.get('place_id')
                if place_id and place_id not in seen_place_ids:
                    seen_place_ids.add(place_id)
                    business_details = self._get_business_details(place_id)
                    if business_details and self._is_in_target_location(business_details, location):
                        businesses.append(business_details)
            
            # 4. Alternatif text search sorguları
            alternative_queries = [
                f"{business_type} {location}",
                f"{location} {business_type}",
                f"{business_type} in {location}"
            ]
            
            for query in alternative_queries:
                try:
                    alt_results = self.gmaps.places(query=query)
                    for result in alt_results.get('results', [])[:15]:
                        place_id = result.get('place_id')
                        if place_id and place_id not in seen_place_ids:
                            seen_place_ids.add(place_id)
                            business_details = self._get_business_details(place_id)
                            if business_details and self._is_in_target_location(business_details, location):
                                businesses.append(business_details)
                except:
                    continue
                
            return businesses
            
        except Exception as e:
            print(f"Arama sırasında hata: {str(e)}")
            return []
    
    def _get_place_type(self, business_type: str) -> str:
        """İşletme türüne göre Google Places type döndür"""
        type_mapping = {
            'hastane': 'hospital',
            'şehir hastanesi': 'hospital',
            'devlet hastanesi': 'hospital',
            'özel hastane': 'hospital',
            'klinik': 'hospital',
            'sağlık merkezi': 'hospital',
            'eczane': 'pharmacy',
            'restoran': 'restaurant',
            'lokanta': 'restaurant',
            'cafe': 'cafe',
            'kahve': 'cafe',
            'market': 'supermarket',
            'süpermarket': 'supermarket',
            'bakkal': 'grocery_or_supermarket',
            'berber': 'hair_care',
            'kuaför': 'hair_care',
            'güzellik merkezi': 'beauty_salon',
            'güzellik salonu': 'beauty_salon',
            'otel': 'lodging',
            'pansiyon': 'lodging',
            'benzin istasyonu': 'gas_station',
            'petrol': 'gas_station',
            'banka': 'bank',
            'atm': 'atm',
            'okul': 'school',
            'lise': 'school',
            'ilkokul': 'school',
            'üniversite': 'university',
            'spor salonu': 'gym',
            'fitness': 'gym'
        }
        
        business_lower = business_type.lower()
        for key, value in type_mapping.items():
            if key in business_lower:
                return value
        return 'establishment'
    
    def _text_search(self, location: str, business_type: str, radius_km: float) -> List[Dict]:
        """Text search ile ek arama yap"""
        try:
            # Birden fazla sorgu formatı dene
            queries = [
                f"{business_type} near {location}",
                f"{business_type} {location}",
                f"{location} {business_type}"
            ]
            
            all_results = []
            for query in queries:
                try:
                    text_results = self.gmaps.places(query=query)
                    results = text_results.get('results', [])
                    all_results.extend(results)
                except:
                    continue
                    
            return all_results
        except:
            return []
    
    def _is_in_target_location(self, business_details: Dict, target_location: str) -> bool:
        """İşletmenin hedef lokasyonda olup olmadığını kontrol et"""
        try:
            business_address = business_details.get('Adres', '').lower()
            target_location_lower = target_location.lower()
            
            # Hedef lokasyondan bölümleri çıkar
            target_parts = target_location_lower.split(',')
            
            # Tüm parçaları kontrol et
            for part in target_parts:
                part = part.strip()
                if part and part in business_address:
                    return True
            
            # Eğer virgül yoksa, direkt kontrol et
            if ',' not in target_location_lower:
                if target_location_lower in business_address:
                    return True
                    
                # Başakşehir gibi özel durumlar için kelime bazlı kontrol
                target_words = target_location_lower.split()
                for word in target_words:
                    if len(word) > 3 and word in business_address:  # Kısa kelimelerden kaçın
                        return True
            
            return True  # Şüpheli durumlarda dahil et (daha fazla sonuç için)
        except:
            # Hata durumunda işletmeyi dahil et
            return True
    
    def _get_business_details(self, place_id: str) -> Optional[Dict]:
        """
        İşletmenin detaylı bilgilerini alır
        
        Args:
            place_id (str): Google Places ID
            
        Returns:
            Dict: İşletme detayları
        """
        try:
            # Detaylı bilgileri al
            place_details = self.gmaps.place(
                place_id=place_id,
                fields=[
                    'name', 'formatted_address', 'formatted_phone_number',
                    'website', 'business_status'
                ]
            )
            
            result = place_details.get('result', {})
            
            
            # Telefon numarası yoksa işletmeyi dahil etme
            phone_number = result.get('formatted_phone_number', 'N/A')
            if phone_number == 'N/A' or not phone_number:
                return None
            
            business_info = {
                'İşletme Adı': result.get('name', 'N/A'),
                'Adres': result.get('formatted_address', 'N/A'),
                'Telefon': phone_number,
                'Website': result.get('website', 'N/A'),
                'Durum': result.get('business_status', 'N/A')
            }
            
            return business_info
            
        except Exception as e:
            print(f"İşletme detayları alınırken hata: {str(e)}")
            return None
    
    def save_to_excel(self, businesses: List[Dict], filename: str = "isletmeler.xlsx"):
        """
        İşletme bilgilerini Excel dosyasına kaydeder
        
        Args:
            businesses (List[Dict]): İşletme bilgileri listesi
            filename (str): Kaydedilecek dosya adı
        """
        try:
            if not businesses:
                print("Kaydedilecek işletme bulunamadı.")
                return
                
            df = pd.DataFrame(businesses)
            
            # Excel dosyasına kaydet
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='İşletmeler', index=False)
                
                # Sütun genişliklerini ayarla
                worksheet = writer.sheets['İşletmeler']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ {len(businesses)} işletme bilgisi '{filename}' dosyasına kaydedildi.")
            
        except Exception as e:
            print(f"Excel dosyası kaydedilirken hata: {str(e)}")
