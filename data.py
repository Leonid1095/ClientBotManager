# data.py
# Работа с хранилищем заказов (Google Sheets опционально, иначе in-memory)

import os
import logging
from datetime import datetime

# In-memory хранилище если Google Sheets недоступен
TICKETS_DB = {}  # {user_id: {order_id: {...}, ...}}
REFERRALS_DB = {}  # {user_id: [referred_user_ids]}
BONUSES_DB = {}  # {user_id: bonus_amount}

try:
    from oauth2client.service_account import ServiceAccountCredentials
    import gspread
    
    CREDS_FILE = "google-credentials.json"
    SCOPE = ["https://spreadsheets.google.com/auth/spreadsheets"]
    USE_GSHEET = os.path.exists(CREDS_FILE)
    
    if USE_GSHEET:
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
            client = gspread.authorize(creds)
            USE_GSHEET = True
        except:
            USE_GSHEET = False
except:
    USE_GSHEET = False

def get_gsheet():
    """Получить Google Sheet (если доступен)"""
    if not USE_GSHEET:
        return None
    try:
        sheet = client.open("BotOrders").sheet1
        return sheet
    except Exception as e:
        logging.error(f"Ошибка подключения к Google Sheets: {e}")
        return None

def save_ticket(user_id, order_id, data):
    """Сохранить заказ"""
    ticket = {
        "order_id": order_id,
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "status": "новый",
        "data": data
    }
    
    # Сохранить в памяти
    if user_id not in TICKETS_DB:
        TICKETS_DB[user_id] = {}
    TICKETS_DB[user_id][order_id] = ticket
    
    # Попытаться сохранить в Google Sheets
    if USE_GSHEET:
        try:
            sheet = get_gsheet()
            if sheet:
                sheet.append_row([
                    order_id,
                    user_id,
                    data.get('fio', ''),
                    data.get('contact', ''),
                    "новый",
                    datetime.now().isoformat()
                ])
        except Exception as e:
            logging.warning(f"Не удалось сохранить в Google Sheets: {e}")

def get_ticket_status(user_id, order_id=None):
    """Получить статус заказов пользователя"""
    # Ищем в памяти
    if user_id in TICKETS_DB:
        if order_id:
            ticket = TICKETS_DB[user_id].get(order_id, {})
            if ticket:
                return f"Статус: {ticket.get('status', 'неизвестно')}\nВремя: {ticket.get('timestamp', '')}"
        # Вернуть все заказы пользователя
        tickets = TICKETS_DB[user_id]
        if tickets:
            result = "Ваши заказы:\n"
            for tid, tdata in tickets.items():
                result += f"• {tid}: {tdata.get('status', 'неизвестно')}\n"
            return result
    
    return "У вас нет заказов"

def get_all_tickets():
    """Получить все заказы"""
    return TICKETS_DB
