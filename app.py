#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, render_template, request, jsonify, send_file, url_for, redirect, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
import uuid
import threading
import time
from datetime import datetime
from dotenv import load_dotenv
from google_maps_scraper import GoogleMapsScraper
from database import Database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

load_dotenv()

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Bu sayfaya erişmek için giriş yapmalısınız.'

# Database setup
db = Database()

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.username = user_data['username']
        self.is_admin = user_data['is_admin']
        self.expiry_date = user_data['expiry_date']
        self.days_left = user_data['days_left']

@login_manager.user_loader
def load_user(user_id):
    # Kullanıcıyı veritabanından yükle
    conn = db.db_path
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, is_admin, expiry_date
        FROM users WHERE id = ? AND is_active = 1
    ''', (int(user_id),))
    
    user_row = cursor.fetchone()
    conn.close()
    
    if user_row:
        user_id, username, is_admin, expiry_date = user_row
        expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
        days_left = (expiry - datetime.now().date()).days
        
        if days_left > 0:  # Sadece süresi dolmamış kullanıcıları yükle
            return User({
                'id': user_id,
                'username': username,
                'is_admin': bool(is_admin),
                'expiry_date': expiry_date,
                'days_left': days_left
            })
    
    return None

# Dosya depolama dizini
UPLOAD_FOLDER = 'downloads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Aktif işlemler için dictionary
active_jobs = {}

class SearchJob:
    def __init__(self, job_id, location, business_type, radius_km):
        self.job_id = job_id
        self.location = location
        self.business_type = business_type
        self.radius_km = radius_km
        self.status = 'pending'  # pending, running, completed, error
        self.progress = 0
        self.result_count = 0
        self.filename = None
        self.error_message = None
        self.start_time = time.time()

def get_iller():
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

def get_ilceler(il):
    """Seçilen ile göre ilçeleri döndürür"""
    ilceler = {
        "Adana": ["Aladağ", "Ceyhan", "Çukurova", "Feke", "İmamoğlu", "Karaisalı", "Karataş", "Kozan", "Pozantı", "Saimbeyli", "Sarıçam", "Seyhan", "Tufanbeyli", "Yumurtalık", "Yüreğir"],
        "Adıyaman": ["Besni", "Çelikhan", "Gerger", "Gölbaşı", "Kahta", "Merkez", "Samsat", "Sincik", "Tut"],
        "Afyonkarahisar": ["Başmakçı", "Bayat", "Bolvadin", "Çay", "Çobanlar", "Dazkırı", "Dinar", "Emirdağ", "Evciler", "Hocalar", "İhsaniye", "İscehisar", "Kızılören", "Merkez", "Sandıklı", "Sinanpaşa", "Sultandağı", "Şuhut"],
        "Ağrı": ["Diyadin", "Doğubayazıt", "Eleşkirt", "Hamur", "Merkez", "Patnos", "Taşlıçay", "Tutak"],
        "Amasya": ["Göynücek", "Gümüşhacıköy", "Hamamözü", "Merkez", "Merzifon", "Suluova", "Taşova"],
        "Ankara": ["Akyurt", "Altındağ", "Ayaş", "Bala", "Beypazarı", "Çamlıdere", "Çankaya", "Çubuk", "Elmadağ", "Etimesgut", "Evren", "Gölbaşı", "Güdül", "Haymana", "Kalecik", "Kazan", "Keçiören", "Kızılcahamam", "Mamak", "Nallıhan", "Polatlı", "Pursaklar", "Sincan", "Şereflikoçhisar", "Yenimahalle"],
        "Antalya": ["Akseki", "Aksu", "Alanya", "Demre", "Döşemealtı", "Elmalı", "Finike", "Gazipaşa", "Gündoğmuş", "İbradı", "Kaş", "Kemer", "Kepez", "Konyaaltı", "Korkuteli", "Kumluca", "Manavgat", "Muratpaşa", "Serik"],
        "Artvin": ["Ardanuç", "Arhavi", "Borçka", "Hopa", "Merkez", "Murgul", "Şavşat", "Yusufeli"],
        "Aydın": ["Bozdoğan", "Buharkent", "Çine", "Didim", "Efeler", "Germencik", "İncirliova", "Karacasu", "Karpuzlu", "Koçarlı", "Köşk", "Kuşadası", "Kuyucak", "Nazilli", "Söke", "Sultanhisar", "Yenipazar"],
        "Balıkesir": ["Altıeylül", "Ayvalık", "Balya", "Bandırma", "Bigadiç", "Burhaniye", "Dursunbey", "Edremit", "Erdek", "Gömeç", "Gönen", "Havran", "İvrindi", "Karesi", "Kepsut", "Manyas", "Marmara", "Savaştepe", "Sındırgı", "Susurluk"],
        "Bilecik": ["Bozüyük", "Gölpazarı", "İnhisar", "Merkez", "Osmaneli", "Pazaryeri", "Söğüt", "Yenipazar"],
        "Bingöl": ["Adaklı", "Genç", "Karlıova", "Kiğı", "Merkez", "Solhan", "Yayladere", "Yedisu"],
        "Bitlis": ["Adilcevaz", "Ahlat", "Güroymak", "Hizan", "Merkez", "Mutki", "Tatvan"],
        "Bolu": ["Dörtdivan", "Gerede", "Göynük", "Kıbrıscık", "Mengen", "Merkez", "Mudurnu", "Seben", "Yeniçağa"],
        "Burdur": ["Ağlasun", "Altınyayla", "Bucak", "Çavdır", "Çeltikçi", "Gölhisar", "Karamanlı", "Kemer", "Merkez", "Tefenni", "Yeşilova"],
        "Bursa": ["Büyükorhan", "Gemlik", "Gürsu", "Harmancık", "İnegöl", "İznik", "Karacabey", "Keles", "Kestel", "Mudanya", "Mustafakemalpaşa", "Nilüfer", "Orhaneli", "Orhangazi", "Osmangazi", "Yenişehir", "Yıldırım"],
        "Çanakkale": ["Ayvacık", "Bayramiç", "Biga", "Bozcaada", "Çan", "Eceabat", "Ezine", "Gelibolu", "Gökçeada", "Lapseki", "Merkez", "Yenice"],
        "Çankırı": ["Atkaracalar", "Bayramören", "Çerkeş", "Eldivan", "Ilgaz", "Kızılırmak", "Korgun", "Kurşunlu", "Merkez", "Orta", "Şabanözü", "Yapraklı"],
        "Çorum": ["Alaca", "Bayat", "Boğazkale", "Dodurga", "İskilip", "Kargı", "Laçin", "Mecitözü", "Merkez", "Oğuzlar", "Ortaköy", "Osmancık", "Sungurlu", "Uğurludağ"],
        "Denizli": ["Acıpayam", "Babadağ", "Baklan", "Bekilli", "Beyağaç", "Bozkurt", "Buldan", "Çal", "Çameli", "Çardak", "Çivril", "Güney", "Honaz", "Kale", "Merkezefendi", "Pamukkale", "Sarayköy", "Serinhisar", "Tavas"],
        "Diyarbakır": ["Bağlar", "Bismil", "Çermik", "Çınar", "Çüngüş", "Dicle", "Eğil", "Ergani", "Hani", "Hazro", "Kayapınar", "Kocaköy", "Kulp", "Lice", "Silvan", "Sur", "Yenişehir"],
        "Edirne": ["Enez", "Havsa", "İpsala", "Keşan", "Lalapaşa", "Meriç", "Merkez", "Süloğlu", "Uzunköprü"],
        "Elazığ": ["Ağın", "Alacakaya", "Arıcak", "Baskil", "Karakoçan", "Keban", "Kovancılar", "Maden", "Merkez", "Palu", "Sivrice"],
        "Erzincan": ["Çayırlı", "İliç", "Kemah", "Kemaliye", "Merkez", "Otlukbeli", "Refahiye", "Tercan", "Üzümlü"],
        "Erzurum": ["Aşkale", "Aziziye", "Çat", "Hınıs", "Horasan", "İspir", "Karaçoban", "Karayazı", "Köprüköy", "Narman", "Oltu", "Olur", "Palandöken", "Pasinler", "Pazaryolu", "Şenkaya", "Tekman", "Tortum", "Uzundere", "Yakutiye"],
        "Eskişehir": ["Alpu", "Beylikova", "Çifteler", "Günyüzü", "Han", "İnönü", "Mahmudiye", "Mihalgazi", "Mihalıççık", "Odunpazarı", "Sarıcakaya", "Seyitgazi", "Sivrihisar", "Tepebaşı"],
        "Gaziantep": ["Araban", "İslahiye", "Karkamış", "Nizip", "Nurdağı", "Oğuzeli", "Şahinbey", "Şehitkamil", "Yavuzeli"],
        "Giresun": ["Alucra", "Bulancak", "Çamoluk", "Çanakçı", "Dereli", "Doğankent", "Espiye", "Eynesil", "Görele", "Güce", "Keşap", "Merkez", "Piraziz", "Şebinkarahisar", "Tirebolu", "Yağlıdere"],
        "Gümüşhane": ["Kelkit", "Köse", "Kürtün", "Merkez", "Şiran", "Torul"],
        "Hakkari": ["Çukurca", "Merkez", "Şemdinli", "Yüksekova"],
        "Hatay": ["Altınözü", "Antakya", "Arsuz", "Belen", "Defne", "Dörtyol", "Erzin", "Hassa", "İskenderun", "Kırıkhan", "Kumlu", "Payas", "Reyhanlı", "Samandağ", "Yayladağı"],
        "Isparta": ["Aksu", "Atabey", "Eğirdir", "Gelendost", "Gönen", "Keçiborlu", "Merkez", "Senirkent", "Sütçüler", "Şarkikaraağaç", "Uluborlu", "Yalvaç", "Yenişarbademli"],
        "Mersin": ["Akdeniz", "Anamur", "Aydıncık", "Bozyazı", "Çamlıyayla", "Erdemli", "Gülnar", "Mezitli", "Mut", "Silifke", "Tarsus", "Toroslar", "Yenişehir"],
        "İstanbul": ["Adalar", "Arnavutköy", "Ataşehir", "Avcılar", "Bağcılar", "Bahçelievler", "Bakırköy", "Başakşehir", "Bayrampaşa", "Beşiktaş", "Beykoz", "Beylikdüzü", "Beyoğlu", "Büyükçekmece", "Çatalca", "Çekmeköy", "Esenler", "Esenyurt", "Eyüpsultan", "Fatih", "Gaziosmanpaşa", "Güngören", "Kadıköy", "Kağıthane", "Kartal", "Küçükçekmece", "Maltepe", "Pendik", "Sancaktepe", "Sarıyer", "Silivri", "Sultanbeyli", "Sultangazi", "Şile", "Şişli", "Tuzla", "Ümraniye", "Üsküdar", "Zeytinburnu"],
        "İzmir": ["Aliağa", "Balçova", "Bayındır", "Bayraklı", "Bergama", "Beydağ", "Bornova", "Buca", "Çeşme", "Çiğli", "Dikili", "Foça", "Gaziemir", "Güzelbahçe", "Karabağlar", "Karaburun", "Karşıyaka", "Kemalpaşa", "Kınık", "Kiraz", "Konak", "Menderes", "Menemen", "Narlıdere", "Ödemiş", "Seferihisar", "Selçuk", "Tire", "Torbalı", "Urla"],
        "Kars": ["Akyaka", "Arpaçay", "Digor", "Kağızman", "Merkez", "Sarıkamış", "Selim", "Susuz"],
        "Kastamonu": ["Abana", "Ağlı", "Araç", "Azdavay", "Bozkurt", "Cide", "Çatalzeytin", "Daday", "Devrekani", "Doğanyurt", "Hanönü", "İhsangazi", "İnebolu", "Küre", "Merkez", "Pınarbaşı", "Seydiler", "Şenpazar", "Taşköprü", "Tosya"],
        "Kayseri": ["Akkışla", "Bünyan", "Develi", "Felahiye", "Hacılar", "İncesu", "Kocasinan", "Melikgazi", "Özvatan", "Pınarbaşı", "Sarıoğlan", "Sarız", "Talas", "Tomarza", "Yahyalı", "Yeşilhisar"],
        "Kırklareli": ["Babaeski", "Demirköy", "Kofçaz", "Lüleburgaz", "Merkez", "Pehlivanköy", "Pınarhisar", "Vize"],
        "Kırşehir": ["Akçakent", "Akpınar", "Boztepe", "Çiçekdağı", "Kaman", "Merkez", "Mucur"],
        "Kocaeli": ["Başiskele", "Çayırova", "Darıca", "Derince", "Dilovası", "Gebze", "Gölcük", "İzmit", "Kandıra", "Karamürsel", "Kartepe", "Körfez"],
        "Konya": ["Ahırlı", "Akören", "Akşehir", "Altınekin", "Beyşehir", "Bozkır", "Cihanbeyli", "Çeltik", "Çumra", "Derbent", "Derebucak", "Doğanhisar", "Emirgazi", "Ereğli", "Güneysinir", "Hadim", "Halkapınar", "Hüyük", "Ilgın", "Kadınhanı", "Karapınar", "Karatay", "Kulu", "Meram", "Sarayönü", "Selçuklu", "Seydişehir", "Taşkent", "Tuzlukçu", "Yalıhüyük", "Yunak"],
        "Kütahya": ["Altıntaş", "Aslanapa", "Çavdarhisar", "Domaniç", "Dumlupınar", "Emet", "Gediz", "Hisarcık", "Merkez", "Pazarlar", "Simav", "Şaphane", "Tavşanlı"],
        "Malatya": ["Akçadağ", "Arapgir", "Arguvan", "Battalgazi", "Darende", "Doğanşehir", "Doğanyol", "Hekimhan", "Kale", "Kuluncak", "Pütürge", "Yazihan", "Yeşilyurt"],
        "Manisa": ["Ahmetli", "Akhisar", "Alaşehir", "Demirci", "Gölmarmara", "Gördes", "Kırkağaç", "Köprübaşı", "Kula", "Salihli", "Sarıgöl", "Saruhanlı", "Selendi", "Soma", "Şehzadeler", "Turgutlu", "Yunusemre"],
        "Mardin": ["Artuklu", "Dargeçit", "Derik", "Kızıltepe", "Mazıdağı", "Midyat", "Nusaybin", "Ömerli", "Savur", "Yeşilli"],
        "Muğla": ["Bodrum", "Dalaman", "Datça", "Fethiye", "Kavaklıdere", "Köyceğiz", "Marmaris", "Menteşe", "Milas", "Ortaca", "Seydikemer", "Ula", "Yatağan"],
        "Muş": ["Bulanık", "Hasköy", "Korkut", "Malazgirt", "Merkez", "Varto"],
        "Nevşehir": ["Acıgöl", "Avanos", "Derinkuyu", "Gülşehir", "Hacıbektaş", "Kozaklı", "Merkez", "Ürgüp"],
        "Niğde": ["Altunhisar", "Bor", "Çamardı", "Çiftlik", "Merkez", "Ulukışla"],
        "Ordu": ["Akkuş", "Altınordu", "Aybastı", "Çamaş", "Çatalpınar", "Çaybaşı", "Fatsa", "Gölköy", "Gülyalı", "Gürgentepe", "İkizce", "Kabadüz", "Kabataş", "Korgan", "Kumru", "Mesudiye", "Perşembe", "Ulubey", "Ünye"],
        "Rize": ["Ardeşen", "Çamlıhemşin", "Çayeli", "Derepazarı", "Fındıklı", "Güneysu", "Hemşin", "İkizdere", "İyidere", "Kalkandere", "Merkez", "Pazar"],
        "Sakarya": ["Adapazarı", "Akyazı", "Arifiye", "Erenler", "Ferizli", "Geyve", "Hendek", "Karapürçek", "Karasu", "Kaynarca", "Kocaali", "Pamukova", "Sapanca", "Serdivan", "Söğütlü", "Taraklı"],
        "Samsun": ["19 Mayıs", "Alaçam", "Asarcık", "Atakum", "Ayvacık", "Bafra", "Canik", "Çarşamba", "Havza", "İlkadım", "Kavak", "Ladik", "Ondokuzmayıs", "Salıpazarı", "Tekkeköy", "Terme", "Vezirköprü", "Yakakent"],
        "Siirt": ["Baykan", "Eruh", "Kurtalan", "Merkez", "Pervari", "Şirvan", "Tillo"],
        "Sinop": ["Ayancık", "Boyabat", "Dikmen", "Durağan", "Erfelek", "Gerze", "Merkez", "Saraydüzü", "Türkeli"],
        "Sivas": ["Akıncılar", "Altınyayla", "Divriği", "Doğanşar", "Gemerek", "Gölova", "Gürün", "Hafik", "İmranlı", "Kangal", "Koyulhisar", "Merkez", "Suşehri", "Şarkışla", "Ulaş", "Yıldızeli", "Zara"],
        "Tekirdağ": ["Çerkezköy", "Çorlu", "Ergene", "Hayrabolu", "Kapaklı", "Malkara", "Marmaraereğlisi", "Muratlı", "Saray", "Süleymanpaşa", "Şarköy"],
        "Tokat": ["Almus", "Artova", "Başçiftlik", "Erbaa", "Merkez", "Niksar", "Pazar", "Reşadiye", "Sulusaray", "Turhal", "Yeşilyurt", "Zile"],
        "Trabzon": ["Akçaabat", "Araklı", "Arsin", "Beşikdüzü", "Çaykara", "Çarşıbaşı", "Dernekpazarı", "Düzköy", "Hayrat", "Köprübaşı", "Maçka", "Of", "Ortahisar", "Sürmene", "Şalpazarı", "Tonya", "Vakfıkebir", "Yomra"],
        "Tunceli": ["Çemişgezek", "Hozat", "Mazgirt", "Merkez", "Nazımiye", "Ovacık", "Pertek", "Pülümür"],
        "Şanlıurfa": ["Akçakale", "Birecik", "Bozova", "Ceylanpınar", "Eyyübiye", "Halfeti", "Haliliye", "Harran", "Hilvan", "Karaköprü", "Siverek", "Suruç", "Viranşehir"],
        "Uşak": ["Banaz", "Eşme", "Karahallı", "Merkez", "Sivaslı", "Ulubey"],
        "Van": ["Bahçesaray", "Başkale", "Çaldıran", "Çatak", "Edremit", "Erciş", "Gevaş", "Gürpınar", "İpekyolu", "Muradiye", "Özalp", "Saray", "Tuşba"],
        "Yozgat": ["Akdağmadeni", "Aydıncık", "Boğazlıyan", "Çandır", "Çayıralan", "Çekerek", "Kadışehri", "Merkez", "Saraykent", "Sarıkaya", "Sorgun", "Şefaatli", "Yenifakılı", "Yerköy"],
        "Zonguldak": ["Alaplı", "Çaycuma", "Devrek", "Gökçebey", "Kilimli", "Kozlu", "Merkez"],
        "Aksaray": ["Ağaçören", "Eskil", "Gülağaç", "Güzelyurt", "Merkez", "Ortaköy", "Sarıyahşi"],
        "Bayburt": ["Aydıntepe", "Demirözü", "Merkez"],
        "Karaman": ["Ayrancı", "Başyayla", "Ermenek", "Kazımkarabekir", "Merkez", "Sarıveliler"],
        "Kırıkkale": ["Bahşılı", "Balışeyh", "Çelebi", "Delice", "Karakeçili", "Keskin", "Merkez", "Sulakyurt", "Yahşihan"],
        "Batman": ["Beşiri", "Gercüş", "Hasankeyf", "Kozluk", "Merkez", "Sason"],
        "Şırnak": ["Beytüşşebap", "Cizre", "Güçlükonak", "İdil", "Merkez", "Silopi", "Uludere"],
        "Bartın": ["Amasra", "Kurucaşile", "Merkez", "Ulus"],
        "Ardahan": ["Çıldır", "Damal", "Göle", "Hanak", "Merkez", "Posof"],
        "Iğdır": ["Aralık", "Karakoyunlu", "Merkez", "Tuzluca"],
        "Yalova": ["Altınova", "Armutlu", "Çınarcık", "Çiftlikköy", "Merkez", "Termal"],
        "Karabük": ["Eflani", "Eskipazar", "Merkez", "Ovacık", "Safranbolu", "Yenice"],
        "Kilis": ["Elbeyli", "Merkez", "Musabeyli", "Polateli"],
        "Osmaniye": ["Bahçe", "Düziçi", "Hasanbeyli", "Kadirli", "Merkez", "Sumbas", "Toprakkale"],
        "Düzce": ["Akçakoca", "Cumayeri", "Çilimli", "Gölyaka", "Gümüşova", "Kaynaşlı", "Merkez", "Yığılca"]
    }
    return ilceler.get(il, [])

def perform_search_background(job_id):
    """Arka planda arama işlemini gerçekleştir"""
    job = active_jobs[job_id]
    
    try:
        job.status = 'running'
        job.progress = 10
        
        api_key = os.getenv('GOOGLE_MAPS_API_KEY')
        if not api_key:
            job.status = 'error'
            job.error_message = 'Google Maps API anahtarı bulunamadı!'
            return
        
        scraper = GoogleMapsScraper(api_key)
        job.progress = 30
        
        # Arama yap
        businesses = scraper.search_businesses(job.location, job.business_type, job.radius_km)
        job.progress = 80
        
        if businesses:
            # Dosya adı oluştur
            safe_location = job.location.replace(" ", "_").replace(",", "")
            safe_business = job.business_type.replace(" ", "_")
            filename = f"{safe_location}_{safe_business}_{job.radius_km}km_{job_id[:8]}.xlsx"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Excel'e kaydet
            scraper.save_to_excel(businesses, filepath)
            
            job.filename = filename
            job.result_count = len(businesses)
            job.status = 'completed'
            job.progress = 100
        else:
            job.status = 'error'
            job.error_message = 'Hiç işletme bulunamadı!'
            
    except Exception as e:
        job.status = 'error'
        job.error_message = str(e)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Giriş sayfası"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_data = db.authenticate_user(username, password)
        if user_data:
            user = User(user_data)
            login_user(user)
            
            # Giriş IP'sini kaydet
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'Unknown'))
            user_agent = request.headers.get('User-Agent', '')
            db.add_login_history(user.id, ip_address, user_agent)
            
            return redirect(url_for('index'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Çıkış yap"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Ana sayfa"""
    iller = get_iller()
    search_history = db.get_user_search_history(current_user.id)
    return render_template('index.html', iller=iller, user=current_user, search_history=search_history)

@app.route('/admin')
@login_required
def admin():
    """Admin paneli"""
    if not current_user.is_admin:
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    users = db.get_all_users()
    # Her kullanıcı için giriş geçmişini ekle
    for user in users:
        user['login_history'] = db.get_user_login_history(user['id'], 10)
    
    return render_template('admin.html', users=users)

@app.route('/admin/create_user', methods=['POST'])
@login_required
def create_user():
    """Yeni kullanıcı oluştur"""
    if not current_user.is_admin:
        return jsonify({'error': 'Yetkiniz yok!'}), 403
    
    username = request.form['username']
    password = request.form['password']
    membership_type = request.form['membership_type']
    
    if membership_type == 'unlimited':
        if db.create_user(username, password, unlimited=True):
            flash(f'Sınırsız kullanıcı "{username}" başarıyla oluşturuldu!', 'success')
        else:
            flash('Bu kullanıcı adı zaten mevcut!', 'error')
    else:
        days_valid = int(membership_type)
        if db.create_user(username, password, days_valid):
            flash(f'Kullanıcı "{username}" ({days_valid} gün) başarıyla oluşturuldu!', 'success')
        else:
            flash('Bu kullanıcı adı zaten mevcut!', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/extend_user/<int:user_id>', methods=['POST'])
@login_required
def extend_user(user_id):
    """Kullanıcı süresini uzat"""
    if not current_user.is_admin:
        return jsonify({'error': 'Yetkiniz yok!'}), 403
    
    days_to_add = int(request.form['days_to_add'])
    
    if db.update_user_expiry(user_id, days_to_add):
        flash('Kullanıcı süresi başarıyla uzatıldı!', 'success')
    else:
        flash('Süre uzatma işlemi başarısız!', 'error')
    
    return redirect(url_for('admin'))

@app.route('/admin/toggle_user/<int:user_id>')
@login_required
def toggle_user(user_id):
    """Kullanıcıyı aktif/pasif yap"""
    if not current_user.is_admin:
        return jsonify({'error': 'Yetkiniz yok!'}), 403
    
    new_status = db.toggle_user_status(user_id)
    status_text = 'aktif' if new_status else 'pasif'
    flash(f'Kullanıcı durumu {status_text} olarak güncellendi!', 'success')
    
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    """Kullanıcıyı sil"""
    if not current_user.is_admin:
        return jsonify({'error': 'Yetkiniz yok!'}), 403
    
    if db.delete_user(user_id):
        flash('Kullanıcı başarıyla silindi!', 'success')
    else:
        flash('Kullanıcı silinemedi!', 'error')
    
    return redirect(url_for('admin'))

@app.route('/api/ilceler/<il>')
def api_ilceler(il):
    """İlçeleri JSON olarak döndür"""
    ilceler = get_ilceler(il)
    return jsonify(ilceler)

@app.route('/api/search', methods=['POST'])
@login_required
def api_search():
    """Arama işlemini başlat"""
    data = request.json
    
    il = data.get('il', '').strip()
    ilce = data.get('ilce', '').strip()
    business_type = data.get('business_type', '').strip()
    radius_km = data.get('radius_km', 3)
    
    if not il or not business_type:
        return jsonify({'error': 'İl ve işletme türü zorunludur!'}), 400
    
    try:
        radius_km = float(radius_km)
        if radius_km <= 0:
            return jsonify({'error': 'Yarıçap 0\'dan büyük olmalıdır!'}), 400
    except ValueError:
        return jsonify({'error': 'Geçerli bir yarıçap değeri girin!'}), 400
    
    # Lokasyon string'i oluştur
    if ilce:
        location = f"{ilce}, {il}, Turkey"
    else:
        location = f"{il}, Turkey"
    
    # Benzersiz iş ID'si oluştur
    job_id = str(uuid.uuid4())
    
    # İş oluştur
    job = SearchJob(job_id, location, business_type, radius_km)
    active_jobs[job_id] = job
    
    # Arama geçmişine kaydet
    db.add_search_history(current_user.id, location, business_type, radius_km)
    
    # Arka planda arama başlat
    thread = threading.Thread(target=perform_search_background, args=(job_id,))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'job_id': job_id,
        'status': 'started',
        'message': 'Arama başlatıldı!'
    })

@app.route('/api/status/<job_id>')
def api_status(job_id):
    """İş durumunu kontrol et"""
    if job_id not in active_jobs:
        return jsonify({'error': 'İş bulunamadı!'}), 404
    
    job = active_jobs[job_id]
    
    response = {
        'job_id': job_id,
        'status': job.status,
        'progress': job.progress,
        'location': job.location,
        'business_type': job.business_type,
        'radius_km': job.radius_km
    }
    
    if job.status == 'completed':
        response['result_count'] = job.result_count
        response['download_url'] = url_for('download_file', filename=job.filename)
    elif job.status == 'error':
        response['error_message'] = job.error_message
    
    return jsonify(response)

@app.route('/download/<filename>')
def download_file(filename):
    """Dosyayı indir"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    else:
        return "Dosya bulunamadı!", 404

@app.route('/result/<job_id>')
def result_page(job_id):
    """Sonuç sayfası"""
    if job_id not in active_jobs:
        return "İş bulunamadı!", 404
    
    job = active_jobs[job_id]
    return render_template('result.html', job=job, job_id=job_id)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
