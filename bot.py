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
from states import OrderForm
from faq import FAQ_LIST
from portfolio import PORTFOLIO
from reviews import REVIEWS
from calc import calculate_price
from data import save_ticket, get_ticket_status, TICKETS_DB, REFERRALS_DB, BONUSES_DB
from backup import BackupManager

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
    for case in PORTFOLIO:
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
    case = next((c for c in PORTFOLIO if c['id'] == case_id), None)
    if case:
        await callback_query.message.answer(
            f"<b>{case['title']}</b>\n{case['details']}", 
            parse_mode="HTML"
        )
    await callback_query.answer()


@dp.message_handler(lambda m: m.text == FAQ_TEXT)
async def handle_faq(message: types.Message):
    """Показ часто задаваемых вопросов"""
    text = "<b>FAQ — Часто задаваемые вопросы:</b>\n"
    for item in FAQ_LIST:
        text += f"\n<b>Q:</b> {item['q']}\n<b>A:</b> {item['a']}\n"
    await message.answer(text, parse_mode="HTML", reply_markup=get_back_keyboard())


@dp.message_handler(lambda m: m.text == SUPPORT_TEXT)
async def handle_support(message: types.Message):
    """Чат с поддержкой"""
    await message.answer(
        "💬 Напишите ваш вопрос — я отвечу лично.",
        reply_markup=get_back_keyboard()
    )


@dp.message_handler(lambda m: m.text == ABOUT_TEXT)
async def handle_about(message: types.Message):
    """Информация о компании"""
    await message.answer(
        "👤 <b>О себе</b>\n"
        "Я — разработчик Telegram-ботов с опытом 3+ года. "
        "Более 50 реализованных проектов для бизнеса и частных лиц.\n\n"
        "Портфолио и отзывы доступны в соответствующих разделах.",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


@dp.message_handler(lambda m: m.text == CONTACT_TEXT)
async def handle_contact_dev(message: types.Message):
    """Контакты разработчика"""
    await message.answer(
        "📞 <b>Контакты</b>\n"
        "Telegram: @ваш_ник\n"
        "Email: email@example.com",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )


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
    text = "Отзывы клиентов:\n"
    for r in REVIEWS:
        text += f"\n<b>{r['author']}</b>: {r['text']}\n"
    text += "\nХотите оставить отзыв? Нажмите кнопку ниже."
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
    """Сохранение отзыва"""
    REVIEWS.append({"author": message.from_user.first_name, "text": message.text})
    await message.answer("Спасибо за ваш отзыв!", reply_markup=get_back_keyboard())
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
    await message.answer("Для заказа бота заполните, пожалуйста, небольшую анкету.\n\nВаши ФИО:")
    await OrderForm.fio.set()

@dp.message_handler(state=OrderForm.fio)
async def process_fio(message: types.Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await message.answer("Ваши контактные данные (телефон, email, Telegram):")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.contact)
async def process_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await message.answer("Опишите вашу идею для бота:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.idea)
async def process_idea(message: types.Message, state: FSMContext):
    await state.update_data(idea=message.text)
    await message.answer("Выберите тип бота (чат-бот, магазин, интеграция и т.д.):")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.type_bot)
async def process_type_bot(message: types.Message, state: FSMContext):
    await state.update_data(type_bot=message.text)
    await message.answer("Укажите желаемый бюджет:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.budget)
async def process_budget(message: types.Message, state: FSMContext):
    await state.update_data(budget=message.text)
    await message.answer("Укажите желаемые сроки:")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.deadline)
async def process_deadline(message: types.Message, state: FSMContext):
    await state.update_data(deadline=message.text)
    await message.answer("Выберите тариф или опции (опишите, если есть):")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.options)
async def process_options(message: types.Message, state: FSMContext):
    await state.update_data(options=message.text)
    await message.answer("Есть ли особые настройки или пожелания?")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.settings)
async def process_settings(message: types.Message, state: FSMContext):
    await state.update_data(settings=message.text)
    await message.answer("Прикрепите файл (если есть) или напишите 'нет':")
    await OrderForm.next()

@dp.message_handler(content_types=types.ContentType.DOCUMENT, state=OrderForm.file)
async def process_file(message: types.Message, state: FSMContext):
    file_id = message.document.file_id
    await state.update_data(file=file_id)
    await message.answer("Где будет размещён бот?\n1. Ваш сервер\n2. Мой сервер (аренда)")
    await OrderForm.next()

@dp.message_handler(lambda m: m.text.lower() == 'нет', state=OrderForm.file)
async def process_no_file(message: types.Message, state: FSMContext):
    await state.update_data(file=None)
    await message.answer("Где будет размещён бот?\n1. Ваш сервер\n2. Мой сервер (аренда)")
    await OrderForm.next()

@dp.message_handler(state=OrderForm.hosting)
async def process_hosting(message: types.Message, state: FSMContext):
    """Обработка хостинга и предложение использовать бонусы"""
    await state.update_data(hosting=message.text)
    user_id = message.from_user.id
    bonus = BONUSES.get(user_id, 0)
    
    if bonus > 0:
        await message.answer(f"У вас есть бонусы: {bonus} руб.\nИспользовать бонусы для скидки? (да/нет)")
        await OrderForm.next()
    else:
        await state.update_data(use_bonus=False, bonus_amount=0)
        data = await state.get_data()
        summary = _format_order_summary(data)
        await message.answer(summary + "\nЕсли всё верно, напишите 'Подтверждаю'. Для отмены — 'Отмена'.")
        await OrderForm.confirm.set()

@dp.message_handler(state=OrderForm.use_bonus)
async def process_use_bonus(message: types.Message, state: FSMContext):
    """Обработка решения об использовании бонусов"""
    user_id = message.from_user.id
    bonus = BONUSES.get(user_id, 0)
    
    if message.text.lower() == 'да':
        await state.update_data(use_bonus=True, bonus_amount=bonus)
        discount_text = f"\nПрименена скидка: {bonus} руб."
    else:
        await state.update_data(use_bonus=False, bonus_amount=0)
        discount_text = ""
    
    data = await state.get_data()
    summary = _format_order_summary(data) + discount_text
    await message.answer(summary + "\nЕсли всё верно, напишите 'Подтверждаю'. Для отмены — 'Отмена'.")
    await OrderForm.next()

@dp.message_handler(lambda m: m.text.lower() == 'подтверждаю', state=OrderForm.confirm)
async def process_confirm(message: types.Message, state: FSMContext):
    """Подтверждение и сохранение заказа"""
    data = await state.get_data()
    order_id = str(uuid.uuid4())[:8]
    user_id = message.from_user.id
    
    # Списываем бонусы если использовались
    bonus_text = ""
    if data.get('use_bonus', False):
        bonus_amount = data.get('bonus_amount', 0)
        BONUSES[user_id] = BONUSES.get(user_id, 0) - bonus_amount
        bonus_text = f"Использовано бонусов: {bonus_amount} руб.\n"
    
    # Формирование тикета
    ticket = (
        f"Новая заявка на бота:\n"
        f"ID заказа: {order_id}\n"
        f"User ID: {user_id}\n"
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
        + bonus_text
    )
    
    # Отправка клиенту и админу
    await message.answer(
        f"✅ Спасибо! Ваша заявка принята.\n"
        f"Номер заказа: {order_id}\n"
        f"Вы можете проверить статус через меню 'Статус заказа'."
    )
    
    try:
        await bot.send_message(ADMIN_USER_ID, ticket)
        if data.get('file'):
            await bot.send_document(ADMIN_USER_ID, data['file'])
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")
    
    # Сохраняем тикет (и в памяти и в Google Sheets)
    try:
        save_ticket(user_id, order_id, data)
    except Exception as e:
        logging.error(f"Ошибка при сохранении тикета: {e}")
    
    await state.finish()

@dp.message_handler(lambda m: m.text.lower() == 'отмена', state=OrderForm.confirm)
async def process_cancel(message: types.Message, state: FSMContext):
    """Отмена заказа"""
    await message.answer("❌ Заявка отменена.")
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
        BotCommand(command="backup", description="💾 Создать бекап (админ)"),
        BotCommand(command="backup_list", description="📂 Список бекапов (админ)"),
        BotCommand(command="backup_settings", description="⚙️ Настройки бекапов (админ)"),
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


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
