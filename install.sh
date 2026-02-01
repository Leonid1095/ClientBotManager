#!/bin/bash
# ===================================================
# Быстрая установка Telegram-бота на Linux/Mac
# ===================================================

set -e  # Выход при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "===================================================="
echo "  🤖 УСТАНОВКА TELEGRAM-БОТА ДЛЯ ЗАКАЗОВ"
echo "===================================================="
echo ""

# Проверка Python
echo "Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ОШИБКА] Python3 не найден!${NC}"
    echo "Установите Python 3.8+:"
    echo "  Ubuntu/Debian: sudo apt-get install python3"
    echo "  MacOS: brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}[OK] Python $PYTHON_VERSION найден${NC}"
echo ""

# Проверка pip
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}[ОШИБКА] pip3 не найден!${NC}"
    echo "Установите pip:"
    echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
    exit 1
fi

echo -e "${GREEN}[OK] pip найден${NC}"
echo ""

# Запуск установщика
echo "Запуск установщика..."
python3 install.py

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}[ОШИБКА] Установка не удалась${NC}"
    exit 1
fi

echo ""
echo "===================================================="
echo "  ✓ Установка завершена успешно!"
echo "===================================================="
echo ""
