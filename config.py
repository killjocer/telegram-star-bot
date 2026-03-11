# config.py - ДЛЯ RAILWAY
import os

# Берем значения из переменных окружения Railway
TOKEN = os.environ.get('TOKEN')
ADMIN_IDS_STR = os.environ.get('ADMIN_IDS', '8526573310')
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',') if id.strip()]
CARD_NUMBER = os.environ.get('CARD_NUMBER')
CARD_HOLDER = os.environ.get('CARD_HOLDER')
BANK_NAME = os.environ.get('BANK_NAME', 'Сбербанк')

# Проверка (для логов)
print(f"✅ Конфиг загружен:")
print(f"   TOKEN: {'есть' if TOKEN else 'НЕТ!'}")
print(f"   ADMIN_IDS: {ADMIN_IDS}")
print(f"   CARD_NUMBER: {CARD_NUMBER}")
