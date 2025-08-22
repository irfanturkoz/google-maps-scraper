#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os

class Database:
    def __init__(self, db_path='users.db'):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Veritabanını başlat ve tabloları oluştur"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Kullanıcılar tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                expiry_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Arama geçmişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                location TEXT NOT NULL,
                business_type TEXT NOT NULL,
                radius_km REAL NOT NULL,
                result_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Kullanıcı giriş IP geçmişi tablosu
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Varsayılan admin kullanıcısı oluştur
        admin_exists = cursor.execute('SELECT COUNT(*) FROM users WHERE username = ?', ('trkz',)).fetchone()[0]
        if admin_exists == 0:
            admin_hash = generate_password_hash('124124Aa.')
            expiry_date = (datetime.now() + timedelta(days=365)).date()
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, expiry_date)
                VALUES (?, ?, ?, ?)
            ''', ('trkz', admin_hash, True, expiry_date))
        
        conn.commit()
        conn.close()
    
    def create_user(self, username, password, days_valid=30, is_admin=False, unlimited=False):
        """Yeni kullanıcı oluştur"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = generate_password_hash(password)
            
            if unlimited:
                # Sınırsız kullanıcı için çok uzak bir tarih (2099-12-31)
                expiry_date = datetime(2099, 12, 31).date()
            else:
                expiry_date = (datetime.now() + timedelta(days=days_valid)).date()
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, is_admin, expiry_date)
                VALUES (?, ?, ?, ?)
            ''', (username, password_hash, is_admin, expiry_date))
            
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            return False  # Kullanıcı zaten var
    
    def verify_user(self, username, password):
        """Kullanıcı doğrulama"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, password_hash, is_admin, expiry_date, is_active
            FROM users WHERE username = ?
        ''', (username,))
        
        user = cursor.fetchone()
        conn.close()
        
        if user and user[4]:  # is_active kontrolü
            user_id, password_hash, is_admin, expiry_date, is_active = user
            if check_password_hash(password_hash, password):
                # Süre kontrolü
                expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
                if expiry >= datetime.now().date():
                    self.update_last_login(user_id)
                    return {
                        'id': user_id,
                        'username': username,
                        'is_admin': bool(is_admin),
                        'expiry_date': expiry_date,
                        'days_left': (expiry - datetime.now().date()).days
                    }
        return None
    
    def update_last_login(self, user_id):
        """Son giriş zamanını güncelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
        ''', (user_id,))
        
        conn.commit()
        conn.close()
    
    def get_all_users(self):
        """Tüm kullanıcıları getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, is_admin, expiry_date, created_at, last_login, is_active
            FROM users ORDER BY created_at DESC
        ''')
        
        users = []
        for row in cursor.fetchall():
            user_id, username, is_admin, expiry_date, created_at, last_login, is_active = row
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            days_left = (expiry - datetime.now().date()).days
            
            # Sınırsız kullanıcı kontrolü (2099 yılı = sınırsız)
            is_unlimited = expiry.year >= 2099
            
            if is_unlimited:
                status = 'Sınırsız' if is_active else 'Pasif'
                days_left_text = 'Sınırsız'
            else:
                status = 'Aktif' if days_left > 0 and is_active else 'Süresi Dolmuş' if days_left <= 0 else 'Pasif'
                days_left_text = f"{days_left} gün" if days_left > 0 else "Dolmuş"
            
            users.append({
                'id': user_id,
                'username': username,
                'is_admin': bool(is_admin),
                'expiry_date': expiry_date,
                'days_left': days_left,
                'days_left_text': days_left_text,
                'created_at': created_at,
                'last_login': last_login,
                'is_active': bool(is_active),
                'is_unlimited': is_unlimited,
                'status': status
            })
        
        conn.close()
        return users
    
    def update_user_expiry(self, user_id, days_to_add):
        """Kullanıcının süresini güncelle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Mevcut süreyi al
        cursor.execute('SELECT expiry_date FROM users WHERE id = ?', (user_id,))
        current_expiry = cursor.fetchone()[0]
        
        # Yeni süreyi hesapla
        current_date = datetime.strptime(current_expiry, '%Y-%m-%d').date()
        new_expiry = current_date + timedelta(days=days_to_add)
        
        cursor.execute('''
            UPDATE users SET expiry_date = ? WHERE id = ?
        ''', (new_expiry, user_id))
        
        conn.commit()
        conn.close()
        return True
    
    def toggle_user_status(self, user_id):
        """Kullanıcı durumunu aktif/pasif yap"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT is_active FROM users WHERE id = ?', (user_id,))
        current_status = cursor.fetchone()[0]
        
        new_status = not bool(current_status)
        cursor.execute('UPDATE users SET is_active = ? WHERE id = ?', (new_status, user_id))
        
        conn.commit()
        conn.close()
        return new_status
    
    def delete_user(self, user_id):
        """Kullanıcıyı sil"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM users WHERE id = ? AND username != "trkz"', (user_id,))
        
        conn.commit()
        conn.close()
        return cursor.rowcount > 0
    
    def add_search_history(self, user_id, location, business_type, radius_km, result_count=0):
        """Arama geçmişine yeni kayıt ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO search_history (user_id, location, business_type, radius_km, result_count)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, location, business_type, radius_km, result_count))
        
        conn.commit()
        conn.close()
    
    def get_user_search_history(self, user_id, limit=5):
        """Kullanıcının arama geçmişini getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT location, business_type, radius_km, result_count, created_at
            FROM search_history 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'location': row[0],
                'business_type': row[1],
                'radius_km': row[2],
                'result_count': row[3],
                'created_at': row[4]
            })
        
        conn.close()
        return history
    
    def add_login_history(self, user_id, ip_address, user_agent=None):
        """Kullanıcı giriş geçmişine kayıt ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO login_history (user_id, ip_address, user_agent)
            VALUES (?, ?, ?)
        ''', (user_id, ip_address, user_agent))
        
        conn.commit()
        conn.close()
    
    def get_user_login_history(self, user_id, limit=10):
        """Kullanıcının giriş geçmişini getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT ip_address, user_agent, login_time
            FROM login_history 
            WHERE user_id = ? 
            ORDER BY login_time DESC 
            LIMIT ?
        ''', (user_id, limit))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'ip_address': row[0],
                'user_agent': row[1],
                'login_time': row[2]
            })
        
        conn.close()
        return history
    
    def authenticate_user(self, username, password):
        """Kullanıcı doğrulama"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, password_hash, is_admin, expiry_date, is_active
            FROM users WHERE username = ? AND is_active = 1
        ''', (username,))
        
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row and check_password_hash(user_row[2], password):
            user_id, username, password_hash, is_admin, expiry_date, is_active = user_row
            expiry = datetime.strptime(expiry_date, '%Y-%m-%d').date()
            days_left = (expiry - datetime.now().date()).days
            
            if days_left > 0 or expiry_date.startswith('2099'):
                return {
                    'id': user_id,
                    'username': username,
                    'is_admin': bool(is_admin),
                    'expiry_date': expiry_date,
                    'days_left': days_left if not expiry_date.startswith('2099') else 999999
                }
        
        return None
