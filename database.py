# database.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
import sqlite3
import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('stars_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Таблица пользователей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                registered_date TEXT,
                last_activity TEXT
            )
        ''')
        
        # Таблица платежей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                amount_rub INTEGER,
                photo_id TEXT,
                target_username TEXT,
                status TEXT DEFAULT 'pending',
                admin_comment TEXT,
                created_at TEXT,
                processed_at TEXT
            )
        ''')
        
        # Таблица отзывов с модерацией
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                review_text TEXT,
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                moderated_at TEXT
            )
        ''')
        self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, first_name, registered_date, last_activity) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, first_name, now, now)
        )
        self.conn.commit()
    
    def update_user_activity(self, user_id):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "UPDATE users SET last_activity = ? WHERE user_id = ?",
            (now, user_id)
        )
        self.conn.commit()
    
    def get_all_users(self):
        self.cursor.execute(
            "SELECT user_id, username, first_name, registered_date, last_activity FROM users ORDER BY registered_date DESC"
        )
        return self.cursor.fetchall()
    
    def get_active_users_count(self):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute(
            "SELECT COUNT(*) FROM users WHERE last_activity LIKE ?",
            (f"{today}%",)
        )
        return self.cursor.fetchone()[0]
    
    def create_payment(self, user_id, item_name, amount_rub, photo_id, target_username):
        self.cursor.execute(
            """INSERT INTO payments 
               (user_id, item_name, amount_rub, photo_id, target_username, created_at) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, item_name, amount_rub, photo_id, target_username, 
             datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_payments(self):
        self.cursor.execute(
            "SELECT * FROM payments WHERE status = 'pending' ORDER BY created_at DESC"
        )
        return self.cursor.fetchall()
    
    def get_payment(self, payment_id):
        self.cursor.execute("SELECT * FROM payments WHERE id = ?", (payment_id,))
        return self.cursor.fetchone()
    
    def approve_payment(self, payment_id, admin_id):
        self.cursor.execute(
            "UPDATE payments SET status = 'approved', processed_at = ? WHERE id = ?",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), payment_id)
        )
        self.conn.commit()
    
    def reject_payment(self, payment_id, comment):
        self.cursor.execute(
            "UPDATE payments SET status = 'rejected', admin_comment = ?, processed_at = ? WHERE id = ?",
            (comment, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), payment_id)
        )
        self.conn.commit()
    
    def get_user_payments(self, user_id):
        self.cursor.execute(
            """SELECT item_name, amount_rub, target_username, status, created_at 
               FROM payments 
               WHERE user_id = ? 
               ORDER BY created_at DESC""",
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def add_review(self, user_id, username, text):
        self.cursor.execute(
            "INSERT INTO reviews (user_id, username, review_text, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def get_pending_reviews(self):
        self.cursor.execute(
            "SELECT id, user_id, username, review_text, created_at, moderated_at FROM reviews WHERE status = 'pending' ORDER BY created_at DESC"
        )
        return self.cursor.fetchall()
    
    def get_approved_reviews(self, limit=10):
        self.cursor.execute(
            "SELECT username, review_text, created_at FROM reviews WHERE status = 'approved' ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return self.cursor.fetchall()
    
    def approve_review(self, review_id):
        self.cursor.execute(
            "UPDATE reviews SET status = 'approved', moderated_at = ? WHERE id = ?",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), review_id)
        )
        self.conn.commit()
    
    def reject_review(self, review_id):
        self.cursor.execute(
            "UPDATE reviews SET status = 'rejected', moderated_at = ? WHERE id = ?",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), review_id)
        )
        self.conn.commit()
    
    def has_user_purchased(self, user_id):
        self.cursor.execute(
            "SELECT COUNT(*) FROM payments WHERE user_id = ? AND status = 'approved'",
            (user_id,)
        )
        return self.cursor.fetchone()[0] > 0
    
    def has_user_reviewed(self, user_id):
        self.cursor.execute(
            "SELECT COUNT(*) FROM reviews WHERE user_id = ?",
            (user_id,)
        )
        return self.cursor.fetchone()[0] > 0