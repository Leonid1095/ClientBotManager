# bot.py
# Основной файл Telegram-бота для заказов

import logging
import uuid
import asyncio
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

from config import *
from menu import main_menu
from states import OrderForm, SupportChat, AdminReply
from faq import FAQ_LIST
from portfolio import PORTFOLIO
from reviews import REVIEWS, PENDING_REVIEWS, get_rating_stars
from calc import calculate_price
from data import save_ticket, get_ticket_status, TICKETS_DB, REFERRALS_DB, BONUSES_DB
from backup import BackupManager
from content_manager import content_manager
from admin_panel import register_admin_handlers

# Значения по умолчанию для параметров бекапа (если не определены в config.py)
try:
    BACKUP_ENABLED
except NameError:
    BACKUP_ENABLED = True

try:
    BACKUP_INTERVAL_DAYS
except NameError:
    BACKUP_INTERVAL_DAYS = 7

try:
    BACKUP_DIR
except NameError:
    BACKUP_DIR = "backups"

try:
    BACKUP_KEEP_COUNT
except NameError:
    BACKUP_KEEP_COUNT = 10

# Настройка логирования (красивый формат)
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT, datefmt="%Y-%m-%d %H:%M:%S")

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Инициализация менеджера бекапов
backup_manager = BackupManager(BACKUP_DIR)
last_backup_time = None

# Тексты кнопок
MENU_TEXT = "🏠 Меню"
BACK_TEXT = "⬅️ Назад"

ORDER_TEXT = "📝 Заказать бота"
PORTFOLIO_TEXT = "💼 Портфолио"
FAQ_TEXT = "❓ FAQ"
SUPPORT_TEXT = "💬 Чат поддержки"
CALC_TEXT = "🧮 Калькулятор стоимости"
STATUS_TEXT = "📦 Статус заказа"
ABOUT_TEXT = "👤 О себе"
CONTACT_TEXT = "📞 Связаться с разработчиком"
REVIEWS_TEXT = "⭐ Отзывы"
BONUS_TEXT = "🎁 Бонусы и рефералы"


def get_back_keyboard() -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add(KeyboardButton(BACK_TEXT), KeyboardButton(MENU_TEXT))
    return kb


def get_main_inline_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("📝 Заказать", callback_data="menu_order"),
        InlineKeyboardButton("💼 Портфолио", callback_data="menu_portfolio"),
        InlineKeyboardButton("❓ FAQ", callback_data="menu_faq"),
        InlineKeyboardButton("🧮 Калькулятор", callback_data="menu_calc"),
        InlineKeyboardButton("📞 Связаться", callback_data="menu_contact"),
    )
    return kb


def get_bot_intro_text() -> str:
    return (
        "<b>ClientBotManager</b> — бот для приёма заказов на разработку.\n\n"
        "<b>Что умеет:</b>\n"
        "• Принимает заявки через анкету\n"
        "• Показывает портфолио и FAQ\n"
        "• Считает стоимость проекта\n"
        "• Ведёт статусы заказов\n"
        "• Хранит отзывы и бонусы\n"
    )


async def send_main_menu(message: types.Message) -> None:
    text = get_bot_intro_text() + "\nВыберите действие в меню или кнопках ниже."
    await message.answer(text, parse_mode="HTML", reply_markup=main_menu)
    await message.answer("Быстрые действия:", reply_markup=get_main_inline_keyboard())

# FSM классы
class StatusForm(StatesGroup):
    order_id = State()

class CalcState(StatesGroup):
    type_bot = State()
    complexity = State()
    hosting = State()

class ReviewForm(StatesGroup):
    text = State()


# ==============================================
# ОБРАБОТЧИКИ КОМАНД
# ==============================================

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    """Обработка команды /start и реферальных ссылок"""
    args = message.get_args()
    user_id = message.from_user.id
    
    # Обработка реферальной ссылки
    if args and args.startswith('ref'):
        try:
            ref_id = int(args[3:])
            if ref_id != user_id:
                REFERRALS_DB.setdefault(ref_id, []).append(user_id)
                BONUSES_DB[ref_id] = BONUSES_DB.get(ref_id, 0) + 100  # 100 руб. бонус
        except ValueError:
            pass
    
    await send_main_menu(message)


@dp.message_handler(commands=['menu'])
async def show_menu(message: types.Message):
    await send_main_menu(message)


@dp.message_handler(lambda m: m.text == MENU_TEXT, state='*')
async def show_menu_button(message: types.Message, state: FSMContext):
    if state:
        await state.finish()
    await send_main_menu(message)


@dp.message_handler(lambda m: m.text == BACK_TEXT, state='*')
async def back_to_menu(message: types.Message, state: FSMContext):
    if state:
        await state.finish()
    await send_main_menu(message)


# ==============================================
# ОБРАБОТЧИКИ МЕНЮ
# ==============================================

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("menu_"))
async def handle_inline_menu(callback_query: types.CallbackQuery):
    action = callback_query.data.replace("menu_", "")
    if action == "order":
        await handle_order(callback_query.message)
    elif action == "portfolio":
        await handle_portfolio(callback_query.message)
    elif action == "faq":
        await handle_faq(callback_query.message)
    elif action == "calc":
        await handle_calc(callback_query.message)
    elif action == "contact":
        await handle_contact_dev(callback_query.message)
    await callback_query.answer()

@dp.message_handler(lambda m: m.text == PORTFOLIO_TEXT)
async def handle_portfolio(message: types.Message):
    """Показ портфолио с кнопками для просмотра кейсов"""
    portfolio = content_manager.get_portfolio()
    if not portfolio:
        await message.answer("❌ Портфолио пусто", reply_markup=get_back_keyboard())
        return
    
    for case in portfolio:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Посмотреть кейс", callback_data=f"case_{case['id']}")
        )
        text = f"<b>{case['title']}</b>\n{case['desc']}"
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    await message.answer("Выберите кейс или вернитесь в меню.", reply_markup=get_back_keyboard())

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("case_"))
async def show_case_details(callback_query: types.CallbackQuery):
    """Показ подробностей кейса"""
    case_id = callback_query.data.split('_')[1]
    portfolio = content_manager.get_portfolio()
    case = next((c for c in portfolio if c['id'] == case_id), None)
    if case:
        await callback_query.message.answer(
            f"<b>{case['title']}</b>\n{case['details']}", 
            parse_mode="HTML"
        )
    await callback_query.answer()


@dp.message_handler(lambda m: m.text == FAQ_TEXT)
async def handle_faq(message: types.Message):
    """Показ часто задаваемых вопросов"""
    faq = content_manager.get_faq()
    if not faq:
        await message.answer("❌ FAQ пусто", reply_markup=get_back_keyboard())
        return
    
    text = "<b>FAQ — Часто задаваемые вопросы:</b>\n"
    for item in faq:
        text += f"\n<b>Q:</b> {item['q']}\n<b>A:</b> {item['a']}\n"
    await message.answer(text, parse_mode="HTML", reply_markup=get_back_keyboard())


@dp.message_handler(lambda m: m.text == SUPPORT_TEXT)
async def handle_support(message: types.Message):
    """Активировать чат с поддержкой"""
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "Неизвестно"
    
    await SupportChat.waiting_message.set()
    
    await message.answer(
        "💬 <b>Чат поддержки активирован!</b>\n\n"
        "Напишите ваш вопрос, и я получу его лично.\n"
        "Вы можете отправлять текст, фото, файлы.\n\n"
        "Для выхода нажмите /menu или 🏠 Меню",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )
    
    # Уведомляем админа
    try:
        await bot.send_message(
            ADMIN_USER_ID,
            f"📨 <b>Новое обращение в поддержку</b>\n\n"
            f"👤 <b>Пользователь:</b> {full_name}\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"📱 <b>Username:</b> @{username}\n\n"
            f"<i>Ожидает ответа...</i>",
            parse_mode="HTML"
        )
    except:
        pass


@dp.message_handler(state=SupportChat.waiting_message, content_types=['text', 'photo', 'document', 'video', 'voice', 'audio'])
async def process_support_message(message: types.Message, state: FSMContext):
    """Обработка сообщения в чате поддержки"""
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    full_name = message.from_user.full_name or "Неизвестно"
    
    # Формируем информацию об отправителе
    user_info = (
        f"💬 <b>Сообщение от пользователя</b>\n\n"
        f"👤 {full_name}\n"
        f"🆔 <code>{user_id}</code>\n"
        f"📱 @{username}\n\n"
    )
    
    # Отправляем админу в зависимости от типа контента
    try:
        if message.text:
            await bot.send_message(
                ADMIN_USER_ID,
                user_info + f"📝 <b>Текст:</b>\n{message.text}\n\n"
                f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        elif message.photo:
            await bot.send_photo(
                ADMIN_USER_ID,
                message.photo[-1].file_id,
                caption=user_info + (f"📝 {message.caption}\n\n" if message.caption else "") +
                f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                ADMIN_USER_ID,
                message.document.file_id,
                caption=user_info + (f"📝 {message.caption}\n\n" if message.caption else "") +
                f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        elif message.video:
            await bot.send_video(
                ADMIN_USER_ID,
                message.video.file_id,
                caption=user_info + (f"📝 {message.caption}\n\n" if message.caption else "") +
                f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        elif message.voice:
            await bot.send_voice(
                ADMIN_USER_ID,
                message.voice.file_id,
                caption=user_info + f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        elif message.audio:
            await bot.send_audio(
                ADMIN_USER_ID,
                message.audio.file_id,
                caption=user_info + (f"📝 {message.caption}\n\n" if message.caption else "") +
                f"<i>Ответить: /reply {user_id}</i>",
                parse_mode="HTML"
            )
        
        await message.answer(
            "✅ Ваше сообщение отправлено!\n"
            "Ожидайте ответа от поддержки.",
            reply_markup=get_back_keyboard()
        )
    except Exception as e:
        await message.answer(
            "❌ Ошибка при отправке сообщения.\n"
            "Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )


@dp.message_handler(commands=['reply'])
async def cmd_reply_start(message: types.Message, state: FSMContext):
    """Админ начинает ответ пользователю"""
    if not is_admin(message.from_user.id):
        return
    
    # Проверяем формат команды: /reply USER_ID
    parts = message.text.split(maxsplit=1)
    
    if len(parts) == 1:
        await message.answer(
            "📝 <b>Ответ пользователю</b>\n\n"
            "Использование:\n"
            "<code>/reply USER_ID</code>\n\n"
            "Затем отправьте текст ответа.",
            parse_mode="HTML"
        )
        await AdminReply.waiting_user_id.set()
        return
    
    # Если указан сразу USER_ID
    try:
        user_id = int(parts[1])
        await message.answer(
            f"✉️ <b>Отправка ответа пользователю {user_id}</b>\n\n"
            f"Напишите текст ответа:",
            parse_mode="HTML"
        )
        await state.update_data(reply_to_user_id=user_id)
        await AdminReply.waiting_message.set()
    except ValueError:
        await message.answer("❌ Неверный формат USER_ID. Должно быть число.")


@dp.message_handler(state=AdminReply.waiting_user_id)
async def process_reply_user_id(message: types.Message, state: FSMContext):
    """Админ указал ID пользователя"""
    try:
        user_id = int(message.text.strip())
        await state.update_data(reply_to_user_id=user_id)
        await message.answer(
            f"✉️ <b>Отправка ответа пользователю {user_id}</b>\n\n"
            f"Напишите текст ответа:",
            parse_mode="HTML"
        )
        await AdminReply.waiting_message.set()
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Введите числовой ID пользователя:"
        )


@dp.message_handler(state=AdminReply.waiting_message, content_types=['text', 'photo', 'document', 'video'])
async def process_reply_message(message: types.Message, state: FSMContext):
    """Админ отправил ответ пользователю"""
    data = await state.get_data()
    user_id = data.get('reply_to_user_id')
    
    if not user_id:
        await message.answer("❌ Ошибка: ID пользователя не найден")
        await state.finish()
        return
    
    try:
        # Отправляем ответ пользователю
        if message.text:
            await bot.send_message(
                user_id,
                f"💬 <b>Ответ от поддержки:</b>\n\n{message.text}",
                parse_mode="HTML"
            )
        elif message.photo:
            await bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=f"💬 <b>Ответ от поддержки:</b>\n\n{message.caption or ''}",
                parse_mode="HTML"
            )
        elif message.document:
            await bot.send_document(
                user_id,
                message.document.file_id,
                caption=f"💬 <b>Ответ от поддержки:</b>\n\n{message.caption or ''}",
                parse_mode="HTML"
            )
        elif message.video:
            await bot.send_video(
                user_id,
                message.video.file_id,
                caption=f"💬 <b>Ответ от поддержки:</b>\n\n{message.caption or ''}",
                parse_mode="HTML"
            )
        
        await message.answer(
            f"✅ Ответ отправлен пользователю <code>{user_id}</code>",
            parse_mode="HTML"
        )
    except Exception as e:
        await message.answer(
            f"❌ Ошибка при отправке: {str(e)}\n\n"
            f"Возможно, пользователь заблокировал бота."
        )
    
    await state.finish()


@dp.message_handler(lambda m: m.text == ABOUT_TEXT)
async def handle_about(message: types.Message):
    """Информация о компании"""
    about_text = content_manager.get_about()
    await message.answer(
        about_text,
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


@dp.message_handler(lambda m: m.text == CONTACT_TEXT)
async def handle_contact_dev(message: types.Message):
    """Контакты разработчика"""
    contacts = content_manager.get_contacts()
    
    text = "📞 <b>Контакты</b>\n"
    if contacts.get('telegram'):
        text += f"Telegram: {contacts['telegram']}\n"
    if contacts.get('email'):
        text += f"Email: {contacts['email']}\n"
    if contacts.get('phone'):
        text += f"Телефон: {contacts['phone']}\n"
    if contacts.get('whatsapp'):
        text += f"WhatsApp: {contacts['whatsapp']}\n"
    
    await message.answer(text, parse_mode="HTML", reply_markup=get_back_keyboard())


@dp.message_handler(lambda m: m.text == BONUS_TEXT)
async def handle_bonuses(message: types.Message):
    """Показ реферальной ссылки и бонусов"""
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref{user_id}"
    invited = REFERRALS_DB.get(user_id, [])
    bonus = BONUSES_DB.get(user_id, 0)
    text = (
        f"Ваша реферальная ссылка:\n{ref_link}\n"
        f"Приглашено пользователей: {len(invited)}\n"
        f"Ваш бонус: {bonus} руб.\n"
        "\nПригласите друга — получите бонус за каждый оплаченный заказ!"
    )
    await message.answer(text, reply_markup=get_back_keyboard())


# ==============================================
# ОТЗЫВЫ
# ==============================================

@dp.message_handler(lambda m: m.text == REVIEWS_TEXT)
async def handle_reviews(message: types.Message):
    """Просмотр отзывов"""
    if not REVIEWS:
        await message.answer(
            "📋 Отзывы клиентов пока отсутствуют.\n\n"
            "Будьте первым! Оставьте отзыв о нашей работе.",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✍️ Оставить отзыв", callback_data="review_add")
            )
        )
        return
    
    # Показываем отзывы
    text = "⭐ <b>Отзывы клиентов:</b>\n\n"
    for review in REVIEWS:
        stars = get_rating_stars(review.get("rating", 5))
        date = review.get("date", "")
        text += f"{stars}\n"
        text += f"<b>{review['author']}</b>"
        if date:
            text += f" • {date}"
        text += f"\n{review['text']}\n\n"
    
    text += "Хотите оставить отзыв? Нажмите кнопку ниже."
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("✍️ Оставить отзыв", callback_data="review_add")
    )
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.callback_query_handler(lambda c: c.data == "review_add")
async def start_review_inline(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Напишите ваш отзыв:")
    await ReviewForm.text.set()
    await callback_query.answer()

@dp.message_handler(lambda m: m.text.lower() == 'оставить отзыв')
async def start_review(message: types.Message):
    """Начало добавления отзыва"""
    await message.answer("Напишите ваш отзыв:")
    await ReviewForm.text.set()

@dp.message_handler(state=ReviewForm.text)
async def save_review(message: types.Message, state: FSMContext):
    """Сохранение отзыва в очередь модерации"""
    user_id = message.from_user.id
    author = message.from_user.first_name or "Анонимный пользователь"
    
    # Добавляем отзыв в очередь модерации
    review_id = f"rev_pending_{len(PENDING_REVIEWS) + 1}"
    PENDING_REVIEWS.append({
        "id": review_id,
        "author": author,
        "rating": 5,  # По умолчанию 5 звёзд
        "text": message.text,
        "user_id": user_id,
        "date": datetime.now().isoformat()
    })
    
    await message.answer(
        "✅ Спасибо за ваш отзыв! Он будет опубликован после проверки модератором.",
        reply_markup=get_back_keyboard()
    )
    
    # Уведомляем администратора
    try:
        await bot.send_message(
            ADMIN_USER_ID,
            f"📝 <b>Новый отзыв на модерацию:</b>\n\n"
            f"<b>Автор:</b> {author}\n"
            f"<b>Текст:</b> {message.text}\n\n"
            f"<b>ID:</b> {review_id}\n"
            f"<b>User ID:</b> {user_id}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_review_{review_id}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_review_{review_id}")
            )
        )
    except Exception as e:
        logging.error(f"Не удалось отправить уведомление администратору: {e}")
    
    await state.finish()


# ==============================================
# СТАТУС ЗАКАЗА
# ==============================================

@dp.message_handler(lambda m: m.text == STATUS_TEXT)
async def handle_status(message: types.Message):
    """Проверка статуса заказов по user_id"""
    user_id = message.from_user.id
    status = get_ticket_status(user_id)
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔎 Проверить по номеру", callback_data="status_by_id")
    )
    await message.answer(status, reply_markup=kb)


# ==============================================
# УПРАВЛЕНИЕ БЕКАПАМИ (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА)
# ==============================================

def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id == ADMIN_USER_ID


async def create_backup_now() -> str:
    """Создает бекап всех данных"""
    global last_backup_time
    
    data_to_backup = {
        "tickets": TICKETS_DB,
        "referrals": REFERRALS_DB,
        "bonuses": BONUSES_DB,
        "reviews": REVIEWS
    }
    
    backup_path = backup_manager.create_backup(data_to_backup)
    if backup_path:
        last_backup_time = datetime.now()
        # Очистка старых бекапов
        backup_manager.cleanup_old_backups(BACKUP_KEEP_COUNT)
        return f"✅ Бекап создан успешно:\n{backup_path}"
    else:
        return "❌ Ошибка при создании бекапа"


@dp.message_handler(commands=['admin'])
async def cmd_admin(message: types.Message):
    """Открыть настройки администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return
    
    # Создаем главное админ-меню
    msg = await message.answer("⏳ Загрузка панели администратора...")
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📝 Управление контентом", callback_data="admin_content_menu"),
        InlineKeyboardButton("💾 Управление бекапами", callback_data="admin_backup_menu"),
        InlineKeyboardButton("⭐ Модерация отзывов", callback_data="admin_reviews_menu"),
        InlineKeyboardButton("📊 Общая статистика", callback_data="admin_main_stats"),
        InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
    )
    
    text = """⚙️ <b>НАСТРОЙКИ АДМИНИСТРАТОРА</b>

Выбери раздел:"""
    
    await msg.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


@dp.message_handler(commands=['backup'])

async def cmd_backup(message: types.Message):
    """Команда для создания бекапа вручную (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return
    
    result = await create_backup_now()
    await message.answer(result)


@dp.message_handler(commands=['backup_list'])
async def cmd_backup_list(message: types.Message):
    """Список всех бекапов (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return
    
    backups = backup_manager.list_backups()
    
    if not backups:
        await message.answer("📂 Бекапы не найдены.")
        return
    
    text = "📂 <b>Список бекапов:</b>\n\n"
    
    for i, backup in enumerate(backups, 1):
        filename = backup['filename']
        size_kb = backup['size_kb']
        metadata = backup.get('metadata', {})
        
        text += f"{i}. <code>{filename}</code>\n"
        text += f"   Размер: {size_kb} KB\n"
        
        if metadata:
            created = metadata.get('created_at', 'неизвестно')
            records = metadata.get('records_count', {})
            text += f"   Создан: {created}\n"
            text += f"   Записей: {records.get('tickets', 0)} заказов, "
            text += f"{records.get('reviews', 0)} отзывов\n"
        
        text += "\n"
    
    # Создаем инлайн-кнопки для восстановления
    kb = InlineKeyboardMarkup(row_width=1)
    for backup in backups[:5]:  # Показываем только первые 5
        kb.add(InlineKeyboardButton(
            f"Восстановить {backup['filename'][:20]}...",
            callback_data=f"restore_{backup['filename']}"
        ))
    
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@dp.message_handler(commands=['backup_settings'])
async def cmd_backup_settings(message: types.Message):
    """Настройки автоматического бекапа (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return
    
    text = (
        "⚙️ <b>Настройки автоматического бекапа:</b>\n\n"
        f"Включено: {'✅' if BACKUP_ENABLED else '❌'}\n"
        f"Интервал: {BACKUP_INTERVAL_DAYS} дней\n"
        f"Директория: {BACKUP_DIR}\n"
        f"Хранить бекапов: {BACKUP_KEEP_COUNT} шт.\n"
    )
    
    if last_backup_time:
        next_backup = last_backup_time + timedelta(days=BACKUP_INTERVAL_DAYS)
        text += f"\nПоследний бекап: {last_backup_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        text += f"Следующий бекап: {next_backup.strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    text += "\n💡 Для изменения настроек отредактируйте файл config.py"
    
    await message.answer(text, parse_mode="HTML")


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("restore_"))
async def handle_restore_backup(callback_query: types.CallbackQuery):
    """Восстановление данных из бекапа"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещен", show_alert=True)
        return
    
    filename = callback_query.data.replace("restore_", "")
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    # Запрашиваем подтверждение
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Да, восстановить", callback_data=f"confirm_restore_{filename}"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_restore")
    )
    
    await callback_query.message.answer(
        f"⚠️ <b>Внимание!</b>\n\n"
        f"Вы уверены, что хотите восстановить данные из бекапа?\n"
        f"<code>{filename}</code>\n\n"
        f"Текущие данные будут заменены!",
        parse_mode="HTML",
        reply_markup=kb
    )
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("confirm_restore_"))
async def confirm_restore_backup(callback_query: types.CallbackQuery):
    """Подтверждение восстановления бекапа"""
    global REFERRALS_DB, BONUSES_DB
    
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещен", show_alert=True)
        return
    
    filename = callback_query.data.replace("confirm_restore_", "")
    backup_path = os.path.join(BACKUP_DIR, filename)
    
    restored_data = backup_manager.restore_backup(backup_path)
    
    if restored_data:
        # Восстанавливаем данные
        from data import TICKETS_DB
        
        TICKETS_DB.clear()
        TICKETS_DB.update(restored_data.get('tickets', {}))
        
        REFERRALS_DB.clear()
        REFERRALS_DB.update(restored_data.get('referrals', {}))
        
        BONUSES_DB.clear()
        BONUSES_DB.update(restored_data.get('bonuses', {}))
        
        REVIEWS.clear()
        REVIEWS.extend(restored_data.get('reviews', []))
        
        await callback_query.message.answer(
            f"✅ Данные успешно восстановлены из бекапа:\n<code>{filename}</code>",
            parse_mode="HTML"
        )
    else:
        await callback_query.message.answer("❌ Ошибка при восстановлении бекапа")
    
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "cancel_restore")
async def cancel_restore(callback_query: types.CallbackQuery):
    """Отмена восстановления"""
    await callback_query.message.answer("❌ Восстановление отменено")
    await callback_query.answer()


# ==============================================
# МОДЕРАЦИЯ ОТЗЫВОВ (ТОЛЬКО ДЛЯ АДМИНИСТРАТОРА)
# ==============================================

@dp.callback_query_handler(lambda c: c.data and c.data.startswith("approve_review_"))
async def approve_review(callback_query: types.CallbackQuery):
    """Одобрить отзыв"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback_query.data.replace("approve_review_", "")
    
    # Найти отзыв в очереди модерации
    review = None
    for i, r in enumerate(PENDING_REVIEWS):
        if r["id"] == review_id:
            review = PENDING_REVIEWS.pop(i)
            break
    
    if review:
        # Добавить в опубликованные отзывы
        review_to_add = {
            "id": review["id"],
            "author": review["author"],
            "rating": review.get("rating", 5),
            "text": review["text"],
            "date": review.get("date", datetime.now().isoformat())
        }
        REVIEWS.append(review_to_add)
        
        await callback_query.message.edit_text(
            f"✅ <b>Отзыв одобрен!</b>\n\n"
            f"<b>Автор:</b> {review['author']}\n"
            f"<b>Текст:</b> {review['text']}",
            parse_mode="HTML"
        )
        
        # Уведомить пользователя (если у нас есть его ID)
        try:
            await bot.send_message(
                review["user_id"],
                "✅ Ваш отзыв одобрен и опубликован! Спасибо за отзыв!"
            )
        except:
            pass
    else:
        await callback_query.message.edit_text("❌ Отзыв не найден")
    
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data and c.data.startswith("reject_review_"))
async def reject_review(callback_query: types.CallbackQuery):
    """Отклонить отзыв (спам, реклама и т.д.)"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещен", show_alert=True)
        return
    
    review_id = callback_query.data.replace("reject_review_", "")
    
    # Найти и удалить отзыв из очереди модерации
    review = None
    for i, r in enumerate(PENDING_REVIEWS):
        if r["id"] == review_id:
            review = PENDING_REVIEWS.pop(i)
            break
    
    if review:
        await callback_query.message.edit_text(
            f"❌ <b>Отзыв отклонен!</b>\n\n"
            f"<b>Автор:</b> {review['author']}\n"
            f"<b>Текст:</b> {review['text']}\n\n"
            f"<i>Причина: спам, реклама или несоответствие правилам</i>",
            parse_mode="HTML"
        )
        
        # Уведомить пользователя
        try:
            await bot.send_message(
                review["user_id"],
                "❌ К сожалению, ваш отзыв не был опубликован.\n\n"
                "Причина: содержимое не соответствует нашим правилам.\n"
                "Пожалуйста, попробуйте оставить отзыв без ссылок и контактов."
            )
        except:
            pass
    else:
        await callback_query.message.edit_text("❌ Отзыв не найден")
    
    await callback_query.answer()


@dp.message_handler(commands=['reviews_pending'])
async def cmd_reviews_pending(message: types.Message):
    """Показать отзывы в очереди модерации (только для админа)"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ Эта команда доступна только администратору.")
        return
    
    if not PENDING_REVIEWS:
        await message.answer("📋 Нет отзывов на модерацию.")
        return
    
    text = f"📋 <b>Отзывы на модерацию ({len(PENDING_REVIEWS)}):</b>\n\n"
    
    for i, review in enumerate(PENDING_REVIEWS, 1):
        text += f"{i}. <b>{review['author']}</b> ({get_rating_stars(review.get('rating', 5))})\n"
        text += f"   {review['text'][:50]}...\n"
        text += f"   ID: <code>{review['id']}</code>\n\n"
    
    # Создаем кнопки для модерации первого отзыва
    if PENDING_REVIEWS:
        first_review = PENDING_REVIEWS[0]
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_review_{first_review['id']}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_review_{first_review['id']}")
        )
        await message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(text, parse_mode="HTML")


# ==============================================
# ОБРАБОТЧИКИ АДМИН-ПАНЕЛИ
# ==============================================

@dp.callback_query_handler(lambda c: c.data == "admin_backup_create")
async def admin_backup_create_callback(callback_query: types.CallbackQuery):
    """Создать бекап из админ-панели"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещён", show_alert=True)
        return
    
    await callback_query.message.edit_text("⏳ Создаю бекап...")
    result = await create_backup_now()
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_backup_menu"))
    
    await callback_query.message.edit_text(result, reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "admin_backup_list")
async def admin_backup_list_callback(callback_query: types.CallbackQuery):
    """Список бекапов из админ-панели"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещён", show_alert=True)
        return
    
    backups = backup_manager.list_backups()
    
    if not backups:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_backup_menu"))
        await callback_query.message.edit_text("📂 Бекапы не найдены.", reply_markup=keyboard)
        return
    
    text = "📂 <b>Список бекапов:</b>\n\n"
    
    for i, backup in enumerate(backups[:10], 1):
        filename = backup['filename']
        size_kb = backup['size_kb']
        metadata = backup.get('metadata', {})
        
        text += f"{i}. <code>{filename}</code>\n"
        text += f"   Размер: {size_kb} KB\n"
        
        if metadata:
            created = metadata.get('created_at', 'неизвестно')
            text += f"   Создан: {created}\n"
        
        text += "\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_backup_menu"))
    
    await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "admin_backup_settings")
async def admin_backup_settings_callback(callback_query: types.CallbackQuery):
    """Настройки бекапов из админ-панели"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещён", show_alert=True)
        return
    
    status = "✅ Включены" if BACKUP_ENABLED else "❌ Выключены"
    
    text = f"""⚙️ <b>НАСТРОЙКИ БЕКАПОВ</b>

<b>Статус:</b> {status}
<b>Интервал:</b> {BACKUP_INTERVAL_DAYS} дней
<b>Хранить:</b> {BACKUP_KEEP_COUNT} последних бекапов
<b>Директория:</b> <code>{BACKUP_DIR}</code>

<i>Для изменения настроек отредактируй config.py</i>"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_backup_menu"))
    
    await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback_query.answer()


@dp.callback_query_handler(lambda c: c.data == "admin_reviews_pending")
async def admin_reviews_pending_callback(callback_query: types.CallbackQuery):
    """Модерация отзывов из админ-панели"""
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⛔️ Доступ запрещён", show_alert=True)
        return
    
    if not PENDING_REVIEWS:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_reviews_menu"))
        await callback_query.message.edit_text(
            "✅ Нет отзывов на модерации!", 
            reply_markup=keyboard
        )
        return
    
    first_review = PENDING_REVIEWS[0]
    stars = get_rating_stars(first_review["rating"])
    
    text = f"""📝 <b>Отзыв на модерации</b> (1 из {len(PENDING_REVIEWS)})

<b>Автор:</b> {first_review['author']}
<b>Рейтинг:</b> {stars}
<b>Текст:</b>
{first_review['text']}

Одобрить или отклонить?"""
    
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Одобрить", callback_data=f"approve_review_{first_review['id']}"),
        InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_review_{first_review['id']}"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_reviews_menu")
    )
    
    await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback_query.answer()


# ==============================================
# СТАТУС ЗАКАЗА
# ==============================================

@dp.callback_query_handler(lambda c: c.data == "status_by_id")
async def status_by_id(callback_query: types.CallbackQuery):
    await callback_query.message.answer("Введите номер заказа:")
    await StatusForm.order_id.set()
    await callback_query.answer()

@dp.message_handler(state=StatusForm.order_id)
async def process_status(message: types.Message, state: FSMContext):
    """Проверка статуса конкретного заказа"""
    order_id = message.text.strip()
    user_id = message.from_user.id
    status = get_ticket_status(user_id, order_id)
    await message.answer(status)
    await state.finish()


# ==============================================
# КАЛЬКУЛЯТОР СТОИМОСТИ
# ==============================================

@dp.message_handler(lambda m: m.text == CALC_TEXT)
async def handle_calc(message: types.Message):
    """Начало расчёта стоимости"""
    await message.answer("Выберите тип бота: магазин/обычный")
    await CalcState.type_bot.set()

@dp.message_handler(state=CalcState.type_bot)
async def calc_type_bot(message: types.Message, state: FSMContext):
    await state.update_data(type_bot=message.text)
    await message.answer("Сложность: обычный/сложный")
    await CalcState.next()

@dp.message_handler(state=CalcState.complexity)
async def calc_complexity(message: types.Message, state: FSMContext):
    await state.update_data(complexity=message.text)
    await message.answer("Где будет размещён бот? мой сервер/ваш сервер")
    await CalcState.next()

@dp.message_handler(state=CalcState.hosting)
async def calc_hosting(message: types.Message, state: FSMContext):
    """Финальный расчёт стоимости с учётом бонусов"""
    await state.update_data(hosting=message.text)
    data = await state.get_data()
    user_id = message.from_user.id
    bonus = BONUSES.get(user_id, 0)
    price_without_bonus = calculate_price(data['type_bot'], data['complexity'], data['hosting'])
    price_with_bonus = calculate_price(data['type_bot'], data['complexity'], data['hosting'], bonus)
    if bonus > 0:
        await message.answer(
            f"Примерная стоимость: {price_without_bonus} руб.\n"
            f"С учетом ваших бонусов ({bonus} руб.): {price_with_bonus} руб."
        )
    else:
        await message.answer(f"Примерная стоимость: {price_without_bonus} руб.")
    await state.finish()


# ==============================================
# FSM ЗАКАЗА БОТА
# ==============================================

@dp.message_handler(lambda m: m.text == ORDER_TEXT)
async def handle_order(message: types.Message):
    """Начало оформления заказа"""
    await message.answer(
        "Для заказа бота заполните, пожалуйста, небольшую анкету.\n\n"
        "Ваши ФИО:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")
        )
    )
    await OrderForm.fio.set()


@dp.callback_query_handler(lambda c: c.data == "cancel_order", state='*')
async def cancel_order_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Отмена оформления заказа (универсальный обработчик)"""
    await callback_query.message.edit_text("❌ Оформление заказа отменено.")
    if state:
        await state.finish()
    await callback_query.answer()


@dp.message_handler(lambda m: m.text.lower() == 'отмена', state=OrderForm)
async def cancel_order_text(message: types.Message, state: FSMContext):
    """Отмена оформления заказа через текстовое сообщение"""
    await message.answer("❌ Оформление заказа отменено.", reply_markup=get_back_keyboard())
    await state.finish()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel_order"))
    return kb

@dp.message_handler(state=OrderForm.fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer(
        "Ваши контактные данные (телефон, email, Telegram):",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer(
        "Опишите вашу идею для бота:",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.idea)
async def process_idea(message: types.Message, state: FSMContext):
    await state.update_data(idea=message.text)
    await message.answer(
        "Выберите тип бота (чат-бот, магазин, интеграция и т.д.):",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.type_bot)
async def process_type_bot(message: types.Message, state: FSMContext):
    await state.update_data(type_bot=message.text)
    await message.answer(
        "Укажите желаемый бюджет:",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.budget)
async def process_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text)
    await message.answer(
        "Укажите желаемые сроки:",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    await message.answer(
        "Выберите тариф или опции (опишите, если есть):",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.options)
async def process_options(message: types.Message, state: FSMContext):
    await state.update_data(options=message.text)
    await message.answer(
        "Есть ли особые настройки или пожелания?",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.settings)
async def process_settings(message: types.Message, state: FSMContext):
    await state.update_data(settings=message.text)
    await message.answer(
        "Прикрепите файл (если есть) или напишите 'нет':",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=OrderForm.file)
async def process_file(message: types.Message, state: FSMContext):
    file_id = message.document.file_id
    await state.update_data(file=file_id)
    await message.answer(
        "Где будет размещён бот?\n1. Ваш сервер\n2. Мой сервер (аренда)",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(lambda m: m.text.lower() == 'нет', state=OrderForm.file)
async def process_no_file(message: types.Message, state: FSMContext):
    await state.update_data(file=None)
    await message.answer(
        "Где будет размещён бот?\n1. Ваш сервер\n2. Мой сервер (аренда)",
        reply_markup=get_cancel_keyboard()
    )
    await OrderForm.next()

@dp.message_handler(state=OrderForm.hosting)
async def process_hosting(message: types.Message, state: FSMContext):
    """Обработка хостинга и предложение использовать бонусы"""
    await state.update_data(hosting=message.text)
    user_id = message.from_user.id
    bonus = BONUSES_DB.get(user_id, 0)
    
    if bonus > 0:
        await message.answer(
            f"У вас есть бонусы: {bonus} руб.\nИспользовать бонусы для скидки? (да/нет)",
            reply_markup=get_cancel_keyboard()
        )
        await OrderForm.next()
    else:
        await state.update_data(use_bonus=False, bonus_amount=0)
        data = await state.get_data()
        summary = _format_order_summary(data)
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("✅ Подтверждаю", callback_data="confirm_order"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")
        )
        await message.answer(summary + "\nЕсли всё верно, нажмите 'Подтверждаю'.", reply_markup=kb)
        await OrderForm.confirm.set()

@dp.message_handler(state=OrderForm.use_bonus)
async def process_use_bonus(message: types.Message, state: FSMContext):
    """Обработка решения об использовании бонусов"""
    user_id = message.from_user.id
    bonus = BONUSES_DB.get(user_id, 0)
    
    if message.text.lower() == 'да':
        await state.update_data(use_bonus=True, bonus_amount=bonus)
        discount_text = f"\nПрименена скидка: {bonus} руб."
    else:
        await state.update_data(use_bonus=False, bonus_amount=0)
        discount_text = ""
    
    data = await state.get_data()
    summary = _format_order_summary(data) + discount_text
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Подтверждаю", callback_data="confirm_order"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel_order")
    )
    await message.answer(summary + "\nЕсли всё верно, нажмите 'Подтверждаю'.", reply_markup=kb)
    await OrderForm.confirm.set()

@dp.callback_query_handler(lambda c: c.data == "confirm_order", state=OrderForm.confirm)
async def process_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    """Подтверждение заказа через кнопку"""
    message = callback_query.message
    data = await state.get_data()
    order_id = str(uuid.uuid4())[:8]
    user_id = callback_query.from_user.id
    
    # Списываем бонусы если использовались
    bonus_text = ""
    if data.get('use_bonus', False):
        bonus_amount = data.get('bonus_amount', 0)
        BONUSES_DB[user_id] = BONUSES_DB.get(user_id, 0) - bonus_amount
        bonus_text = f"Использовано бонусов: {bonus_amount} руб.\n"
    
    # Формирование тикета для администратора
    ticket = (
        f"<b>🆕 Новая заявка на разработку бота:</b>\n\n"
        f"<b>ID заказа:</b> <code>{order_id}</code>\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>ФИО:</b> {data.get('fio', '-')}\n"
        f"<b>Контакты:</b> {data.get('contact', '-')}\n"
        f"<b>Идея:</b> {data.get('idea', '-')}\n"
        f"<b>Тип бота:</b> {data.get('type_bot', '-')}\n"
        f"<b>Бюджет:</b> {data.get('budget', '-')}\n"
        f"<b>Сроки:</b> {data.get('deadline', '-')}\n"
        f"<b>Тариф/опции:</b> {data.get('options', '-')}\n"
        f"<b>Настройки:</b> {data.get('settings', '-')}\n"
        f"<b>Файл:</b> {'Приложен' if data.get('file') else 'Нет'}\n"
        f"<b>Хостинг:</b> {data.get('hosting', '-')}\n"
        f"{bonus_text}"
    )
    
    # Отправка клиенту
    await callback_query.message.edit_text(
        f"✅ <b>Спасибо! Ваша заявка принята.</b>\n\n"
        f"<b>Номер заказа:</b> <code>{order_id}</code>\n"
        f"Вы можете проверить статус через меню '📦 Статус заказа'.",
        parse_mode="HTML"
    )
    
    # Отправка администратору
    try:
        await bot.send_message(ADMIN_USER_ID, ticket, parse_mode="HTML")
        if data.get('file'):
            await bot.send_document(ADMIN_USER_ID, data['file'], caption=f"Файл к заявке #{order_id}")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
        await callback_query.message.answer("⚠️ Ошибка отправки администратору. Пожалуйста, свяжитесь напрямую.")
    
    # Сохраняем тикет (и в памяти и в Google Sheets)
    try:
        save_ticket(user_id, order_id, data)
    except Exception as e:
        logging.error(f"Ошибка при сохранении тикета: {e}")
    
    await state.finish()
    await callback_query.answer()

@dp.message_handler(lambda m: m.text.lower() == 'подтверждаю', state=OrderForm.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    """Подтверждение заказа (старый способ, для совместимости)"""
    data = await state.get_data()
    order_id = str(uuid.uuid4())[:8]
    user_id = message.from_user.id
    
    # Списываем бонусы если использовались
    bonus_text = ""
    if data.get('use_bonus', False):
        bonus_amount = data.get('bonus_amount', 0)
        BONUSES_DB[user_id] = BONUSES_DB.get(user_id, 0) - bonus_amount
        bonus_text = f"Использовано бонусов: {bonus_amount} руб.\n"
    
    # Формирование тикета для администратора
    ticket = (
        f"<b>🆕 Новая заявка на разработку бота:</b>\n\n"
        f"<b>ID заказа:</b> <code>{order_id}</code>\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>ФИО:</b> {data.get('fio', '-')}\n"
        f"<b>Контакты:</b> {data.get('contact', '-')}\n"
        f"<b>Идея:</b> {data.get('idea', '-')}\n"
        f"<b>Тип бота:</b> {data.get('type_bot', '-')}\n"
        f"<b>Бюджет:</b> {data.get('budget', '-')}\n"
        f"<b>Сроки:</b> {data.get('deadline', '-')}\n"
        f"<b>Тариф/опции:</b> {data.get('options', '-')}\n"
        f"<b>Настройки:</b> {data.get('settings', '-')}\n"
        f"<b>Файл:</b> {'Приложен' if data.get('file') else 'Нет'}\n"
        f"<b>Хостинг:</b> {data.get('hosting', '-')}\n"
        f"{bonus_text}"
    )
    
    # Отправка клиенту
    await message.answer(
        f"✅ <b>Спасибо! Ваша заявка принята.</b>\n\n"
        f"<b>Номер заказа:</b> <code>{order_id}</code>\n"
        f"Вы можете проверить статус через меню '📦 Статус заказа'.",
        parse_mode="HTML"
    )
    
    # Отправка администратору
    try:
        await bot.send_message(ADMIN_USER_ID, ticket, parse_mode="HTML")
        if data.get('file'):
            await bot.send_document(ADMIN_USER_ID, data['file'], caption=f"Файл к заявке #{order_id}")
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
        await message.answer("⚠️ Ошибка отправки администратору. Пожалуйста, свяжитесь напрямую.")
    
    # Сохраняем тикет (и в памяти и в Google Sheets)
    try:
        save_ticket(user_id, order_id, data)
    except Exception as e:
        logging.error(f"Ошибка при сохранении тикета: {e}")
    
    await state.finish()


# ==============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================

def _format_order_summary(data: dict) -> str:
    """Форматирование сводки заказа"""
    return (
        f"Проверьте заявку:\n"
        f"ФИО: {data['fio']}\n"
        f"Контакты: {data['contact']}\n"
        f"Идея: {data['idea']}\n"
        f"Тип бота: {data['type_bot']}\n"
        f"Бюджет: {data['budget']}\n"
        f"Сроки: {data['deadline']}\n"
        f"Тариф/опции: {data['options']}\n"
        f"Настройки: {data['settings']}\n"
        f"Файл: {'Есть' if data.get('file') else 'Нет'}\n"
        f"Хостинг: {data['hosting']}\n"
    )


# ==============================================
# ЗАПУСК БОТА
# ==============================================

async def periodic_backup():
    """Периодическое создание бекапов"""
    while True:
        try:
            # Ждем указанный интервал (в секундах)
            await asyncio.sleep(BACKUP_INTERVAL_DAYS * 24 * 60 * 60)
            
            if BACKUP_ENABLED:
                logging.info("Запуск автоматического бекапа...")
                result = await create_backup_now()
                logging.info(result)
                
                # Уведомляем администратора
                try:
                    await bot.send_message(ADMIN_USER_ID, f"🔄 Автоматический бекап:\n{result}")
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление о бекапе: {e}")
                    
        except Exception as e:
            logging.error(f"Ошибка в periodic_backup: {e}")
            await asyncio.sleep(3600)  # В случае ошибки ждем 1 час


async def on_startup(dp):
    """Действия при запуске бота"""
    logging.info("🤖 Бот запущен!")
    
    # Регистрируем команды в меню Telegram
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="🚀 Главное меню"),
        BotCommand(command="menu", description="🏠 Вернуться в меню"),
        BotCommand(command="admin", description="⚙️ Настройки администратора"),
    ]
    await bot.set_my_commands(commands)
    logging.info("✅ Команды зарегистрированы в меню Telegram")
    
    # Создаем начальный бекап при старте
    if BACKUP_ENABLED:
        logging.info("Создание начального бекапа...")
        result = await create_backup_now()
        logging.info(result)
    
    # Запускаем фоновую задачу для периодических бекапов
    if BACKUP_ENABLED:
        asyncio.create_task(periodic_backup())
        logging.info(f"Автоматические бекапы включены (каждые {BACKUP_INTERVAL_DAYS} дней)")
    
    # Регистрируем обработчики админ-панели
    register_admin_handlers(dp)
    logging.info("✅ Админ-панель зарегистрирована")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
