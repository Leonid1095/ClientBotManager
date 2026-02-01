#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Умный установщик Telegram-бота для заказов
Установка и конфигурация в несколько кликов
"""

import os
import sys
import subprocess
import platform
import json
from pathlib import Path

class BotInstaller:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.config_file = self.project_dir / "config.py"
        self.venv_dir = self.project_dir / "venv"
        self.os_type = platform.system()
        
    def print_header(self):
        print("\n" + "="*60)
        print("🤖 УСТАНОВЩИК TELEGRAM-БОТА ДЛЯ ЗАКАЗОВ")
        print("="*60 + "\n")
    
    def check_python(self):
        print("✓ Проверка Python...")
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 8):
            print(f"✗ Требуется Python 3.8+, а у вас {version.major}.{version.minor}")
            sys.exit(1)
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} - OK\n")
    
    def create_venv(self):
        print("✓ Создание виртуального окружения...")
        if self.venv_dir.exists():
            print("  Виртуальное окружение уже существует\n")
            return True
        
        try:
            subprocess.check_call([sys.executable, "-m", "venv", str(self.venv_dir)])
            print(f"✓ Виртуальное окружение создано: {self.venv_dir}\n")
            return True
        except Exception as e:
            print(f"✗ Ошибка при создании venv: {e}\n")
            return False
    
    def get_pip_command(self):
        if self.os_type == "Windows":
            return str(self.venv_dir / "Scripts" / "pip.exe")
        else:
            return str(self.venv_dir / "bin" / "pip")
    
    def install_requirements(self):
        print("✓ Установка зависимостей...")
        pip_cmd = self.get_pip_command()
        requirements_file = self.project_dir / "requirements.txt"
        
        try:
            subprocess.check_call([pip_cmd, "install", "-r", str(requirements_file)])
            print("✓ Зависимости установлены\n")
            return True
        except Exception as e:
            print(f"✗ Ошибка при установке зависимостей: {e}\n")
            return False
    
    def configure_bot(self):
        print("✓ КОНФИГУРАЦИЯ БОТА\n")
        
        # Проверка существующей конфигурации
        if self.config_file.exists():
            response = input("Конфиг уже существует. Перезаписать? (y/n): ").strip().lower()
            if response != 'y':
                print("Конфигурация не изменена\n")
                return True
        
        print("Введите данные для вашего бота:\n")
        
        # Телеграм токен
        while True:
            token = input("1. Токен Telegram-бота (от @BotFather): ").strip()
            if token and len(token) > 30:
                break
            print("   ✗ Неверный формат токена. Попробуйте снова.")
        
        # Admin User ID
        while True:
            try:
                admin_id = int(input("2. Ваш Telegram ID (для уведомлений): ").strip())
                if admin_id > 0:
                    break
                print("   ✗ ID должен быть положительным числом.")
            except ValueError:
                print("   ✗ Введите число.")
        
        # Email для связи (опционально)
        email = input("3. Ваш email для связи (опционально): ").strip()
        
        # Telegram никнейм (опционально)
        username = input("4. Ваш Telegram никнейм (опционально, без @): ").strip()
        
        # Google Sheets (опционально)
        use_sheets = input("5. Использовать Google Sheets для тикетов? (y/n): ").strip().lower() == 'y'
        sheets_name = ""
        if use_sheets:
            sheets_name = input("   Название Google Sheet (по умолчанию: BotOrders): ").strip() or "BotOrders"
        
        # Создание конфига
        config_content = f'''# Конфигурация Telegram-бота

# Токен бота от @BotFather
TELEGRAM_TOKEN = "{token}"

# Ваш Telegram ID (получить можно у @userinfobot)
ADMIN_USER_ID = {admin_id}

# Контактные данные разработчика
DEVELOPER_EMAIL = "{email}" if "{email}" else "your_email@example.com"
DEVELOPER_USERNAME = "{username}" if "{username}" else "your_username"

# Google Sheets интеграция
USE_GOOGLE_SHEETS = {use_sheets}
GOOGLE_SHEETS_NAME = "{sheets_name}"
GOOGLE_CREDENTIALS_FILE = "google-credentials.json"

# Параметры бонусов
BONUS_PER_REFERRAL = 100  # Рубли за каждого приглашённого
BASE_BOT_PRICE = 5000  # Базовая цена бота

# Параметры хостинга
SHOP_BOT_PRICE_ADD = 5000
COMPLEX_BOT_PRICE_ADD = 7000
HOSTING_PRICE_ADD = 2000
'''
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print("\n✓ Конфигурация сохранена в config.py\n")
            return True
        except Exception as e:
            print(f"\n✗ Ошибка при сохранении конфига: {e}\n")
            return False
    
    def create_startup_script(self):
        print("✓ Создание скрипта запуска...\n")
        
        if self.os_type == "Windows":
            script_name = "run.bat"
            script_content = f'''@echo off
cd /d "%~dp0"
"{str(self.venv_dir / 'Scripts' / 'python.exe')}" bot.py
pause
'''
        else:
            script_name = "run.sh"
            script_content = f'''#!/bin/bash
cd "$(dirname "$0")"
"{str(self.venv_dir / 'bin' / 'python')}" bot.py
'''
        
        script_path = self.project_dir / script_name
        try:
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            if self.os_type != "Windows":
                os.chmod(script_path, 0o755)
            
            print(f"✓ Скрипт запуска создан: {script_name}\n")
            return True
        except Exception as e:
            print(f"✗ Ошибка при создании скрипта: {e}\n")
            return False
    
    def show_next_steps(self):
        print("="*60)
        print("✓ УСТАНОВКА ЗАВЕРШЕНА!\n")
        
        print("📝 СЛЕДУЮЩИЕ ШАГИ:\n")
        
        print("1. Если вы выбрали Google Sheets:")
        print("   - Скачайте credentials.json из Google Cloud Console")
        print("   - Поместите в папку проекта: google-credentials.json\n")
        
        print("2. Для запуска бота используйте команду:")
        if self.os_type == "Windows":
            print("   > run.bat")
            print("   или")
            print(f'   > "{str(self.venv_dir / "Scripts" / "python.exe")}" bot.py\n')
        else:
            print("   $ ./run.sh")
            print("   или")
            print(f'   $ "{str(self.venv_dir / "bin" / "python")}" bot.py\n')
        
        print("3. Протестируйте бота в Telegram:")
        print("   - Найдите бота по токену")
        print("   - Отправьте /start\n")
        
        print("4. Документация: см. README.md\n")
        print("="*60 + "\n")
    
    def run(self):
        try:
            self.print_header()
            self.check_python()
            
            print("Процесс установки:\n")
            
            if not self.create_venv():
                return False
            
            if not self.install_requirements():
                return False
            
            if not self.configure_bot():
                return False
            
            if not self.create_startup_script():
                return False
            
            self.show_next_steps()
            return True
            
        except KeyboardInterrupt:
            print("\n\n✗ Установка отменена пользователем")
            return False
        except Exception as e:
            print(f"\n✗ Неожиданная ошибка: {e}")
            return False

if __name__ == "__main__":
    installer = BotInstaller()
    success = installer.run()
    sys.exit(0 if success else 1)
