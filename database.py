# database.py - С ТАБЛИЦЕЙ ЦЕН
import sqlite3
import datetime
import random
import string

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('stars_bot.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.init_prices()
    
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
                processed_at TEXT,
                gift_code TEXT
            )
        ''')
        
        # Таблица отзывов
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
        
        # Таблица промокодов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS promocodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                discount INTEGER,
                expires_at TEXT,
                uses_left INTEGER,
                created_at TEXT
            )
        ''')
        
        # Таблица цен на товары
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT UNIQUE,
                price INTEGER,
                updated_at TEXT
            )
        ''')
        self.conn.commit()
    
    def init_prices(self):
        """Инициализация цен по умолчанию"""
        default_prices = [
            ('мишка', 24),
            ('сердце', 24),
            ('подарок', 35),
            ('stars_50', 75),
            ('stars_100', 135),
            ('stars_150', 203)
        ]
        
        for item_name, price in default_prices:
            self.cursor.execute(
                "INSERT OR IGNORE INTO prices (item_name, price, updated_at) VALUES (?, ?, ?)",
                (item_name, price, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
        self.conn.commit()
    
    def get_gift_prices(self):
        """Получить цены на подарки"""
        prices = {}
        for gift in ['мишка', 'сердце', 'подарок']:
            self.cursor.execute(
                "SELECT price FROM prices WHERE item_name = ?",
                (gift,)
            )
            result = self.cursor.fetchone()
            prices[gift] = result[0] if result else 0
        return prices
    
    def get_stars_prices(self):
        """Получить цены на звёзды"""
        prices = {}
        for stars in [50, 100, 150]:
            self.cursor.execute(
                "SELECT price FROM prices WHERE item_name = ?",
                (f'stars_{stars}',)
            )
            result = self.cursor.fetchone()
            prices[stars] = result[0] if result else 0
        return prices
    
    def update_gift_price(self, gift_name, new_price):
        """Обновить цену подарка"""
        self.cursor.execute(
            "UPDATE prices SET price = ?, updated_at = ? WHERE item_name = ?",
            (new_price, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gift_name)
        )
        self.conn.commit()
    
    def update_stars_price(self, stars_count, new_price):
        """Обновить цену звёзд"""
        self.cursor.execute(
            "UPDATE prices SET price = ?, updated_at = ? WHERE item_name = ?",
            (new_price, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f'stars_{stars_count}')
        )
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
        gift_code = self.generate_gift_code()
        self.cursor.execute(
            "UPDATE payments SET status = 'approved', processed_at = ?, gift_code = ? WHERE id = ?",
            (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), gift_code, payment_id)
        )
        self.conn.commit()
    
    def reject_payment(self, payment_id, comment):
        self.cursor.execute(
            "UPDATE payments SET status = 'rejected', admin_comment = ?, processed_at = ? WHERE id = ?",
            (comment, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), payment_id)
        )
        self.conn.commit()
    
    def generate_gift_code(self):
        """Генерация случайного кода для подарка"""
        letters = string.ascii_uppercase + string.digits
        return ''.join(random.choice(letters) for _ in range(8))
    
    def get_user_payments(self, user_id):
        self.cursor.execute(
            """SELECT item_name, amount_rub, target_username, status, created_at 
               FROM payments 
               WHERE user_id = ? 
               ORDER BY created_at DESC""",
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def get_sales_stats(self):
        """Статистика продаж для админа"""
        self.cursor.execute(
            "SELECT COUNT(*), SUM(amount_rub) FROM payments WHERE status = 'approved'"
        )
        result = self.cursor.fetchone()
        total_sales = result[0] or 0
        total_amount = result[1] or 0
        avg_check = total_amount // total_sales if total_sales > 0 else 0
        
        self.cursor.execute(
            "SELECT item_name, COUNT(*) FROM payments WHERE status = 'approved' GROUP BY item_name ORDER BY COUNT(*) DESC LIMIT 1"
        )
        popular = self.cursor.fetchone()
        popular_item = popular[0] if popular else "нет данных"
        
        return (total_sales, total_amount, avg_check, popular_item)
    
    def get_top_buyers(self, limit=10):
        """Топ покупателей по количеству покупок"""
        self.cursor.execute(
            """SELECT user_id, username, COUNT(*) as purchase_count 
               FROM payments 
               WHERE status = 'approved' 
               GROUP BY user_id 
               ORDER BY purchase_count DESC 
               LIMIT ?""",
            (limit,)
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
    
    # Промокоды
    def create_promo(self, code, discount, uses):
        expires = (datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "INSERT INTO promocodes (code, discount, expires_at, uses_left, created_at) VALUES (?, ?, ?, ?, ?)",
            (code, discount, expires, uses, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        self.conn.commit()
        return self.cursor.lastrowid
    
    def check_promo(self, code):
        self.cursor.execute(
            "SELECT * FROM promocodes WHERE code = ? AND uses_left > 0 AND expires_at > ?",
            (code, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        return self.cursor.fetchone()
    
    def get_all_promos(self):
        self.cursor.execute(
            "SELECT * FROM promocodes ORDER BY created_at DESC"
        )
        return self.cursor.fetchall()
    
    def apply_promo_to_user(self, user_id, promo_id, discount):
        # Здесь логика применения скидки к пользователю
        pass
