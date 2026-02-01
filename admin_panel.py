"""
Админ-панель для управления контентом бота
Позволяет редактировать Портфолио, FAQ, Контакты и "О себе" без доступа к коду
"""

from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import logging

from config import ADMIN_USER_ID
from content_manager import content_manager

logger = logging.getLogger(__name__)


# ==================== FSM STATES ====================

class AdminPortfolio(StatesGroup):
    """Состояния для редактирования портфолио"""
    menu = State()
    select_case = State()
    edit_title = State()
    edit_desc = State()
    edit_details = State()
    add_title = State()
    add_desc = State()
    add_details = State()
    confirm_delete = State()


class AdminFAQ(StatesGroup):
    """Состояния для редактирования FAQ"""
    menu = State()
    select_faq = State()
    edit_question = State()
    edit_answer = State()
    add_question = State()
    add_answer = State()
    confirm_delete = State()


class AdminContacts(StatesGroup):
    """Состояния для редактирования контактов"""
    menu = State()
    edit_telegram = State()
    edit_email = State()
    edit_phone = State()
    edit_whatsapp = State()


class AdminAbout(StatesGroup):
    """Состояния для редактирования 'О себе'"""
    menu = State()
    edit_text = State()


# ==================== ГЛАВНОЕ МЕНЮ АДМИН-ПАНЕЛИ ====================

async def admin_menu(message: types.Message):
    """Главное меню админ-панели"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.reply("❌ Доступ запрещён")
        return
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Портфолио", callback_data="admin_portfolio_menu"),
        InlineKeyboardButton("❓ FAQ", callback_data="admin_faq_menu"),
        InlineKeyboardButton("📞 Контакты", callback_data="admin_contacts_menu"),
        InlineKeyboardButton("👤 О себе", callback_data="admin_about_menu"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
    )
    
    text = """⚙️ <b>АДМИН-ПАНЕЛЬ</b>

Выбери раздел для редактирования:"""
    
    await message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== ПОРТФОЛИО ====================

async def portfolio_menu(call: types.CallbackQuery):
    """Меню портфолио"""
    portfolio = content_manager.get_portfolio()
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for case in portfolio:
        keyboard.add(InlineKeyboardButton(
            f"✏️ {case['title'][:30]}...",
            callback_data=f"edit_case_{case['id']}"
        ))
    
    keyboard.add(
        InlineKeyboardButton("➕ Добавить кейс", callback_data="add_case_title"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    
    text = f"""📦 <b>ПОРТФОЛИО</b>

Всего кейсов: {len(portfolio)}

Выбери кейс для редактирования:"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_case_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактирование кейса"""
    case_id = call.data.replace("edit_case_", "")
    
    portfolio = content_manager.get_portfolio()
    case = next((c for c in portfolio if c["id"] == case_id), None)
    
    if not case:
        await call.answer("❌ Кейс не найден")
        return
    
    await state.update_data(current_case_id=case_id)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📝 Название", callback_data="edit_case_title"),
        InlineKeyboardButton("📄 Короткое описание", callback_data="edit_case_desc"),
        InlineKeyboardButton("📋 Полное описание", callback_data="edit_case_details"),
        InlineKeyboardButton("🗑️ Удалить кейс", callback_data="delete_case_confirm"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_portfolio_menu")
    )
    
    text = f"""✏️ <b>Редактирование кейса</b>

<b>Название:</b> {case['title']}
<b>Краткое описание:</b> {case['desc']}

Выбери что редактировать:"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_case_title_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать название кейса"""
    await state.set_state(AdminPortfolio.edit_title)
    text = "✏️ Отправь новое название для кейса:"
    await call.message.edit_text(text, reply_markup=None)


async def process_edit_case_title(message: types.Message, state: FSMContext):
    """Обработка нового названия кейса"""
    data = await state.get_data()
    case_id = data.get("current_case_id")
    
    success = content_manager.update_portfolio_case(case_id, title=message.text)
    
    if success:
        await message.reply("✅ Название обновлено!")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data=f"edit_case_{case_id}"))
        await message.answer("Продолжить редактирование?", reply_markup=keyboard)
    else:
        await message.reply("❌ Ошибка при сохранении")
    
    await state.reset_state()


async def add_case_title_callback(call: types.CallbackQuery, state: FSMContext):
    """Добавить новый кейс - вводим название"""
    await state.set_state(AdminPortfolio.add_title)
    text = "➕ Отправь название нового кейса:"
    await call.message.edit_text(text, reply_markup=None)


async def process_add_case_title(message: types.Message, state: FSMContext):
    """Сохраняем название и переходим к описанию"""
    await state.update_data(new_case_title=message.text)
    await state.set_state(AdminPortfolio.add_desc)
    await message.reply("📄 Теперь отправь краткое описание (1-2 строки):")


async def process_add_case_desc(message: types.Message, state: FSMContext):
    """Сохраняем описание и переходим к деталям"""
    await state.update_data(new_case_desc=message.text)
    await state.set_state(AdminPortfolio.add_details)
    await message.reply("📋 Отправь полное описание кейса (может быть развёрнутым):")


async def process_add_case_details(message: types.Message, state: FSMContext):
    """Сохраняем деньги и добавляем кейс"""
    data = await state.get_data()
    
    success = content_manager.add_portfolio_case(
        title=data["new_case_title"],
        desc=data["new_case_desc"],
        details=message.text
    )
    
    if success:
        await message.reply("✅ Кейс добавлен в портфолио!")
    else:
        await message.reply("❌ Ошибка при добавлении")
    
    await state.reset_state()


async def delete_case_confirm_callback(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления кейса"""
    data = await state.get_data()
    case_id = data.get("current_case_id")
    
    portfolio = content_manager.get_portfolio()
    case = next((c for c in portfolio if c["id"] == case_id), None)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_case_{case_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"edit_case_{case_id}")
    )
    
    text = f"⚠️ <b>Удалить кейс?</b>\n\n{case['title']}"
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_delete_case_callback(call: types.CallbackQuery):
    """Подтверждение удаления кейса"""
    case_id = call.data.replace("confirm_delete_case_", "")
    
    success = content_manager.delete_portfolio_case(case_id)
    
    if success:
        await call.answer("✅ Кейс удалён")
        # Возвращаемся в меню портфолио
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📦 Портфолио", callback_data="admin_portfolio_menu"))
        await call.message.edit_text("✅ Кейс успешно удалён", reply_markup=keyboard)
    else:
        await call.answer("❌ Ошибка при удалении")


# ==================== FAQ ====================

async def faq_menu(call: types.CallbackQuery):
    """Меню FAQ"""
    faq = content_manager.get_faq()
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for item in faq:
        q_preview = item['q'][:35] + "..." if len(item['q']) > 35 else item['q']
        keyboard.add(InlineKeyboardButton(
            f"✏️ {q_preview}",
            callback_data=f"edit_faq_{item['id']}"
        ))
    
    keyboard.add(
        InlineKeyboardButton("➕ Добавить вопрос", callback_data="add_faq_question"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    
    text = f"""❓ <b>FAQ</b>

Всего вопросов: {len(faq)}

Выбери вопрос для редактирования:"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_faq_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактирование FAQ"""
    faq_id = call.data.replace("edit_faq_", "")
    
    faq = content_manager.get_faq()
    item = next((f for f in faq if f["id"] == faq_id), None)
    
    if not item:
        await call.answer("❌ Вопрос не найден")
        return
    
    await state.update_data(current_faq_id=faq_id)
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("❓ Редактировать вопрос", callback_data="edit_faq_question"),
        InlineKeyboardButton("💬 Редактировать ответ", callback_data="edit_faq_answer"),
        InlineKeyboardButton("🗑️ Удалить вопрос", callback_data="delete_faq_confirm"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_faq_menu")
    )
    
    text = f"""✏️ <b>Редактирование FAQ</b>

<b>❓ Вопрос:</b>
{item['q']}

<b>💬 Ответ:</b>
{item['a'][:100]}...

Что редактировать?"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_faq_question_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать вопрос FAQ"""
    await state.set_state(AdminFAQ.edit_question)
    await call.message.edit_text("❓ Отправь новый вопрос:", reply_markup=None)


async def process_edit_faq_question(message: types.Message, state: FSMContext):
    """Обработка нового вопроса"""
    data = await state.get_data()
    faq_id = data.get("current_faq_id")
    
    success = content_manager.update_faq(faq_id, question=message.text)
    
    if success:
        await message.reply("✅ Вопрос обновлён!")
    else:
        await message.reply("❌ Ошибка при сохранении")
    
    await state.reset_state()


async def edit_faq_answer_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать ответ FAQ"""
    await state.set_state(AdminFAQ.edit_answer)
    await call.message.edit_text("💬 Отправь новый ответ:", reply_markup=None)


async def process_edit_faq_answer(message: types.Message, state: FSMContext):
    """Обработка нового ответа"""
    data = await state.get_data()
    faq_id = data.get("current_faq_id")
    
    success = content_manager.update_faq(faq_id, answer=message.text)
    
    if success:
        await message.reply("✅ Ответ обновлён!")
    else:
        await message.reply("❌ Ошибка при сохранении")
    
    await state.reset_state()


async def add_faq_question_callback(call: types.CallbackQuery, state: FSMContext):
    """Добавить новый вопрос в FAQ"""
    await state.set_state(AdminFAQ.add_question)
    await call.message.edit_text("➕ Отправь новый вопрос:", reply_markup=None)


async def process_add_faq_question(message: types.Message, state: FSMContext):
    """Сохраняем вопрос и переходим к ответу"""
    await state.update_data(new_faq_question=message.text)
    await state.set_state(AdminFAQ.add_answer)
    await message.reply("💬 Теперь отправь ответ на вопрос:")


async def process_add_faq_answer(message: types.Message, state: FSMContext):
    """Сохраняем ответ и добавляем FAQ"""
    data = await state.get_data()
    
    success = content_manager.add_faq(
        question=data["new_faq_question"],
        answer=message.text
    )
    
    if success:
        await message.reply("✅ Вопрос добавлен в FAQ!")
    else:
        await message.reply("❌ Ошибка при добавлении")
    
    await state.reset_state()


async def delete_faq_confirm_callback(call: types.CallbackQuery, state: FSMContext):
    """Подтверждение удаления FAQ"""
    data = await state.get_data()
    faq_id = data.get("current_faq_id")
    
    faq = content_manager.get_faq()
    item = next((f for f in faq if f["id"] == faq_id), None)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_faq_{faq_id}"),
        InlineKeyboardButton("❌ Отмена", callback_data=f"edit_faq_{faq_id}")
    )
    
    text = f"⚠️ <b>Удалить вопрос?</b>\n\n{item['q']}"
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def confirm_delete_faq_callback(call: types.CallbackQuery):
    """Подтверждение удаления FAQ"""
    faq_id = call.data.replace("confirm_delete_faq_", "")
    
    success = content_manager.delete_faq(faq_id)
    
    if success:
        await call.answer("✅ Вопрос удалён")
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("❓ FAQ", callback_data="admin_faq_menu"))
        await call.message.edit_text("✅ Вопрос успешно удалён", reply_markup=keyboard)


# ==================== КОНТАКТЫ ====================

async def contacts_menu(call: types.CallbackQuery):
    """Меню контактов"""
    contacts = content_manager.get_contacts()
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("✏️ Telegram", callback_data="edit_contact_telegram"),
        InlineKeyboardButton("✏️ Email", callback_data="edit_contact_email"),
        InlineKeyboardButton("✏️ Телефон", callback_data="edit_contact_phone"),
        InlineKeyboardButton("✏️ WhatsApp", callback_data="edit_contact_whatsapp"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    
    text = f"""📞 <b>КОНТАКТЫ</b>

📱 <b>Telegram:</b> {contacts.get('telegram', 'не указан')}
📧 <b>Email:</b> {contacts.get('email', 'не указан')}
☎️ <b>Телефон:</b> {contacts.get('phone', 'не указан')}
💬 <b>WhatsApp:</b> {contacts.get('whatsapp', 'не указан')}

Выбери контакт для редактирования:"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_contact_telegram_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать Telegram"""
    await state.set_state(AdminContacts.edit_telegram)
    await call.message.edit_text("📱 Отправь новый Telegram ник (например @username):", reply_markup=None)


async def process_edit_contact_telegram(message: types.Message, state: FSMContext):
    """Сохраняем Telegram"""
    content_manager.update_contacts(telegram=message.text)
    await message.reply("✅ Telegram обновлён!")
    await state.reset_state()


async def edit_contact_email_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать Email"""
    await state.set_state(AdminContacts.edit_email)
    await call.message.edit_text("📧 Отправь новый Email:", reply_markup=None)


async def process_edit_contact_email(message: types.Message, state: FSMContext):
    """Сохраняем Email"""
    content_manager.update_contacts(email=message.text)
    await message.reply("✅ Email обновлён!")
    await state.reset_state()


async def edit_contact_phone_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать телефон"""
    await state.set_state(AdminContacts.edit_phone)
    await call.message.edit_text("☎️ Отправь новый номер телефона:", reply_markup=None)


async def process_edit_contact_phone(message: types.Message, state: FSMContext):
    """Сохраняем телефон"""
    content_manager.update_contacts(phone=message.text)
    await message.reply("✅ Телефон обновлён!")
    await state.reset_state()


async def edit_contact_whatsapp_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать WhatsApp"""
    await state.set_state(AdminContacts.edit_whatsapp)
    await call.message.edit_text("💬 Отправь WhatsApp номер:", reply_markup=None)


async def process_edit_contact_whatsapp(message: types.Message, state: FSMContext):
    """Сохраняем WhatsApp"""
    content_manager.update_contacts(whatsapp=message.text)
    await message.reply("✅ WhatsApp обновлён!")
    await state.reset_state()


# ==================== О СЕБЕ ====================

async def about_menu(call: types.CallbackQuery):
    """Меню 'О себе'"""
    about = content_manager.get_about()
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✏️ Редактировать текст", callback_data="edit_about_text"),
        InlineKeyboardButton("🔙 Назад", callback_data="admin_back")
    )
    
    preview = about[:200] + "..." if len(about) > 200 else about
    
    text = f"""👤 <b>О СЕБЕ</b>

<b>Текущий текст:</b>
{preview}

Что делать?"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def edit_about_text_callback(call: types.CallbackQuery, state: FSMContext):
    """Редактировать текст 'О себе'"""
    await state.set_state(AdminAbout.edit_text)
    current = content_manager.get_about()
    await call.message.edit_text(f"👤 Отправь новый текст для раздела 'О себе':\n\n<i>(Можешь использовать HTML теги для форматирования)</i>\n\n<b>Текущий текст:</b>\n{current[:300]}...", 
                                reply_markup=None, 
                                parse_mode="HTML")


async def process_edit_about_text(message: types.Message, state: FSMContext):
    """Сохраняем текст 'О себе'"""
    success = content_manager.update_about(message.text)
    
    if success:
        await message.reply("✅ Текст обновлён!")
    else:
        await message.reply("❌ Ошибка при сохранении")
    
    await state.reset_state()


# ==================== СТАТИСТИКА ====================

async def admin_stats(call: types.CallbackQuery):
    """Показать статистику"""
    stats = content_manager.get_stats()
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_menu_back"))
    
    text = f"""📊 <b>СТАТИСТИКА КОНТЕНТА</b>

📦 Кейсов в портфолио: {stats['portfolio_count']}
❓ Вопросов в FAQ: {stats['faq_count']}
📞 Контакты обновлены: {stats['contacts_updated']}
👤 О себе обновлено: {stats['about_updated']}

Нужна более детальная информация? Обращайся с вопросами!"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


# ==================== UTILITY CALLBACKS ====================

async def admin_back_callback(call: types.CallbackQuery):
    """Вернуться в главное меню"""
    await admin_menu(call.message)


async def admin_menu_back_callback(call: types.CallbackQuery):
    """Вернуться в главное меню админ-панели"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📦 Портфолио", callback_data="admin_portfolio_menu"),
        InlineKeyboardButton("❓ FAQ", callback_data="admin_faq_menu"),
        InlineKeyboardButton("📞 Контакты", callback_data="admin_contacts_menu"),
        InlineKeyboardButton("👤 О себе", callback_data="admin_about_menu"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")
    )
    
    text = """⚙️ <b>АДМИН-ПАНЕЛЬ</b>

Выбери раздел для редактирования:"""
    
    await call.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")


async def admin_close_callback(call: types.CallbackQuery):
    """Закрыть админ-панель"""
    await call.message.delete()


# ==================== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ====================

def register_admin_handlers(dp: Dispatcher):
    """Регистрация всех обработчиков админ-панели"""
    
    # Главное меню
    dp.register_callback_query_handler(admin_menu, text="admin_menu", state="*")
    
    # Портфолио
    dp.register_callback_query_handler(portfolio_menu, text="admin_portfolio_menu", state="*")
    dp.register_callback_query_handler(edit_case_callback, lambda c: c.data.startswith("edit_case_"), state="*")
    dp.register_callback_query_handler(edit_case_title_callback, text="edit_case_title", state="*")
    dp.register_message_handler(process_edit_case_title, state=AdminPortfolio.edit_title)
    dp.register_callback_query_handler(add_case_title_callback, text="add_case_title", state="*")
    dp.register_message_handler(process_add_case_title, state=AdminPortfolio.add_title)
    dp.register_message_handler(process_add_case_desc, state=AdminPortfolio.add_desc)
    dp.register_message_handler(process_add_case_details, state=AdminPortfolio.add_details)
    dp.register_callback_query_handler(delete_case_confirm_callback, text="delete_case_confirm", state="*")
    dp.register_callback_query_handler(confirm_delete_case_callback, lambda c: c.data.startswith("confirm_delete_case_"), state="*")
    
    # FAQ
    dp.register_callback_query_handler(faq_menu, text="admin_faq_menu", state="*")
    dp.register_callback_query_handler(edit_faq_callback, lambda c: c.data.startswith("edit_faq_"), state="*")
    dp.register_callback_query_handler(edit_faq_question_callback, text="edit_faq_question", state="*")
    dp.register_message_handler(process_edit_faq_question, state=AdminFAQ.edit_question)
    dp.register_callback_query_handler(edit_faq_answer_callback, text="edit_faq_answer", state="*")
    dp.register_message_handler(process_edit_faq_answer, state=AdminFAQ.edit_answer)
    dp.register_callback_query_handler(add_faq_question_callback, text="add_faq_question", state="*")
    dp.register_message_handler(process_add_faq_question, state=AdminFAQ.add_question)
    dp.register_message_handler(process_add_faq_answer, state=AdminFAQ.add_answer)
    dp.register_callback_query_handler(delete_faq_confirm_callback, text="delete_faq_confirm", state="*")
    dp.register_callback_query_handler(confirm_delete_faq_callback, lambda c: c.data.startswith("confirm_delete_faq_"), state="*")
    
    # Контакты
    dp.register_callback_query_handler(contacts_menu, text="admin_contacts_menu", state="*")
    dp.register_callback_query_handler(edit_contact_telegram_callback, text="edit_contact_telegram", state="*")
    dp.register_message_handler(process_edit_contact_telegram, state=AdminContacts.edit_telegram)
    dp.register_callback_query_handler(edit_contact_email_callback, text="edit_contact_email", state="*")
    dp.register_message_handler(process_edit_contact_email, state=AdminContacts.edit_email)
    dp.register_callback_query_handler(edit_contact_phone_callback, text="edit_contact_phone", state="*")
    dp.register_message_handler(process_edit_contact_phone, state=AdminContacts.edit_phone)
    dp.register_callback_query_handler(edit_contact_whatsapp_callback, text="edit_contact_whatsapp", state="*")
    dp.register_message_handler(process_edit_contact_whatsapp, state=AdminContacts.edit_whatsapp)
    
    # О себе
    dp.register_callback_query_handler(about_menu, text="admin_about_menu", state="*")
    dp.register_callback_query_handler(edit_about_text_callback, text="edit_about_text", state="*")
    dp.register_message_handler(process_edit_about_text, state=AdminAbout.edit_text)
    
    # Статистика
    dp.register_callback_query_handler(admin_stats, text="admin_stats", state="*")
    
    # Утилиты
    dp.register_callback_query_handler(admin_back_callback, text="admin_back", state="*")
    dp.register_callback_query_handler(admin_menu_back_callback, text="admin_menu_back", state="*")
    dp.register_callback_query_handler(admin_close_callback, text="admin_close", state="*")
