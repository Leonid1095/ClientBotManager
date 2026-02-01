# ПОЛНАЯ ИНСТРУКЦИЯ: РАЗВЕРТЫВАНИЕ БОТА НА СЕРВЕРЕ

## 🚀 Быстрая установка (1 команда)

### Linux (Ubuntu/Debian):
```bash
wget https://raw.githubusercontent.com/Leonid1095/ClientBotManager/main/clientbotmanager_setup.sh && chmod +x clientbotmanager_setup.sh && ./clientbotmanager_setup.sh
```

### Или через git:
```bash
git clone https://github.com/Leonid1095/ClientBotManager.git
cd ClientBotManager
chmod +x clientbotmanager_setup.sh
./clientbotmanager_setup.sh
```

---

## 📋 Пошаговая инструкция

### ШАГ 1: Подключение к серверу

#### По SSH:
```bash
ssh username@your-server-ip
```

#### Пример:
```bash
ssh root@192.168.1.100
```

---

### ШАГ 2: Обновление системы

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

---

### ШАГ 3: Установка зависимостей

```bash
# Python и необходимые пакеты
sudo apt-get install -y python3 python3-pip python3-venv git

# Проверка установки
python3 --version
git --version
```

---

### ШАГ 4: Создание директории для бота

```bash
# Создание директории
sudo mkdir -p /opt/clientbotmanager

# Права доступа
sudo chown -R $USER:$USER /opt/clientbotmanager

# Переход в директорию
cd /opt/clientbotmanager
```

---

### ШАГ 5: Загрузка бота

#### Вариант A: Через Git
```bash
git clone https://github.com/Leonid1095/ClientBotManager.git .
```

#### Вариант B: Через wget (zip)
```bash
wget https://github.com/Leonid1095/ClientBotManager/archive/refs/heads/main.zip
unzip main.zip
mv ClientBotManager-main/* .
rm -rf ClientBotManager-main main.zip
```

#### Вариант C: Загрузка через SCP (с локального ПК)
```bash
# На вашем локальном компьютере:
scp -r "e:/Cursor Project/Бот по заказам/"* username@server-ip:/opt/clientbotmanager/
```

---

### ШАГ 6: Установка бота

```bash
cd /opt/clientbotmanager
python3 install.py
```

**Скрипт спросит:**
1. Токен Telegram-бота (от @BotFather)
2. Ваш Telegram ID (от @userinfobot)
3. Email (опционально)
4. Telegram никнейм (опционально)
5. Использовать Google Sheets? (y/n)

---

### ШАГ 7: Настройка автозапуска (systemd)

#### Создание service файла:
```bash
sudo nano /etc/systemd/system/clientbotmanager.service
```

#### Вставьте (замените YOUR_USER на ваше имя пользователя):
```ini
[Unit]
Description=ClientBotManager Telegram Bot
After=network.target

[Service]
Type=simple
User=YOUR_USER
WorkingDirectory=/opt/clientbotmanager
ExecStart=/opt/clientbotmanager/venv/bin/python /opt/clientbotmanager/bot.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/clientbotmanager/bot.log
StandardError=append:/opt/clientbotmanager/bot_error.log

[Install]
WantedBy=multi-user.target
```

#### Сохраните: `Ctrl+O`, `Enter`, `Ctrl+X`

---

### ШАГ 8: Запуск и активация

```bash
# Перезагрузка конфигурации systemd
sudo systemctl daemon-reload

# Включение автозапуска
sudo systemctl enable clientbotmanager.service

# Запуск бота
sudo systemctl start clientbotmanager.service

# Проверка статуса
sudo systemctl status clientbotmanager.service
```

**Ожидаемый результат:**
```
● clientbotmanager.service - ClientBotManager Telegram Bot
   Loaded: loaded (/etc/systemd/system/clientbotmanager.service; enabled)
   Active: active (running) since ...
```

---

### ШАГ 9: Создание скриптов управления

```bash
# Создание скрипта управления
nano /opt/clientbotmanager/control.sh
```

#### Вставьте:
```bash
#!/bin/bash
case "$1" in
    start)
        sudo systemctl start clientbotmanager.service
        echo "Бот запущен"
        ;;
    stop)
        sudo systemctl stop clientbotmanager.service
        echo "Бот остановлен"
        ;;
    restart)
        sudo systemctl restart clientbotmanager.service
        echo "Бот перезапущен"
        ;;
    status)
        sudo systemctl status clientbotmanager.service
        ;;
    logs)
        tail -f /opt/clientbotmanager/bot.log
        ;;
    errors)
        tail -f /opt/clientbotmanager/bot_error.log
        ;;
    update)
        cd /opt/clientbotmanager
        git pull
        sudo systemctl restart clientbotmanager.service
        echo "Бот обновлён"
        ;;
    *)
        echo "Использование: $0 {start|stop|restart|status|logs|errors|update}"
        exit 1
        ;;
esac
```

#### Сделайте исполняемым:
```bash
chmod +x /opt/clientbotmanager/control.sh
```

---

## 🎮 УПРАВЛЕНИЕ БОТОМ

### Основные команды:

```bash
# Запуск бота
/opt/clientbotmanager/control.sh start

# Остановка бота
/opt/clientbotmanager/control.sh stop

# Перезапуск бота
/opt/clientbotmanager/control.sh restart

# Статус бота
/opt/clientbotmanager/control.sh status

# Просмотр логов (в реальном времени)
/opt/clientbotmanager/control.sh logs

# Просмотр ошибок
/opt/clientbotmanager/control.sh errors

# Обновление бота из GitHub
/opt/clientbotmanager/control.sh update
```

### Системные команды:

```bash
# Статус службы
sudo systemctl status clientbotmanager

# Логи systemd
sudo journalctl -u clientbotmanager -f

# Логи за сегодня
sudo journalctl -u clientbotmanager --since today

# Последние 100 строк логов
sudo journalctl -u clientbotmanager -n 100
```

---

## 🔧 НАСТРОЙКА ПОСЛЕ УСТАНОВКИ

### 1. Google Sheets (если используете):

```bash
cd /opt/clientbotmanager

# Загрузите credentials.json на сервер
scp google-credentials.json username@server:/opt/clientbotmanager/

# Проверьте наличие
ls -la google-credentials.json
```

### 2. Редактирование конфигурации:

```bash
nano /opt/clientbotmanager/config.py
```

### 3. Добавление портфолио/FAQ:

```bash
# Портфолио
nano /opt/clientbotmanager/portfolio.py

# FAQ
nano /opt/clientbotmanager/faq.py

# После изменений - перезапуск
/opt/clientbotmanager/control.sh restart
```

---

## 🐛 РЕШЕНИЕ ПРОБЛЕМ

### Бот не запускается:

```bash
# Проверка логов
sudo journalctl -u clientbotmanager -n 50

# Проверка логов бота
tail -50 /opt/clientbotmanager/bot_error.log

# Проверка конфигурации
cat /opt/clientbotmanager/config.py

# Ручной запуск для отладки
cd /opt/clientbotmanager
./venv/bin/python bot.py
```

### Python модули не найдены:

```bash
cd /opt/clientbotmanager
./venv/bin/pip install -r requirements.txt
/opt/clientbotmanager/control.sh restart
```

### Проблемы с правами:

```bash
sudo chown -R $USER:$USER /opt/clientbotmanager
chmod +x /opt/clientbotmanager/control.sh
```

---

## 📊 МОНИТОРИНГ

### Автоматическая проверка работы:

```bash
# Создайте cron задачу для проверки
crontab -e

# Добавьте (проверка каждые 5 минут):
*/5 * * * * systemctl is-active --quiet clientbotmanager || systemctl start clientbotmanager
```

### Просмотр использования ресурсов:

```bash
# Использование CPU и памяти
top -p $(pgrep -f "python.*bot.py")

# Детальная информация
ps aux | grep bot.py
```

---

## 🔄 ОБНОВЛЕНИЕ БОТА

### Автоматическое (из GitHub):

```bash
/opt/clientbotmanager/control.sh update
```

### Ручное:

```bash
cd /opt/clientbotmanager
git pull
./venv/bin/pip install -r requirements.txt
/opt/clientbotmanager/control.sh restart
```

---

## 🔒 БЕЗОПАСНОСТЬ

### 1. Настройка firewall:

```bash
# Разрешить только SSH и исходящий трафик
sudo ufw allow ssh
sudo ufw enable
```

### 2. Создание отдельного пользователя:

```bash
# Создание пользователя для бота
sudo useradd -m -s /bin/bash botuser

# Передача прав
sudo chown -R botuser:botuser /opt/clientbotmanager

# Изменить User в service файле на botuser
```

### 3. Ограничение доступа к config.py:

```bash
chmod 600 /opt/clientbotmanager/config.py
```

---

## 📝 БЭКАП

### Создание бэкапа:

```bash
# Ручной бэкап
tar -czf clientbotmanager-backup-$(date +%Y%m%d).tar.gz /opt/clientbotmanager

# Автоматический бэкап (добавить в cron)
0 2 * * * tar -czf /backups/clientbotmanager-$(date +\%Y\%m\%d).tar.gz /opt/clientbotmanager
```

### Восстановление:

```bash
tar -xzf clientbotmanager-backup-20260201.tar.gz -C /
/opt/clientbotmanager/control.sh restart
```

---

## ✅ ПРОВЕРКА РАБОТОСПОСОБНОСТИ

После установки:

1. ✅ Бот отвечает на команду `/start` в Telegram
2. ✅ Меню отображается корректно
3. ✅ Форма заказа работает
4. ✅ Служба активна: `sudo systemctl is-active clientbotmanager`
5. ✅ Нет ошибок в логах: `tail /opt/clientbotmanager/bot_error.log`
6. ✅ Бот автоматически запускается после перезагрузки сервера

---

## 🎯 ИТОГОВАЯ СТРУКТУРА

```
/opt/clientbotmanager/
├── bot.py                    # Основной файл
├── config.py                 # Конфигурация (токен, user_id)
├── venv/                     # Виртуальное окружение
├── control.sh                # Скрипт управления
├── bot.log                   # Логи работы
├── bot_error.log             # Логи ошибок
├── google-credentials.json   # Credentials (если используете)
└── ...остальные файлы...
```

---

## 📞 ПОДДЕРЖКА

- **GitHub Issues:** https://github.com/Leonid1095/ClientBotManager/issues
- **Документация:** README.md в репозитории
- **Логи:** `/opt/clientbotmanager/control.sh logs`

---

**Готово! Бот работает 24/7 в фоновом режиме!** 🎉
