# main.py - С ЦВЕТНЫМИ КНОПКАМИ (Telegram Bot API 9.4)
import asyncio
import logging
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database import Database
import datetime
from keep_alive import keep_alive

# Запускаем веб-сервер для Railway
keep_alive()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# === СОСТОЯНИЯ (FSM) ===
class ReviewStates(StatesGroup):
    waiting_for_review = State()

class PaymentStates(StatesGroup):
    waiting_for_photo = State()
    selected_item = State()
    selected_price = State()
    selected_username = State()

class RejectState(StatesGroup):
    waiting_for_reason = State()

class UsernameState(StatesGroup):
    waiting_for_username = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

class PromoState(StatesGroup):
    waiting_for_code = State()
    waiting_for_discount = State()
    waiting_for_uses = State()

class EnterPromoState(StatesGroup):
    waiting_for_promo = State()

class EditPriceState(StatesGroup):
    waiting_for_item = State()
    waiting_for_new_price = State()

# === ЭМОДЗИ ДЛЯ КНОПОК ===
EMOJI = {
    "primary": "🔵",
    "success": "🟢",
    "danger": "🔴",
    "warning": "🟡",
    "info": "⚪",
    "cancel": "✖️",
    "back": "◀️",
    "promo": "🏷️",
    "edit": "✏️",
    "save": "💾",
    "buy": "💫",
    "profile": "👤",
    "reviews": "⭐",
    "support": "🛠",
    "gift": "🎁",
    "stars": "⭐",
    "lucky": "🎲",
    "color": "🎨",
}

# === КЛАВИАТУРЫ С ЦВЕТНЫМИ КНОПКАМИ ===
def main_keyboard(user_id=None):
    """Главное меню с цветными кнопками"""
    buttons = []
    
    # 🔵 Синяя кнопка "Купить" (primary - главное действие)
    buttons.append([
        InlineKeyboardButton(
            text=f"{EMOJI['buy']} Купить", 
            callback_data="buy_menu",
            style="primary"  # 🔵 Синяя
        )
    ])
    
    # 🟢 Зелёная кнопка "Ввести промокод" (success - выгодное действие)
    buttons.append([
        InlineKeyboardButton(
            text=f"{EMOJI['promo']} Ввести промокод", 
            callback_data="enter_promo",
            style="success"  # 🟢 Зелёная
        )
    ])
    
    # 🟢 Зелёный "Профиль" и 🔵 Синие "Отзывы"
    buttons.append([
        InlineKeyboardButton(
            text=f"{EMOJI['profile']} Профиль", 
            callback_data="profile",
            style="success"  # 🟢 Зелёная
        ),
        InlineKeyboardButton(
            text=f"{EMOJI['reviews']} Отзывы", 
            callback_data="reviews",
            style="primary"  # 🔵 Синяя
        )
    ])
    
    # ⚪ Серая кнопка "Поддержка" (без стиля - стандартная)
    buttons.append([
        InlineKeyboardButton(
            text=f"{EMOJI['support']} Поддержка", 
            callback_data="support"
            # без style - стандартная серая
        )
    ])
    
    # 🔴 Красная кнопка для админа (danger - только для админов)
    if user_id and user_id in config.ADMIN_IDS:
        buttons.append([
            InlineKeyboardButton(
                text=f"{EMOJI['danger']} 👑 Админ-панель", 
                callback_data="admin_panel",
                style="danger"  # 🔴 Красная
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_keyboard():
    """Кнопка отмены - всегда красная (danger)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"{EMOJI['cancel']} Отменить", 
                callback_data="cancel_action",
                style="danger"  # 🔴 Красная - опасное действие
            )
        ]
    ])
    return keyboard

def admin_panel_keyboard():
    """Кнопки админ-панели с цветами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🟡 Жёлтые для ожидающих действий
        [
            InlineKeyboardButton(
                text=f"{EMOJI['warning']} ⏳ Платежи", 
                callback_data="admin_payments",
                style="danger"  # 🔴 Красная - важные действия
            )
        ],
        # 🟢 Зелёные для отзывов
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} ⭐ Отзывы", 
                callback_data="admin_reviews",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синие для информации
        [
            InlineKeyboardButton(
                text=f"{EMOJI['primary']} 👥 Пользователи", 
                callback_data="admin_users",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟢 Зелёные для статистики
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} 📊 Статистика", 
                callback_data="admin_stats",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синие для редактирования
        [
            InlineKeyboardButton(
                text=f"{EMOJI['edit']} 💰 Редактировать цены", 
                callback_data="admin_edit_prices",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟢 Зелёные для промокодов
        [
            InlineKeyboardButton(
                text=f"{EMOJI['promo']} 🏷️ Промокоды", 
                callback_data="admin_promo",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🟡 Жёлтые для рассылки
        [
            InlineKeyboardButton(
                text=f"{EMOJI['warning']} 📢 Рассылка", 
                callback_data="admin_broadcast",
                style="danger"  # 🔴 Красная - массовые действия
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="back_to_main",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def admin_edit_prices_keyboard():
    """Кнопки выбора товара для изменения цены"""
    gift_prices = db.get_gift_prices()
    stars_prices = db.get_stars_prices()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🟢 Зелёные для подарков
        [
            InlineKeyboardButton(
                text=f"🧸 Мишка ({gift_prices['мишка']}₽)", 
                callback_data="edit_price_мишка",
                style="success"  # 🟢 Зелёная
            )
        ],
        [
            InlineKeyboardButton(
                text=f"❤️ Сердце ({gift_prices['сердце']}₽)", 
                callback_data="edit_price_сердце",
                style="success"  # 🟢 Зелёная
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🎁 Подарок ({gift_prices['подарок']}₽)", 
                callback_data="edit_price_подарок",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синие для звёзд
        [
            InlineKeyboardButton(
                text=f"50 ⭐ ({stars_prices[50]}₽)", 
                callback_data="edit_price_stars_50",
                style="primary"  # 🔵 Синяя
            )
        ],
        [
            InlineKeyboardButton(
                text=f"100 ⭐ ({stars_prices[100]}₽)", 
                callback_data="edit_price_stars_100",
                style="primary"  # 🔵 Синяя
            )
        ],
        [
            InlineKeyboardButton(
                text=f"150 ⭐ ({stars_prices[150]}₽)", 
                callback_data="edit_price_stars_150",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="admin_panel",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def admin_promo_keyboard():
    """Кнопки управления промокодами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🟢 Зелёная для создания
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} Создать промокод", 
                callback_data="promo_create",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синяя для списка
        [
            InlineKeyboardButton(
                text=f"{EMOJI['primary']} Список промокодов", 
                callback_data="promo_list",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="admin_panel",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def buy_menu_keyboard():
    """Меню выбора категории покупки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🟢 Зелёная для подарков
        [
            InlineKeyboardButton(
                text=f"{EMOJI['gift']} Подарки", 
                callback_data="buy_gifts",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синяя для звёзд
        [
            InlineKeyboardButton(
                text=f"{EMOJI['stars']} Звёзды", 
                callback_data="buy_stars",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟡 Жёлтая для случайного выбора
        [
            InlineKeyboardButton(
                text=f"{EMOJI['lucky']} Мне повезёт", 
                callback_data="lucky_gift",
                style="danger"  # 🔴 Красная - сюрприз
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="back_to_main",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def gifts_keyboard():
    """Кнопки с подарками (цены берутся из БД)"""
    prices = db.get_gift_prices()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🟢 Зелёные для подарков
        [
            InlineKeyboardButton(
                text=f"🧸 Мишка — {prices['мишка']}₽", 
                callback_data=f"gift_мишка_{prices['мишка']}",
                style="success"  # 🟢 Зелёная
            )
        ],
        [
            InlineKeyboardButton(
                text=f"❤️ Сердце — {prices['сердце']}₽", 
                callback_data=f"gift_сердце_{prices['сердце']}",
                style="danger"  # 🔴 Красная - сердечко
            )
        ],
        [
            InlineKeyboardButton(
                text=f"🎁 Подарок — {prices['подарок']}₽", 
                callback_data=f"gift_подарок_{prices['подарок']}",
                style="primary"  # 🔵 Синяя
            )
        ],
        # ⚪ Серая для выбора цвета
        [
            InlineKeyboardButton(
                text=f"{EMOJI['color']} Выбрать цвет", 
                callback_data="gift_color"
                # без style - стандартная серая
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="buy_menu",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def gift_color_keyboard():
    """Выбор цвета для подарка"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🔴 Красный
        [
            InlineKeyboardButton(
                text=f"{EMOJI['danger']} Красный", 
                callback_data="color_красный",
                style="danger"  # 🔴 Красная
            )
        ],
        # 🔵 Синий
        [
            InlineKeyboardButton(
                text=f"{EMOJI['primary']} Синий", 
                callback_data="color_синий",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟢 Зелёный
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} Зелёный", 
                callback_data="color_зелёный",
                style="success"  # 🟢 Зелёная
            )
        ],
        # ⚪ Белый (без стиля)
        [
            InlineKeyboardButton(
                text=f"⚪ Белый", 
                callback_data="color_белый"
                # без style - стандартная серая
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="buy_gifts",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def stars_keyboard():
    """Кнопки со звёздами (цены берутся из БД)"""
    prices = db.get_stars_prices()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🔵 Синие для звёзд
        [
            InlineKeyboardButton(
                text=f"50 ⭐ — {prices[50]}₽", 
                callback_data=f"stars_50_{prices[50]}",
                style="primary"  # 🔵 Синяя
            )
        ],
        [
            InlineKeyboardButton(
                text=f"100 ⭐ — {prices[100]}₽", 
                callback_data=f"stars_100_{prices[100]}",
                style="success"  # 🟢 Зелёная
            )
        ],
        [
            InlineKeyboardButton(
                text=f"150 ⭐ — {prices[150]}₽", 
                callback_data=f"stars_150_{prices[150]}",
                style="danger"  # 🔴 Красная
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="buy_menu",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def admin_payment_keyboard(payment_id):
    """Кнопки для админа (одобрить/отказать)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # 🟢 Зелёная для одобрения
            InlineKeyboardButton(
                text=f"{EMOJI['success']} Одобрить", 
                callback_data=f"approve_{payment_id}",
                style="success"  # 🟢 Зелёная
            ),
            # 🔴 Красная для отказа
            InlineKeyboardButton(
                text=f"{EMOJI['danger']} Отказать", 
                callback_data=f"reject_{payment_id}",
                style="danger"  # 🔴 Красная
            )
        ]
    ])
    return keyboard

def admin_review_keyboard(review_id):
    """Кнопки для модерации отзыва"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            # 🟢 Зелёная для публикации
            InlineKeyboardButton(
                text=f"{EMOJI['success']} Опубликовать", 
                callback_data=f"publish_review_{review_id}",
                style="success"  # 🟢 Зелёная
            ),
            # 🔴 Красная для отклонения
            InlineKeyboardButton(
                text=f"{EMOJI['danger']} Отклонить", 
                callback_data=f"decline_review_{review_id}",
                style="danger"  # 🔴 Красная
            )
        ]
    ])
    return keyboard

def reviews_keyboard():
    """Кнопки в разделе отзывов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🔵 Синяя для просмотра
        [
            InlineKeyboardButton(
                text=f"{EMOJI['primary']} 👀 Смотреть отзывы", 
                callback_data="view_reviews",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟢 Зелёная для написания
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} ✍️ Написать отзыв", 
                callback_data="write_review",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🟡 Жёлтая для топа
        [
            InlineKeyboardButton(
                text=f"{EMOJI['warning']} 🏆 Топ покупателей", 
                callback_data="top_buyers",
                style="danger"  # 🔴 Красная - достижения
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="back_to_main",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

def support_keyboard():
    """Кнопки в поддержке"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        # 🔵 Синяя для FAQ
        [
            InlineKeyboardButton(
                text=f"{EMOJI['primary']} ❓ Частые вопросы", 
                callback_data="faq",
                style="primary"  # 🔵 Синяя
            )
        ],
        # 🟢 Зелёная для чата
        [
            InlineKeyboardButton(
                text=f"{EMOJI['success']} 💬 Чат с админом", 
                callback_data="chat_with_admin",
                style="success"  # 🟢 Зелёная
            )
        ],
        # 🔵 Синяя кнопка назад
        [
            InlineKeyboardButton(
                text=f"{EMOJI['back']} Назад", 
                callback_data="back_to_main",
                style="primary"  # 🔵 Синяя
            )
        ]
    ])
    return keyboard

# === ОБРАБОТЧИК КОМАНДЫ ОТМЕНЫ ===
@dp.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    
    await callback.message.edit_text(
        "✅ Действие отменено. Возвращаю в главное меню.",
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    """Команда /cancel для отмены"""
    current_state = await state.get_state()
    if current_state is not None:
        await state.clear()
    
    await message.answer(
        "✅ Действие отменено",
        reply_markup=main_keyboard(message.from_user.id)
    )

# === ОБРАБОТЧИКИ ПРОМОКОДОВ ===
@dp.callback_query(F.data == "enter_promo")
async def enter_promo_start(callback: CallbackQuery, state: FSMContext):
    """Начало ввода промокода"""
    await callback.message.edit_text(
        f"{EMOJI['promo']} <b>Введите промокод:</b>\n\n"
        "Напишите код, который вам дали\n"
        "или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(EnterPromoState.waiting_for_promo)
    await callback.answer()

@dp.message(EnterPromoState.waiting_for_promo)
async def process_enter_promo(message: types.Message, state: FSMContext):
    """Обработка введённого промокода"""
    promo_code = message.text.strip().upper()
    
    # Проверяем промокод в базе
    promo = db.check_promo(promo_code)
    
    if not promo:
        await message.answer(
            f"{EMOJI['danger']} Промокод не найден или истёк",
            reply_markup=main_keyboard(message.from_user.id)
        )
        await state.clear()
        return
    
    promo_id, code, discount, expires_at, uses_left, created_at = promo
    
    # Сохраняем промокод в профиль пользователя
    db.apply_promo_to_user(message.from_user.id, promo_id, discount)
    
    await message.answer(
        f"{EMOJI['success']} <b>Промокод применён!</b>\n\n"
        f"Скидка: {discount}%\n"
        f"Осталось использований: {uses_left - 1}",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.from_user.id)
    )
    await state.clear()

# === АДМИН-ПАНЕЛЬ ДЛЯ ПРОМОКОДОВ ===
@dp.callback_query(F.data == "admin_promo")
async def admin_promo(callback: CallbackQuery):
    """Меню управления промокодами"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['promo']} <b>Управление промокодами</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=admin_promo_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "promo_create")
async def promo_create_start(callback: CallbackQuery, state: FSMContext):
    """Создание нового промокода - шаг 1 (код)"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['promo']} <b>Создание промокода</b>\n\n"
        "Введите код промокода (например: SKIDKA10):\n"
        "или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PromoState.waiting_for_code)
    await callback.answer()

@dp.message(PromoState.waiting_for_code)
async def promo_create_code(message: types.Message, state: FSMContext):
    """Создание промокода - шаг 2 (скидка)"""
    promo_code = message.text.strip().upper()
    await state.update_data(promo_code=promo_code)
    
    await message.answer(
        f"{EMOJI['promo']} Введите размер скидки (только число, например: 10, 20, 50):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PromoState.waiting_for_discount)

@dp.message(PromoState.waiting_for_discount)
async def promo_create_discount(message: types.Message, state: FSMContext):
    """Создание промокода - шаг 3 (количество использований)"""
    try:
        discount = int(message.text.strip())
        if discount < 1 or discount > 100:
            raise ValueError
    except:
        await message.answer(
            f"{EMOJI['danger']} Введите число от 1 до 100",
            reply_markup=cancel_keyboard()
        )
        return
    
    await state.update_data(discount=discount)
    
    await message.answer(
        f"{EMOJI['promo']} Введите количество использований (например: 10, 50, 100):",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PromoState.waiting_for_uses)

@dp.message(PromoState.waiting_for_uses)
async def promo_create_uses(message: types.Message, state: FSMContext):
    """Создание промокода - шаг 4 (сохранение)"""
    try:
        uses = int(message.text.strip())
        if uses < 1:
            raise ValueError
    except:
        await message.answer(
            f"{EMOJI['danger']} Введите положительное число",
            reply_markup=cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    promo_code = data.get('promo_code')
    discount = data.get('discount')
    
    # Сохраняем в базу
    db.create_promo(promo_code, discount, uses)
    
    await message.answer(
        f"{EMOJI['success']} <b>Промокод создан!</b>\n\n"
        f"Код: {promo_code}\n"
        f"Скидка: {discount}%\n"
        f"Использований: {uses}",
        parse_mode="HTML",
        reply_markup=admin_promo_keyboard()
    )
    await state.clear()

@dp.callback_query(F.data == "promo_list")
async def promo_list(callback: CallbackQuery):
    """Список всех промокодов"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    promos = db.get_all_promos()
    
    if not promos:
        text = "📭 Нет созданных промокодов"
    else:
        text = f"{EMOJI['promo']} <b>Список промокодов:</b>\n\n"
        for promo in promos:
            promo_id, code, discount, expires_at, uses_left, created_at = promo
            expires = expires_at.split()[0] if expires_at else "никогда"
            text += f"• <b>{code}</b> - {discount}% | Осталось: {uses_left} | до {expires}\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="admin_promo",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

# === АДМИН-ПАНЕЛЬ ДЛЯ РЕДАКТИРОВАНИЯ ЦЕН ===
@dp.callback_query(F.data == "admin_edit_prices")
async def admin_edit_prices(callback: CallbackQuery):
    """Меню выбора товара для изменения цены"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"{EMOJI['edit']} <b>Редактирование цен</b>\n\n"
        "Выберите товар для изменения цены:",
        parse_mode="HTML",
        reply_markup=admin_edit_prices_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("edit_price_"))
async def edit_price_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования цены выбранного товара"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    item = callback.data.replace("edit_price_", "")
    
    # Определяем название товара для отображения
    item_names = {
        "мишка": "🧸 Мишка",
        "сердце": "❤️ Сердце",
        "подарок": "🎁 Подарок",
        "stars_50": "50 ⭐",
        "stars_100": "100 ⭐",
        "stars_150": "150 ⭐"
    }
    
    display_name = item_names.get(item, item)
    
    await state.update_data(edit_item=item)
    
    await callback.message.edit_text(
        f"{EMOJI['edit']} <b>Изменение цены</b>\n\n"
        f"Товар: {display_name}\n"
        f"Введите новую цену в рублях (только число):\n"
        f"или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(EditPriceState.waiting_for_new_price)
    await callback.answer()

@dp.message(EditPriceState.waiting_for_new_price)
async def edit_price_save(message: types.Message, state: FSMContext):
    """Сохранение новой цены"""
    try:
        new_price = int(message.text.strip())
        if new_price < 1:
            raise ValueError
    except:
        await message.answer(
            f"{EMOJI['danger']} Введите положительное число",
            reply_markup=cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    item = data.get('edit_item')
    
    # Сохраняем цену в базу
    if item in ["мишка", "сердце", "подарок"]:
        db.update_gift_price(item, new_price)
        display_name = f"🎁 {item}"
    else:
        stars_count = int(item.split("_")[1])
        db.update_stars_price(stars_count, new_price)
        display_name = f"⭐ {stars_count}"
    
    await message.answer(
        f"{EMOJI['success']} <b>Цена обновлена!</b>\n\n"
        f"{display_name} теперь стоит {new_price}₽",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )
    await state.clear()

# === ОБРАБОТЧИКИ КОМАНД ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    username = message.from_user.username or "нет_username"
    first_name = message.from_user.first_name or "Пользователь"
    
    db.add_user(user_id, username, first_name)
    db.update_user_activity(user_id)
    
    await message.answer(
        f"👋 Привет, {first_name}!\n\n"
        f"Добро пожаловать в магазин!\n"
        f"Здесь вы можете купить подарки и звёзды.",
        reply_markup=main_keyboard(user_id)
    )

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Команда для входа в админ-панель"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("У вас нет доступа к админ-панели")
        return
    
    await message.answer(
        "👑 <b>Админ-панель</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )

# === АДМИН-ПАНЕЛЬ ===
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    """Открыть админ-панель"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_payments")
async def admin_payments(callback: CallbackQuery):
    """Просмотр ожидающих платежей"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    payments = db.get_pending_payments()
    if not payments:
        await callback.message.edit_text(
            "📭 Нет ожидающих платежей",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{EMOJI['back']} Назад", 
                        callback_data="admin_panel",
                        style="primary"  # 🔵 Синяя
                    )
                ]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"💰 Найдено платежей: {len(payments)}\n\nОтправляю по одному...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="admin_panel",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    
    for payment in payments:
        payment_id, user_id, item_name, amount_rub, photo_id, target_username, status, comment, created_at, processed_at = payment
        
        text = (
            f"💰 <b>Платёж #{payment_id}</b>\n"
            f"👤 Покупатель: <code>{user_id}</code>\n"
            f"🎁 Товар: {item_name}\n"
            f"💵 Сумма: {amount_rub} руб.\n"
            f"📦 Для @{target_username}\n"
            f"📅 Дата: {created_at}"
        )
        
        await bot.send_photo(
            chat_id=callback.from_user.id,
            photo=photo_id,
            caption=text,
            parse_mode="HTML",
            reply_markup=admin_payment_keyboard(payment_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data == "admin_reviews")
async def admin_reviews(callback: CallbackQuery):
    """Просмотр новых отзывов на модерации"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    pending_reviews = db.get_pending_reviews()
    if not pending_reviews:
        await callback.message.edit_text(
            "📭 Нет новых отзывов на модерации",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{EMOJI['back']} Назад", 
                        callback_data="admin_panel",
                        style="primary"  # 🔵 Синяя
                    )
                ]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"⭐ Найдено отзывов: {len(pending_reviews)}\n\nОтправляю...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="admin_panel",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    
    for review in pending_reviews:
        review_id, user_id, username, review_text, created_at, moderated_at = review
        
        await bot.send_message(
            chat_id=callback.from_user.id,
            text=(
                f"⭐ <b>Отзыв #{review_id}</b>\n"
                f"👤 @{username} (ID: {user_id})\n"
                f"💬 {review_text}\n"
                f"📅 {created_at}"
            ),
            parse_mode="HTML",
            reply_markup=admin_review_keyboard(review_id)
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("publish_review_"))
async def publish_review(callback: CallbackQuery):
    """Опубликовать отзыв"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    review_id = int(callback.data.split("_")[2])
    db.approve_review(review_id)
    
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>Отзыв опубликован</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отзыв опубликован", show_alert=False)

@dp.callback_query(F.data.startswith("decline_review_"))
async def decline_review(callback: CallbackQuery):
    """Отклонить отзыв"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    review_id = int(callback.data.split("_")[2])
    db.reject_review(review_id)
    
    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>Отзыв отклонён</b>",
        parse_mode="HTML"
    )
    await callback.answer("Отзыв отклонён", show_alert=False)

@dp.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Просмотр всех пользователей"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    users = db.get_all_users()
    total_users = len(users)
    active_users = db.get_active_users_count()
    
    text = (
        f"👥 <b>Всего пользователей:</b> {total_users}\n"
        f"📊 <b>Активных сегодня:</b> {active_users}\n\n"
        f"<b>Последние 10 пользователей:</b>\n"
    )
    
    for user in users[:10]:
        user_id, username, first_name, reg_date, last_activity = user
        username_display = f"@{username}" if username != "нет_username" else "нет username"
        reg_date_short = reg_date.split()[0] if reg_date else "неизвестно"
        text += f"• {user_id} | {username_display} | {first_name[:15]} | {reg_date_short}\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="admin_panel",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика продаж"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    stats = db.get_sales_stats()
    total_sales, total_amount, avg_check, popular_item = stats
    
    text = (
        f"📊 <b>Статистика продаж</b>\n\n"
        f"💰 Всего продаж: {total_sales}\n"
        f"💵 Общая сумма: {total_amount}₽\n"
        f"📈 Средний чек: {avg_check}₽\n"
        f"🔥 Популярный товар: {popular_item}\n"
    )
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="admin_panel",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Рассылка сообщения всем пользователям"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 <b>Рассылка</b>\n\n"
        "Отправьте сообщение для рассылки всем пользователям:\n"
        "или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.answer()

@dp.message(BroadcastState.waiting_for_message)
async def process_broadcast(message: types.Message, state: FSMContext):
    """Отправка рассылки"""
    if message.from_user.id not in config.ADMIN_IDS:
        await state.clear()
        return
    
    broadcast_text = message.text
    users = db.get_all_users()
    sent = 0
    failed = 0
    
    status_msg = await message.answer(f"📢 Начинаю рассылку {len(users)} пользователям...")
    
    for user in users:
        user_id = user[0]
        try:
            await bot.send_message(
                user_id,
                f"📢 <b>Рассылка от администратора</b>\n\n{broadcast_text}",
                parse_mode="HTML"
            )
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)  # Чтобы не забанили
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не доставлено: {failed}"
    )
    await state.clear()

# === ОСНОВНЫЕ ОБРАБОТЧИКИ ===
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: CallbackQuery):
    """Меню выбора категории"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "💫 <b>Выберите категорию:</b>",
        parse_mode="HTML",
        reply_markup=buy_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_gifts")
async def buy_gifts(callback: CallbackQuery):
    """Меню выбора подарка"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "🎁 <b>Выберите подарок:</b>",
        parse_mode="HTML",
        reply_markup=gifts_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "buy_stars")
async def buy_stars(callback: CallbackQuery):
    """Меню выбора звёзд"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "⭐ <b>Выберите количество звёзд:</b>",
        parse_mode="HTML",
        reply_markup=stars_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "lucky_gift")
async def lucky_gift(callback: CallbackQuery, state: FSMContext):
    """Случайный подарок"""
    db.update_user_activity(callback.from_user.id)
    
    import random
    prices = db.get_gift_prices()
    gifts = [
        ("Мишка", prices['мишка']),
        ("Сердце", prices['сердце']),
        ("Подарок", prices['подарок'])
    ]
    gift_name, price = random.choice(gifts)
    
    await state.update_data(
        selected_item=f"Подарок: {gift_name} (🎲 Случайный)",
        selected_price=price
    )
    
    await callback.message.edit_text(
        f"🎲 <b>Вам выпал: {gift_name}</b>\n"
        f"💰 Сумма: {price}₽\n\n"
        f"📝 <b>Инструкция по оплате:</b>\n"
        f"1️⃣ Отправьте <b>@username</b> получателя\n"
        f"2️⃣ Переведите <b>{price}₽</b> на карту:\n"
        f"   <code>{config.CARD_NUMBER}</code>\n"
        f"   {config.CARD_HOLDER}\n"
        f"3️⃣ Сделайте скриншот чека/перевода\n"
        f"4️⃣ Отправьте фото чека в этот чат\n\n"
        f"👉 <b>Напишите @username получателя:</b>\n"
        f"или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    
    await state.set_state(UsernameState.waiting_for_username)
    await callback.answer()

@dp.callback_query(F.data == "gift_color")
async def gift_color(callback: CallbackQuery):
    """Выбор цвета подарка"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "🎨 <b>Выберите цвет:</b>",
        parse_mode="HTML",
        reply_markup=gift_color_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("color_"))
async def process_color(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора цвета"""
    db.update_user_activity(callback.from_user.id)
    color = callback.data.split("_")[1]
    
    await state.update_data(selected_color=color)
    
    await callback.message.edit_text(
        f"✅ Выбран цвет: {color}\n\n"
        f"🎁 <b>Выберите подарок:</b>",
        reply_markup=gifts_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("gift_"))
async def process_gift_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подарка"""
    db.update_user_activity(callback.from_user.id)
    parts = callback.data.split("_")
    gift_name = parts[1]
    price = int(parts[2])
    
    data = await state.get_data()
    color = data.get('selected_color', '')
    
    item_name = f"Подарок: {gift_name}"
    if color:
        item_name += f" ({color})"
    
    await state.update_data(
        selected_item=item_name,
        selected_price=price
    )
    
    await callback.message.edit_text(
        f"🎁 <b>Вы выбрали: {gift_name}</b>\n"
        f"{f'🎨 Цвет: {color}\n' if color else ''}"
        f"💰 Сумма: {price}₽\n\n"
        f"📝 <b>Инструкция по оплате:</b>\n"
        f"1️⃣ Отправьте <b>@username</b> получателя\n"
        f"2️⃣ Переведите <b>{price}₽</b> на карту:\n"
        f"   <code>{config.CARD_NUMBER}</code>\n"
        f"   {config.CARD_HOLDER}\n"
        f"3️⃣ Сделайте скриншот чека/перевода\n"
        f"4️⃣ Отправьте фото чека в этот чат\n\n"
        f"⏳ Администратор проверит и зачислит вам моментально!\n\n"
        f"👉 <b>Напишите @username получателя:</b>\n"
        f"или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    
    await state.set_state(UsernameState.waiting_for_username)
    await callback.answer()

@dp.callback_query(F.data.startswith("stars_"))
async def process_stars_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора звёзд"""
    db.update_user_activity(callback.from_user.id)
    parts = callback.data.split("_")
    stars = parts[1]
    price = int(parts[2])
    
    await state.update_data(
        selected_item=f"Звёзды: {stars} ⭐",
        selected_price=price
    )
    
    await callback.message.edit_text(
        f"⭐ <b>Вы выбрали: {stars} звёзд</b>\n"
        f"💰 Сумма: {price}₽\n\n"
        f"📝 <b>Инструкция по оплате:</b>\n"
        f"1️⃣ Отправьте <b>@username</b> получателя\n"
        f"2️⃣ Переведите <b>{price}₽</b> на карту:\n"
        f"   <code>{config.CARD_NUMBER}</code>\n"
        f"   {config.CARD_HOLDER}\n"
        f"3️⃣ Сделайте скриншот чека/перевода\n"
        f"4️⃣ Отправьте фото чека в этот чат\n\n"
        f"⏳ Администратор проверит и зачислит вам моментально!\n\n"
        f"👉 <b>Напишите @username получателя:</b>\n"
        f"или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    
    await state.set_state(UsernameState.waiting_for_username)
    await callback.answer()

@dp.message(UsernameState.waiting_for_username)
async def handle_username(message: types.Message, state: FSMContext):
    """Получение username получателя"""
    db.update_user_activity(message.from_user.id)
    username = message.text.strip()
    
    if username.startswith('@'):
        username = username[1:]
    
    await state.update_data(target_username=username)
    await state.set_state(PaymentStates.waiting_for_photo)
    
    await message.answer(
        f"✅ Username @{username} сохранён!\n\n"
        f"📸 Теперь отправьте фото чека/перевода:\n"
        f"или /cancel для отмены",
        reply_markup=cancel_keyboard()
    )

@dp.message(PaymentStates.waiting_for_photo, F.photo)
async def handle_payment_photo(message: types.Message, state: FSMContext):
    """Получение фото чека от пользователя"""
    db.update_user_activity(message.from_user.id)
    data = await state.get_data()
    item_name = data.get('selected_item')
    amount = data.get('selected_price')
    target_username = data.get('target_username')
    
    photo_id = message.photo[-1].file_id
    
    payment_id = db.create_payment(
        user_id=message.from_user.id,
        item_name=item_name,
        amount_rub=amount,
        photo_id=photo_id,
        target_username=target_username
    )
    
    await message.answer(
        "✅ <b>Чек получен!</b>\n"
        "Администратор проверит платёж в ближайшее время.\n"
        "Вы получите уведомление о результате.",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.from_user.id)
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=(
                    f"💰 <b>Новый чек #{payment_id}</b>\n"
                    f"👤 Покупатель: {message.from_user.id}\n"
                    f"@{message.from_user.username}\n"
                    f"🎁 Товар: {item_name}\n"
                    f"💵 Сумма: {amount} руб.\n"
                    f"📦 Для: @{target_username}"
                ),
                parse_mode="HTML",
                reply_markup=admin_payment_keyboard(payment_id)
            )
        except Exception as e:
            print(f"Не удалось отправить админу: {e}")
    
    await state.clear()

@dp.message(PaymentStates.waiting_for_photo)
async def handle_payment_no_photo(message: types.Message):
    """Если пользователь отправил не фото"""
    db.update_user_activity(message.from_user.id)
    await message.answer(
        "❌ Пожалуйста, отправьте фото чека (скриншот перевода)\n"
        "или /cancel для отмены",
        reply_markup=cancel_keyboard()
    )

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    """Админ одобряет платёж"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[1])
    payment = db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    db.approve_payment(payment_id, callback.from_user.id)
    
    user_id = payment[1]
    item_name = payment[2]
    target_username = payment[5]
    
    # Генерация кода для подарка
    gift_code = db.generate_gift_code()
    
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Ваш платёж одобрен!</b>\n\n"
            f"🎁 {item_name}\n"
            f"📦 Для: @{target_username}\n"
            f"🔑 Код получения: <code>{gift_code}</code>\n\n"
            f"Спасибо за покупку!",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить пользователя: {e}")
    
    await callback.message.answer(
        f"✅ <b>ПЛАТЁЖ #{payment_id} ОДОБРЕН</b>\n"
        f"Код выдан: {gift_code}",
        parse_mode="HTML"
    )
    
    await callback.answer("Платёж одобрен", show_alert=False)

@dp.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery, state: FSMContext):
    """Админ отклоняет платёж"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[1])
    
    await state.update_data(reject_payment_id=payment_id)
    
    await callback.message.answer(
        "❌ Укажите причину отказа (отправьте текстовое сообщение):\n"
        "или /cancel для отмены",
        reply_markup=cancel_keyboard()
    )
    
    await state.set_state(RejectState.waiting_for_reason)
    await callback.answer()

@dp.message(RejectState.waiting_for_reason)
async def process_reject_reason(message: types.Message, state: FSMContext):
    """Обработка причины отказа"""
    db.update_user_activity(message.from_user.id)
    data = await state.get_data()
    payment_id = data.get('reject_payment_id')
    reason = message.text
    
    payment = db.get_payment(payment_id)
    if not payment:
        await message.answer("Ошибка: платёж не найден")
        await state.clear()
        return
    
    db.reject_payment(payment_id, reason)
    
    user_id = payment[1]
    try:
        await bot.send_message(
            user_id,
            f"❌ <b>Ваш платёж отклонён</b>\n\n"
            f"Причина: {reason}\n"
            f"Попробуйте оформить заказ заново или свяжитесь с поддержкой.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить пользователя: {e}")
    
    await message.answer(f"✅ Отказ отправлен пользователю. Причина: {reason}")
    await state.clear()

@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Показ профиля пользователя с историей"""
    db.update_user_activity(callback.from_user.id)
    user_id = callback.from_user.id
    
    payments = db.get_user_payments(user_id)
    
    profile_text = f"👤 <b>Ваш профиль</b>\n\n"
    profile_text += f"🆔 ID: <code>{user_id}</code>\n\n"
    profile_text += f"📊 <b>История покупок:</b>\n"
    
    if not payments:
        profile_text += "   У вас пока нет покупок"
    else:
        for i, payment in enumerate(payments[:5], 1):
            item_name, amount_rub, target_username, status, created_at = payment
            status_emoji = "✅" if status == "approved" else "⏳" if status == "pending" else "❌"
            date = created_at.split()[0] if created_at else "недавно"
            profile_text += f"\n{i}. {status_emoji} {item_name}\n"
            profile_text += f"   💰 {amount_rub}₽ для @{target_username}\n"
            profile_text += f"   📅 {date}\n"
    
    await callback.message.edit_text(
        profile_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="back_to_main",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "reviews")
async def reviews_menu(callback: CallbackQuery):
    """Меню отзывов"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "⭐ <b>Отзывы наших покупателей</b>\n\n"
        "Вы можете посмотреть отзывы или оставить свой.",
        parse_mode="HTML",
        reply_markup=reviews_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "view_reviews")
async def view_reviews(callback: CallbackQuery):
    """Просмотр опубликованных отзывов"""
    db.update_user_activity(callback.from_user.id)
    reviews = db.get_approved_reviews(10)
    
    if not reviews:
        text = "📭 Пока нет отзывов. Будьте первым!"
    else:
        text = "⭐ <b>Отзывы покупателей:</b>\n\n"
        for username, review_text, created_at in reviews:
            date = created_at.split()[0] if created_at else "недавно"
            text += f"👤 @{username} ({date}):\n"
            text += f"   \"{review_text}\"\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['primary']} ✍️ Написать отзыв", 
                    callback_data="write_review",
                    style="primary"  # 🔵 Синяя
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['warning']} 🏆 Топ покупателей", 
                    callback_data="top_buyers",
                    style="danger"  # 🔴 Красная
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="reviews",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "top_buyers")
async def top_buyers(callback: CallbackQuery):
    """Топ покупателей"""
    db.update_user_activity(callback.from_user.id)
    top_users = db.get_top_buyers(10)
    
    if not top_users:
        text = "🏆 Пока нет покупателей"
    else:
        text = "🏆 <b>Топ покупателей:</b>\n\n"
        for i, (user_id, username, total) in enumerate(top_users, 1):
            username_display = f"@{username}" if username != "нет_username" else f"ID {user_id}"
            text += f"{i}. {username_display} - {total} покупок\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="reviews",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "write_review")
async def write_review_start(callback: CallbackQuery, state: FSMContext):
    """Начало написания отзыва"""
    db.update_user_activity(callback.from_user.id)
    user_id = callback.from_user.id
    
    if not db.has_user_purchased(user_id):
        await callback.answer("❌ Оставлять отзывы могут только покупатели", show_alert=True)
        return
    
    if db.has_user_reviewed(user_id):
        await callback.answer("❌ Вы уже оставляли отзыв", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✍️ <b>Напишите ваш отзыв</b>\n\n"
        "Отправьте текстовое сообщение с вашим отзывом:\n"
        "или /cancel для отмены",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(ReviewStates.waiting_for_review)
    await callback.answer()

@dp.message(ReviewStates.waiting_for_review)
async def process_review(message: types.Message, state: FSMContext):
    """Сохранение отзыва (на модерацию)"""
    db.update_user_activity(message.from_user.id)
    user_id = message.from_user.id
    username = message.from_user.username or "anonymous"
    review_text = message.text
    
    review_id = db.add_review(user_id, username, review_text)
    
    await message.answer(
        "✅ <b>Спасибо за ваш отзыв!</b>\n"
        "Он отправлен на модерацию и появится после проверки.",
        parse_mode="HTML",
        reply_markup=main_keyboard(message.from_user.id)
    )
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"⭐ <b>Новый отзыв #{review_id}</b>\n"
                f"👤 @{username}\n"
                f"💬 {review_text}",
                parse_mode="HTML",
                reply_markup=admin_review_keyboard(review_id)
            )
        except:
            pass
    
    await state.clear()

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    """Поддержка"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "🛠 <b>Служба поддержки</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=support_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "faq")
async def faq(callback: CallbackQuery):
    """Частые вопросы"""
    db.update_user_activity(callback.from_user.id)
    text = (
        "❓ <b>Часто задаваемые вопросы:</b>\n\n"
        "1. <b>Как оплатить?</b>\n"
        "   Переведите нужную сумму на карту и отправьте чек\n\n"
        "2. <b>Сколько ждать?</b>\n"
        "   Администратор проверит платёж в течение часа\n\n"
        "3. <b>Как получить подарок?</b>\n"
        "   После одобрения вы получите код в сообщении\n\n"
        "4. <b>Можно ли вернуть деньги?</b>\n"
        "   Возврат только при отказе администратора\n\n"
        "Остались вопросы? Напишите @killjocer"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="support",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "chat_with_admin")
async def chat_with_admin(callback: CallbackQuery):
    """Чат с админом"""
    db.update_user_activity(callback.from_user.id)
    await callback.message.edit_text(
        "💬 <b>Чат с администратором</b>\n\n"
        "Напишите ваш вопрос, и администратор ответит вам в личные сообщения.\n\n"
        "Админ: @killjocer",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{EMOJI['back']} Назад", 
                    callback_data="support",
                    style="primary"  # 🔵 Синяя
                )
            ]
        ])
    )
    await callback.answer()

# === ЗАПУСК ===
async def main():
    print("🚀 Бот запущен и готов к работе!")
    print(f"👑 Админ ID: {config.ADMIN_IDS}")
    print(f"📱 Поддержка: @killjocer")
    print(f"🎨 Кнопки теперь цветные! 🔵🟢🔴")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
