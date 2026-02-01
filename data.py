# data.py
# Модуль для работы с хранением данных (тикеты, отзывы, портфолио и др.)

# Здесь будет реализовано:
# - Сохранение и загрузка тикетов
# - Работа с портфолио
# - Хранение отзывов
# - Интеграция с внешними сервисами (Google Sheets, Trello и др.)


import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка доступа к Google Sheets
SCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
CREDS_FILE = 'google-credentials.json'  # Путь к вашему credentials файлу
SHEET_NAME = 'BotOrders'  # Название таблицы

def get_gsheet():
	creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
	client = gspread.authorize(creds)
	sheet = client.open(SHEET_NAME).sheet1
	return sheet

def save_ticket(ticket_data: dict):
	sheet = get_gsheet()
	values = [
		ticket_data.get('order_id', ''),
		ticket_data.get('fio', ''),
		ticket_data.get('contact', ''),
		ticket_data.get('idea', ''),
		ticket_data.get('type_bot', ''),
		ticket_data.get('budget', ''),
		ticket_data.get('deadline', ''),
		ticket_data.get('options', ''),
		ticket_data.get('settings', ''),
		ticket_data.get('file', ''),
		ticket_data.get('hosting', ''),
		ticket_data.get('status', 'новый'),
		ticket_data.get('user_id', ''),
	]
	sheet.append_row(values)

def get_ticket_status(order_id: str):
	sheet = get_gsheet()
	records = sheet.get_all_records()
	for row in records:
		if str(row.get('order_id')) == str(order_id):
			return row.get('status', 'не найдено')
	return 'не найдено'
