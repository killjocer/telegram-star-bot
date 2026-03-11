# main.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import config
from database import Database
import datetime

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=config.TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# === СОСТОЯНИЯ (FSM) ===
class ReviewStates(StatesGroup):
    waiting_for_review = State()

class AdminReviewStates(StatesGroup):
    waiting_for_review_response = State()

class PaymentStates(StatesGroup):
    waiting_for_photo = State()
    selected_item = State()
    selected_price = State()
    selected_username = State()

class RejectState(StatesGroup):
    waiting_for_reason = State()

class UsernameState(StatesGroup):
    waiting_for_username = State()

# === КЛАВИАТУРЫ ===
def main_keyboard(user_id=None):
    """Главное меню (с админ-кнопкой если админ)"""
    buttons = [
        [InlineKeyboardButton(text="💫 Купить", callback_data="buy_menu")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
         InlineKeyboardButton(text="⭐ Отзывы", callback_data="reviews")],
        [InlineKeyboardButton(text="🛠 Поддержка", callback_data="support")]
    ]
    
    # Если пользователь админ - добавляем кнопку админки
    if user_id and user_id in config.ADMIN_IDS:
        buttons.append([InlineKeyboardButton(text="👑 Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel_keyboard():
    """Кнопки админ-панели"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏳ Ожидающие платежи", callback_data="admin_payments")],
        [InlineKeyboardButton(text="⭐ Новые отзывы", callback_data="admin_reviews")],
        [InlineKeyboardButton(text="👥 Все пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ])
    return keyboard

def buy_menu_keyboard():
    """Меню выбора категории покупки"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Подарки", callback_data="buy_gifts")],
        [InlineKeyboardButton(text="⭐ Звёзды", callback_data="buy_stars")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ])
    return keyboard

def gifts_keyboard():
    """Кнопки с подарками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧸 Мишка — 24₽", callback_data="gift_мишка_24")],
        [InlineKeyboardButton(text="❤️ Сердце — 24₽", callback_data="gift_сердце_24")],
        [InlineKeyboardButton(text="🎁 Подарок — 35₽", callback_data="gift_подарок_35")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="buy_menu")]
    ])
    return keyboard

def stars_keyboard():
    """Кнопки со звёздами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="50 ⭐ — 75₽", callback_data="stars_50_75")],
        [InlineKeyboardButton(text="100 ⭐ — 135₽", callback_data="stars_100_135")],
        [InlineKeyboardButton(text="150 ⭐ — 203₽", callback_data="stars_150_203")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="buy_menu")]
    ])
    return keyboard

def admin_payment_keyboard(payment_id):
    """Кнопки для админа (одобрить/отказать)"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{payment_id}"),
            InlineKeyboardButton(text="❌ Отказать", callback_data=f"reject_{payment_id}")
        ]
    ])
    return keyboard

def admin_review_keyboard(review_id):
    """Кнопки для модерации отзыва"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"publish_review_{review_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_review_{review_id}")
        ]
    ])
    return keyboard

def reviews_keyboard():
    """Кнопки в разделе отзывов"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👀 Смотреть отзывы", callback_data="view_reviews")],
        [InlineKeyboardButton(text="✍️ Написать отзыв", callback_data="write_review")],
        [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
    ])
    return keyboard

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
                [InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"💰 Найдено платежей: {len(payments)}\n\nОтправляю по одному...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")]
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
                [InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")]
            ])
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        f"⭐ Найдено отзывов: {len(pending_reviews)}\n\nОтправляю...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")]
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
    
    # Статистика
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
            [InlineKeyboardButton(text="◀ Назад", callback_data="admin_panel")]
        ])
    )
    await callback.answer()

# === ОБРАБОТЧИКИ КОЛБЭКОВ (ОСНОВНЫЕ) ===
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

@dp.callback_query(F.data.startswith("gift_"))
async def process_gift_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора подарка"""
    db.update_user_activity(callback.from_user.id)
    _, gift_name, price = callback.data.split("_")
    
    await state.update_data(
        selected_item=f"Подарок: {gift_name}",
        selected_price=int(price)
    )
    
    await callback.message.edit_text(
        f"🎁 <b>Вы выбрали: {gift_name}</b>\n"
        f"💰 Сумма: {price}₽\n\n"
        f"📝 <b>Инструкция по оплате:</b>\n"
        f"1️⃣ Отправьте <b>@username</b> получателя\n"
        f"2️⃣ Переведите <b>{price}₽</b> на карту:\n"
        f"   <code>{config.CARD_NUMBER}</code>\n"
        f"   {config.CARD_HOLDER}\n"
        f"3️⃣ Сделайте скриншот чека/перевода\n"
        f"4️⃣ Отправьте фото чека в этот чат\n\n"
        f"⏳ Администратор проверит и зачислит вам моментально!\n\n"
        f"👉 <b>Напишите @username получателя:</b>",
        parse_mode="HTML"
    )
    
    await state.set_state(UsernameState.waiting_for_username)
    await callback.answer()

@dp.callback_query(F.data.startswith("stars_"))
async def process_stars_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора звёзд"""
    db.update_user_activity(callback.from_user.id)
    _, stars, price = callback.data.split("_")
    
    await state.update_data(
        selected_item=f"Звёзды: {stars} ⭐",
        selected_price=int(price)
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
        f"👉 <b>Напишите @username получателя:</b>",
        parse_mode="HTML"
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
        f"📸 Теперь отправьте фото чека/перевода:"
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
        parse_mode="HTML"
    )
    
    # Отправляем уведомление админу
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
        "❌ Пожалуйста, отправьте фото чека (скриншот перевода)"
    )

@dp.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    """Админ одобряет платёж - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("У вас нет прав", show_alert=True)
        return
    
    payment_id = int(callback.data.split("_")[1])
    payment = db.get_payment(payment_id)
    
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    
    # Одобряем платёж
    db.approve_payment(payment_id, callback.from_user.id)
    
    # Уведомляем пользователя
    user_id = payment[1]
    item_name = payment[2]
    target_username = payment[5]
    
    try:
        await bot.send_message(
            user_id,
            f"✅ <b>Ваш платёж одобрен!</b>\n\n"
            f"🎁 {item_name}\n"
            f"📦 Для: @{target_username}\n\n"
            f"Спасибо за покупку!",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Не удалось уведомить пользователя: {e}")
    
    # Вместо edit_caption отправляем новое сообщение
    try:
        await callback.message.answer(
            "✅ <b>ПЛАТЁЖ ОДОБРЕН</b>\n\n"
            "Пользователь уведомлён.",
            parse_mode="HTML"
        )
    except:
        pass
    
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
        "❌ Укажите причину отказа (отправьте текстовое сообщение):"
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
            [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
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
            [InlineKeyboardButton(text="✍️ Написать отзыв", callback_data="write_review")],
            [InlineKeyboardButton(text="◀ Назад", callback_data="reviews")]
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
    
    # Проверяем, не оставлял ли уже отзыв
    if db.has_user_reviewed(user_id):
        await callback.answer("❌ Вы уже оставляли отзыв", show_alert=True)
        return
    
    await callback.message.edit_text(
        "✍️ <b>Напишите ваш отзыв</b>\n\n"
        "Отправьте текстовое сообщение с вашим отзывом:",
        parse_mode="HTML"
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
    
    # Уведомляем админов о новом отзыве
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
        "По всем вопросам обращайтесь к администратору:\n"
        "@killjocer",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀ Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

# === ЗАПУСК ===
async def main():
    print("🚀 Бот запущен и готов к работе!")
    print(f"👑 Админ ID: {config.ADMIN_IDS}")
    print(f"📱 Поддержка: @killjocer")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())