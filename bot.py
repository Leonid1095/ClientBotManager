# bot.py
# Основной файл Telegram-бота для заказов

import logging
import uuid
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import *
from menu import main_menu
from states import OrderForm
from faq import FAQ_LIST
from portfolio import PORTFOLIO
from reviews import REVIEWS
from calc import calculate_price
from data import save_ticket, get_ticket_status

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# In-memory база для рефералов и бонусов (можно заменить на Google Sheets)
REFERRALS = {}
BONUSES = {}

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
                REFERRALS.setdefault(ref_id, []).append(user_id)
                BONUSES[ref_id] = BONUSES.get(ref_id, 0) + 100  # 100 руб. бонус
        except ValueError:
            pass
    
    text = (
        "👋 Привет! Я — ваш личный бот для заказов.\n"
        "Выберите действие в меню."
    )
    await message.answer(text, reply_markup=main_menu)


# ==============================================
# ОБРАБОТЧИКИ МЕНЮ
# ==============================================

@dp.message_handler(lambda m: m.text == "Портфолио")
async def handle_portfolio(message: types.Message):
    """Показ портфолио с кнопками для просмотра кейсов"""
    for case in PORTFOLIO:
        kb = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Посмотреть кейс", callback_data=f"case_{case['id']}")
        )
        text = f"<b>{case['title']}</b>\n{case['desc']}"
        await message.answer(text, parse_mode="HTML", reply_markup=kb)

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


@dp.message_handler(lambda m: m.text == "FAQ")
async def handle_faq(message: types.Message):
    """Показ часто задаваемых вопросов"""
    text = "<b>FAQ — Часто задаваемые вопросы:</b>\n"
    for item in FAQ_LIST:
        text += f"\n<b>Q:</b> {item['q']}\n<b>A:</b> {item['a']}\n"
    await message.answer(text, parse_mode="HTML")


@dp.message_handler(lambda m: m.text == "Чат поддержки")
async def handle_support(message: types.Message):
    """Чат с поддержкой"""
    await message.answer("Напишите ваш вопрос, и я отвечу лично.")


@dp.message_handler(lambda m: m.text == "О компании")
async def handle_about(message: types.Message):
    """Информация о компании"""
    await message.answer(
        "Я — разработчик Telegram-ботов с опытом 3+ года. "
        "Более 50 реализованных проектов для бизнеса и частных лиц.\n\n"
        "Портфолио и отзывы доступны в соответствующих разделах."
    )


@dp.message_handler(lambda m: m.text == "Связаться с разработчиком")
async def handle_contact_dev(message: types.Message):
    """Контакты разработчика"""
    await message.answer("Для связи: @ваш_ник или email@example.com")


@dp.message_handler(lambda m: m.text == "Бонусы и рефералы")
async def handle_bonuses(message: types.Message):
    """Показ реферальной ссылки и бонусов"""
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.get_me()).username}?start=ref{user_id}"
    invited = REFERRALS.get(user_id, [])
    bonus = BONUSES.get(user_id, 0)
    text = (
        f"Ваша реферальная ссылка:\n{ref_link}\n"
        f"Приглашено пользователей: {len(invited)}\n"
        f"Ваш бонус: {bonus} руб.\n"
        "\nПригласите друга — получите бонус за каждый оплаченный заказ!"
    )
    await message.answer(text)


# ==============================================
# ОТЗЫВЫ
# ==============================================

@dp.message_handler(lambda m: m.text == "Отзывы")
async def handle_reviews(message: types.Message):
    """Просмотр отзывов"""
    text = "Отзывы клиентов:\n"
    for r in REVIEWS:
        text += f"\n<b>{r['author']}</b>: {r['text']}\n"
    text += "\nЕсли хотите оставить отзыв, напишите 'Оставить отзыв'."
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text.lower() == 'оставить отзыв')
async def start_review(message: types.Message):
    """Начало добавления отзыва"""
    await message.answer("Напишите ваш отзыв:")
    await ReviewForm.text.set()

@dp.message_handler(state=ReviewForm.text)
async def save_review(message: types.Message, state: FSMContext):
    """Сохранение отзыва"""
    REVIEWS.append({"author": message.from_user.first_name, "text": message.text})
    await message.answer("Спасибо за ваш отзыв!")
    await state.finish()


# ==============================================
# СТАТУС ЗАКАЗА
# ==============================================

@dp.message_handler(lambda m: m.text == "Статус заказа")
async def handle_status(message: types.Message):
    """Запрос номера заказа для проверки статуса"""
    await message.answer("Введите номер вашего заказа для проверки статуса:")
    await StatusForm.order_id.set()

@dp.message_handler(state=StatusForm.order_id)
async def process_status(message: types.Message, state: FSMContext):
    """Проверка статуса заказа"""
    order_id = message.text.strip()
    status = get_ticket_status(order_id)
    await message.answer(f"Статус заказа {order_id}: {status}")
    await state.finish()


# ==============================================
# КАЛЬКУЛЯТОР СТОИМОСТИ
# ==============================================

@dp.message_handler(lambda m: m.text == "Калькулятор стоимости")
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

@dp.message_handler(lambda m: m.text == "Заказать бота")
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
        f"Спасибо! Ваша заявка принята. Ваш номер заказа: {order_id}\n"
        f"Вы можете проверить статус через меню 'Статус заказа'."
    )
    await bot.send_message(ADMIN_USER_ID, ticket)
    if data.get('file'):
        await bot.send_document(ADMIN_USER_ID, data['file'])
    
    # Сохраняем тикет в Google Sheets
    try:
        save_ticket({
            'order_id': order_id,
            'fio': data['fio'],
            'contact': data['contact'],
            'idea': data['idea'],
            'type_bot': data['type_bot'],
            'budget': data['budget'],
            'deadline': data['deadline'],
            'options': data['options'],
            'settings': data['settings'],
            'file': data.get('file', ''),
            'hosting': data['hosting'],
            'status': 'новый',
            'user_id': user_id,
        })
    except Exception as e:
        logging.error(f"Ошибка при сохранении тикета в Google Sheets: {e}")
    
    await state.finish()

@dp.message_handler(lambda m: m.text.lower() == 'отмена', state=OrderForm.confirm)
async def process_cancel(message: types.Message, state: FSMContext):
    """Отмена заказа"""
    await message.answer("Заявка отменена.")
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

if __name__ == '__main__':
    print("🤖 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
