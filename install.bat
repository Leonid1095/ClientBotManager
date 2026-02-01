@echo off
REM ===================================================
REM  Быстрая установка Telegram-бота на Windows
REM ===================================================

chcp 65001 > nul

echo.
echo ====================================================
echo.  УСТАНОВКА TELEGRAM-БОТА ДЛЯ ЗАКАЗОВ
echo.
echo  Эта программа установит бота и настроит его
echo ====================================================
echo.

REM Проверка Python
echo Проверка Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ОШИБКА] Python не найден!
    echo.
    echo Установите Python 3.8+ с https://www.python.org
    echo При установке отметьте "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

echo [OK] Python найден
echo.

REM Запуск установщика
echo Запуск установщика...
python install.py

if errorlevel 1 (
    echo.
    echo [ОШИБКА] Установка не удалась
    echo.
    pause
    exit /b 1
)

echo.
echo ====================================================
echo  Установка завершена успешно!
echo ====================================================
echo.
pause
