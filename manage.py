#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для управления ботом
Запуск, остановка, перезагрузка, обновление
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

class BotManager:
    def __init__(self):
        self.project_dir = Path(__file__).parent
        self.bot_file = self.project_dir / "bot.py"
        self.venv_dir = self.project_dir / "venv"
        self.os_type = sys.platform
        self.process = None
    
    def get_python(self):
        if self.os_type == "win32":
            return str(self.venv_dir / "Scripts" / "python.exe")
        else:
            return str(self.venv_dir / "bin" / "python")
    
    def run(self):
        """Запуск бота"""
        print("🚀 Запуск бота...\n")
        
        python_exe = self.get_python()
        if not Path(python_exe).exists():
            print("❌ Виртуальное окружение не найдено!")
            print("Сначала запустите установку: python install.py")
            return False
        
        try:
            self.process = subprocess.Popen(
                [python_exe, str(self.bot_file)],
                cwd=str(self.project_dir)
            )
            print(f"✓ Бот запущен (PID: {self.process.pid})")
            
            # Ожидание завершения
            try:
                self.process.wait()
            except KeyboardInterrupt:
                print("\n⏹ Остановка бота...")
                self.process.terminate()
                self.process.wait(timeout=5)
                print("✓ Бот остановлен")
            
            return True
        except Exception as e:
            print(f"❌ Ошибка при запуске: {e}")
            return False
    
    def update(self):
        """Обновление зависимостей"""
        print("📦 Обновление зависимостей...\n")
        
        if self.os_type == "win32":
            pip_exe = self.venv_dir / "Scripts" / "pip.exe"
        else:
            pip_exe = self.venv_dir / "bin" / "pip"
        
        try:
            subprocess.check_call([str(pip_exe), "install", "--upgrade", "-r", "requirements.txt"])
            print("\n✓ Зависимости обновлены")
            return True
        except Exception as e:
            print(f"❌ Ошибка при обновлении: {e}")
            return False
    
    def show_menu(self):
        """Главное меню"""
        print("\n" + "="*50)
        print("  🤖 МЕНЕДЖЕР TELEGRAM-БОТА")
        print("="*50)
        print("\n1. Запустить бота")
        print("2. Обновить зависимости")
        print("3. Просмотр логов")
        print("4. Выход")
        print()
    
    def view_logs(self):
        """Просмотр логов"""
        log_file = self.project_dir / "bot.log"
        if not log_file.exists():
            print("📄 Логи пока не созданы")
            return
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Показываем последние 50 строк
                print("\n" + "="*50)
                print("📄 ПОСЛЕДНИЕ ЛОГИ (последние 50 строк)")
                print("="*50 + "\n")
                print(''.join(lines[-50:]))
        except Exception as e:
            print(f"❌ Ошибка при чтении логов: {e}")

def main():
    manager = BotManager()
    
    print("\n" + "="*50)
    print("  🤖 МЕНЕДЖЕР TELEGRAM-БОТА")
    print("="*50)
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "run":
            manager.run()
        elif command == "update":
            manager.update()
        elif command == "logs":
            manager.view_logs()
        else:
            print(f"Неизвестная команда: {command}")
            print("\nДоступные команды:")
            print("  python manage.py run      - Запустить бота")
            print("  python manage.py update   - Обновить зависимости")
            print("  python manage.py logs    - Просмотр логов")
    else:
        # Интерактивное меню
        while True:
            manager.show_menu()
            choice = input("Выберите действие: ").strip()
            
            if choice == "1":
                manager.run()
            elif choice == "2":
                manager.update()
            elif choice == "3":
                manager.view_logs()
            elif choice == "4":
                print("\n👋 До свидания!")
                break
            else:
                print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
