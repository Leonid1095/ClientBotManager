# menu.py
# Модуль для создания и управления главным меню и разделами

# Здесь будут реализованы:
# - Главное меню
# - Кнопки для: Заказать бота, Портфолио, FAQ, Чат, Калькулятор стоимости


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
	KeyboardButton("О компании"),
	KeyboardButton("Связаться с разработчиком"),
	KeyboardButton("Отзывы"),
	KeyboardButton("Бонусы и рефералы")
)
