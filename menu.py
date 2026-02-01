# menu.py
# Модуль для создания и управления главным меню и разделами

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Главное меню
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(
    KeyboardButton("Заказать бота"),
    KeyboardButton("Портфолио")
)
main_menu.add(
    KeyboardButton("FAQ"),
    KeyboardButton("Чат поддержки"),
    KeyboardButton("Калькулятор стоимости")
)
main_menu.add(
    KeyboardButton("Статус заказа"),
	KeyboardButton("О себе"),
