#!/bin/bash
# ===================================================
# ClientBotManager - Автоматическое развертывание
# Telegram Bot для управления заказами
# ===================================================

set -e  # Выход при ошибке

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "=========================================="
echo "  🤖 ClientBotManager Setup"
echo "  Развертывание на Linux-сервер"
echo "=========================================="
echo -e "${NC}"

# Проверка прав root
if [[ $EUID -ne 0 ]]; then
   echo -e "${YELLOW}Внимание: Для установки системных зависимостей могут потребоваться права sudo${NC}"
fi

# 1. Обновление системы
echo -e "${BLUE}[1/8] Обновление системы...${NC}"
sudo apt-get update -qq

# 2. Установка Python и зависимостей
echo -e "${BLUE}[2/8] Установка Python и зависимостей...${NC}"
sudo apt-get install -y python3 python3-pip python3-venv git

# 3. Проверка Python версии
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION установлен${NC}"

# 4. Создание директории для бота
echo -e "${BLUE}[3/8] Создание директории для ClientBotManager...${NC}"
BOT_DIR="/opt/clientbotmanager"
read -p "Директория для установки [$BOT_DIR]: " USER_DIR
BOT_DIR=${USER_DIR:-$BOT_DIR}

if [ -d "$BOT_DIR" ]; then
    read -p "Директория существует. Очистить? (y/n): " CLEAR
    if [ "$CLEAR" = "y" ]; then
        sudo rm -rf "$BOT_DIR"
    fi
fi

sudo mkdir -p "$BOT_DIR"
sudo chown -R $USER:$USER "$BOT_DIR"
cd "$BOT_DIR"

echo -e "${GREEN}✓ Директория создана: $BOT_DIR${NC}"

# 5. Клонирование репозитория
echo -e "${BLUE}[4/8] Загрузка ClientBotManager с GitHub...${NC}"
read -p "Клонировать из GitHub? (y/n): " CLONE
if [ "$CLONE" = "y" ]; then
    git clone https://github.com/Leonid1095/ClientBotManager.git .
    echo -e "${GREEN}✓ Репозиторий загружен${NC}"
else
    echo -e "${YELLOW}Скопируйте файлы бота в $BOT_DIR${NC}"
    read -p "Нажмите Enter после копирования файлов..."
fi

# 6. Запуск установщика
echo -e "${BLUE}[5/8] Запуск установщика ClientBotManager...${NC}"
python3 install.py

# 7. Создание systemd service
echo -e "${BLUE}[6/8] Настройка автозапуска (systemd)...${NC}"

SERVICE_FILE="/etc/systemd/system/clientbotmanager.service"
sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=ClientBotManager Telegram Bot
Documentation=https://github.com/Leonid1095/ClientBotManager
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$BOT_DIR
ExecStart=$BOT_DIR/venv/bin/python $BOT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=append:$BOT_DIR/clientbotmanager.log
StandardError=append:$BOT_DIR/clientbotmanager_error.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✓ Systemd service создан${NC}"

# 8. Запуск и активация службы
echo -e "${BLUE}[7/8] Запуск службы...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable clientbotmanager.service
sudo systemctl start clientbotmanager.service

# Проверка статуса
sleep 2
if sudo systemctl is-active --quiet clientbotmanager.service; then
    echo -e "${GREEN}✓ ClientBotManager успешно запущен!${NC}"
else
    echo -e "${RED}✗ Ошибка при запуске. Проверьте логи: journalctl -u clientbotmanager -n 50${NC}"
fi

# 9. Создание скриптов управления
echo -e "${BLUE}[8/8] Создание скриптов управления...${NC}"

cat > "$BOT_DIR/cbm-control.sh" <<'CONTROL'
#!/bin/bash
# ClientBotManager Control Script

SERVICE_NAME="clientbotmanager"
BOT_DIR="/opt/clientbotmanager"

case "$1" in
    start)
        sudo systemctl start $SERVICE_NAME.service
        echo "✓ ClientBotManager запущен"
        ;;
    stop)
        sudo systemctl stop $SERVICE_NAME.service
        echo "✓ ClientBotManager остановлен"
        ;;
    restart)
        sudo systemctl restart $SERVICE_NAME.service
        echo "✓ ClientBotManager перезапущен"
        ;;
    status)
        sudo systemctl status $SERVICE_NAME.service
        ;;
    logs)
        tail -f $BOT_DIR/clientbotmanager.log
        ;;
    errors)
        tail -f $BOT_DIR/clientbotmanager_error.log
        ;;
    update)
        cd $BOT_DIR
        git pull
        sudo systemctl restart $SERVICE_NAME.service
        echo "✓ ClientBotManager обновлён и перезапущен"
        ;;
    *)
        echo "ClientBotManager Control"
        echo "Использование: $0 {start|stop|restart|status|logs|errors|update}"
        exit 1
        ;;
esac
CONTROL

chmod +x "$BOT_DIR/cbm-control.sh"

echo -e "${GREEN}✓ Скрипты управления созданы${NC}"

# Итоги
echo ""
echo -e "${BLUE}=========================================="
echo "  ✓ УСТАНОВКА CLIENTBOTMANAGER ЗАВЕРШЕНА!"
echo "==========================================${NC}"
echo ""
echo -e "${GREEN}Команды управления:${NC}"
echo "  $BOT_DIR/cbm-control.sh start    - Запустить бота"
echo "  $BOT_DIR/cbm-control.sh stop     - Остановить бота"
echo "  $BOT_DIR/cbm-control.sh restart  - Перезапустить бота"
echo "  $BOT_DIR/cbm-control.sh status   - Статус бота"
echo "  $BOT_DIR/cbm-control.sh logs     - Просмотр логов"
echo "  $BOT_DIR/cbm-control.sh errors   - Просмотр ошибок"
echo "  $BOT_DIR/cbm-control.sh update   - Обновить из GitHub"
echo ""
echo -e "${GREEN}Системные команды:${NC}"
echo "  sudo systemctl status clientbotmanager      - Статус службы"
echo "  sudo journalctl -u clientbotmanager -f      - Логи systemd"
echo ""
echo -e "${BLUE}Бот работает 24/7 и автоматически запустится после перезагрузки!${NC}"
echo ""
