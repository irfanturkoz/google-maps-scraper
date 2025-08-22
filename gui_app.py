#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
from dotenv import load_dotenv
from google_maps_scraper import GoogleMapsScraper
import threading

class GoogleMapsGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗺️ Google Maps İşletme Bilgisi Çekme Programı")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # API anahtarını yükle
        load_dotenv()
        self.api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        
        self.create_widgets()
        
    def create_widgets(self):
        # Ana frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Başlık
        title_label = ttk.Label(main_frame, text="🗺️ Google Maps İşletme Bilgisi Çekme", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # İl seçimi
        ttk.Label(main_frame, text="🏙️ İl:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.il_var = tk.StringVar()
        self.il_combo = ttk.Combobox(main_frame, textvariable=self.il_var, width=40)
        self.il_combo['values'] = self.get_iller()
        self.il_combo.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        self.il_combo.bind('<<ComboboxSelected>>', self.on_il_selected)
        
        # İlçe seçimi
        ttk.Label(main_frame, text="🏘️ İlçe:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ilce_var = tk.StringVar()
        self.ilce_combo = ttk.Combobox(main_frame, textvariable=self.ilce_var, width=40)
        self.ilce_combo.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # İşletme türü
        ttk.Label(main_frame, text="🏢 İşletme Türü:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.business_var = tk.StringVar()
        self.business_combo = ttk.Combobox(main_frame, textvariable=self.business_var, width=40)
        self.business_combo['values'] = [
            'güzellik merkezi', 'restoran', 'eczane', 'market', 'berber', 
            'kuaför', 'cafe', 'hastane', 'klinik', 'diş hekimi', 'veteriner',
            'otomobil servisi', 'benzin istasyonu', 'otel', 'pansiyon',
            'spor salonu', 'fitness', 'okul', 'dershane', 'kırtasiye'
        ]
        self.business_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Yarıçap
        ttk.Label(main_frame, text="📏 Yarıçap (km):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.radius_var = tk.StringVar(value="3")
        radius_entry = ttk.Entry(main_frame, textvariable=self.radius_var, width=40)
        radius_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=5)
        
        # Dosya adı
        ttk.Label(main_frame, text="📄 Excel Dosya Adı:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.filename_var = tk.StringVar()
        filename_frame = ttk.Frame(main_frame)
        filename_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5)
        
        filename_entry = ttk.Entry(filename_frame, textvariable=self.filename_var)
        filename_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        browse_btn = ttk.Button(filename_frame, text="📁", width=3, 
                               command=self.browse_file)
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Arama butonu
        self.search_btn = ttk.Button(main_frame, text="🔍 Arama Başlat", 
                                    command=self.start_search, style="Accent.TButton")
        self.search_btn.grid(row=6, column=0, columnspan=2, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Sonuç alanı
        ttk.Label(main_frame, text="📊 Sonuçlar:").grid(row=8, column=0, sticky=tk.W, pady=(10, 5))
        
        # Text widget with scrollbar
        text_frame = ttk.Frame(main_frame)
        text_frame.grid(row=9, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.result_text = tk.Text(text_frame, height=10, width=60)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Grid weights
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(9, weight=1)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
    def get_iller(self):
        """Türkiye'nin illerini döndürür"""
        return [
            "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya",
            "Artvin", "Aydın", "Balıkesir", "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur",
            "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır", "Edirne",
            "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane",
            "Hakkari", "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu",
            "Kayseri", "Kırklareli", "Kırşehir", "Kocaeli", "Konya", "Kütahya", "Malatya",
            "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir", "Niğde", "Ordu",
            "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
            "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray",
            "Bayburt", "Karaman", "Kırıkkale", "Batman", "Şırnak", "Bartın", "Ardahan",
            "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
        ]
    
    def get_ilceler(self, il):
        """Seçilen ile göre ilçeleri döndürür (örnek olarak birkaç il)"""
        ilceler = {
            "İstanbul": ["Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", 
                        "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü",
                        "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt",
                        "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane",
                        "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer",
                        "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla", 
                        "Ümraniye", "Üsküdar", "Zeytinburnu"],
            "Ankara": ["Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya",
                      "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana",
                      "Kalecik", "Kazan", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan",
                      "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"],
            "İzmir": ["Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova",
                     "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe",
                     "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz",
                     "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar",
                     "Selçuk", "Tire", "Torbalı", "Urla"],
            "Mersin": ["Akdeniz", "Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli",
                      "Gülnar", "Mezitli", "Mut", "Silifke", "Tarsus", "Toroslar", "Yenişehir"]
        }
        return ilceler.get(il, [])
    
    def on_il_selected(self, event):
        """İl seçildiğinde ilçeleri güncelle"""
        il = self.il_var.get()
        ilceler = self.get_ilceler(il)
        self.ilce_combo['values'] = ilceler
        self.ilce_var.set("")
        
        # Otomatik dosya adı oluştur
        if il and self.business_var.get():
            self.update_filename()
    
    def update_filename(self):
        """Otomatik dosya adı oluştur"""
        il = self.il_var.get().replace(" ", "_")
        ilce = self.ilce_var.get().replace(" ", "_")
        business = self.business_var.get().replace(" ", "_")
        radius = self.radius_var.get()
        
        if il and business:
            if ilce:
                filename = f"{il}_{ilce}_{business}_{radius}km.xlsx"
            else:
                filename = f"{il}_{business}_{radius}km.xlsx"
            self.filename_var.set(filename)
    
    def browse_file(self):
        """Dosya kaydetme konumu seç"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            self.filename_var.set(filename)
    
    def start_search(self):
        """Arama işlemini başlat"""
        if not self.api_key:
            messagebox.showerror("Hata", "Google Maps API anahtarı bulunamadı!\n.env dosyasını kontrol edin.")
            return
        
        il = self.il_var.get().strip()
        ilce = self.ilce_var.get().strip()
        business_type = self.business_var.get().strip()
        
        if not il:
            messagebox.showerror("Hata", "Lütfen bir il seçin!")
            return
            
        if not business_type:
            messagebox.showerror("Hata", "Lütfen işletme türünü girin!")
            return
        
        try:
            radius_km = float(self.radius_var.get())
            if radius_km <= 0:
                messagebox.showerror("Hata", "Yarıçap 0'dan büyük olmalıdır!")
                return
        except ValueError:
            messagebox.showerror("Hata", "Geçerli bir yarıçap değeri girin!")
            return
        
        filename = self.filename_var.get().strip()
        if not filename:
            self.update_filename()
            filename = self.filename_var.get()
        
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        # Lokasyon string'i oluştur
        if ilce:
            location = f"{ilce}, {il}, Turkey"
        else:
            location = f"{il}, Turkey"
        
        # Arama işlemini thread'de çalıştır
        self.search_btn.config(state='disabled', text='🔍 Aranıyor...')
        self.progress.start()
        self.result_text.delete(1.0, tk.END)
        
        thread = threading.Thread(target=self.perform_search, 
                                args=(location, business_type, radius_km, filename))
        thread.daemon = True
        thread.start()
    
    def perform_search(self, location, business_type, radius_km, filename):
        """Arama işlemini gerçekleştir"""
        try:
            scraper = GoogleMapsScraper(self.api_key)
            
            self.update_result_text(f"🔍 Arama başlatılıyor...\n")
            self.update_result_text(f"📍 Lokasyon: {location}\n")
            self.update_result_text(f"🏢 İşletme türü: {business_type}\n")
            self.update_result_text(f"📏 Yarıçap: {radius_km} km\n")
            self.update_result_text("-" * 50 + "\n")
            
            businesses = scraper.search_businesses(location, business_type, radius_km)
            
            if businesses:
                self.update_result_text(f"✅ {len(businesses)} işletme bulundu!\n\n")
                
                # Excel'e kaydet
                scraper.save_to_excel(businesses, filename)
                full_path = os.path.abspath(filename)
                self.update_result_text(f"📁 Dosya kaydedildi: {full_path}\n\n")
                
                # Özet bilgiler
                self.update_result_text("📊 ÖZET BİLGİLER:\n")
                self.update_result_text("-" * 20 + "\n")
                
                # Puan ortalaması
                ratings = [b['Puan'] for b in businesses if b['Puan'] != 'N/A']
                if ratings:
                    avg_rating = sum(ratings) / len(ratings)
                    self.update_result_text(f"⭐ Ortalama puan: {avg_rating:.1f}\n")
                
                # İstatistikler
                with_phone = len([b for b in businesses if b['Telefon'] != 'N/A'])
                with_website = len([b for b in businesses if b['Website'] != 'N/A'])
                
                self.update_result_text(f"📞 Telefonu olan: {with_phone}/{len(businesses)}\n")
                self.update_result_text(f"🌐 Website'si olan: {with_website}/{len(businesses)}\n")
                
                messagebox.showinfo("Başarılı", f"{len(businesses)} işletme bulundu ve Excel dosyasına kaydedildi!")
                
            else:
                self.update_result_text("❌ Hiç işletme bulunamadı!\n")
                self.update_result_text("💡 Farklı arama terimleri veya daha geniş yarıçap deneyin.\n")
                messagebox.showwarning("Sonuç Yok", "Hiç işletme bulunamadı!")
                
        except Exception as e:
            error_msg = f"❌ Hata: {str(e)}\n"
            self.update_result_text(error_msg)
            messagebox.showerror("Hata", str(e))
        
        finally:
            # UI'yi güncelle
            self.root.after(0, self.search_completed)
    
    def update_result_text(self, text):
        """Result text'i güncelle (thread-safe)"""
        self.root.after(0, lambda: self.result_text.insert(tk.END, text))
        self.root.after(0, lambda: self.result_text.see(tk.END))
    
    def search_completed(self):
        """Arama tamamlandığında UI'yi güncelle"""
        self.progress.stop()
        self.search_btn.config(state='normal', text='🔍 Arama Başlat')

def main():
    root = tk.Tk()
    app = GoogleMapsGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
