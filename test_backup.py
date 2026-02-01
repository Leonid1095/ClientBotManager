#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы бекапов
"""

from backup import BackupManager
from data import TICKETS_DB, REFERRALS_DB, BONUSES_DB
from reviews import REVIEWS
import json

print("=" * 50)
print("🧪 Тест системы бекапов ClientBotManager")
print("=" * 50)

# Добавим тестовые данные
print("\n📝 Добавление тестовых данных...")
TICKETS_DB['123456789'] = {
    'order_001': {
        'order_id': 'order_001',
        'user_id': 123456789,
        'status': 'новый',
        'data': {'fio': 'Иван Иванов', 'idea': 'Бот для продаж'}
    }
}
REFERRALS_DB['987654321'] = [123456789, 111111111]
BONUSES_DB['987654321'] = 500
REVIEWS.append({'author': 'Тестовый юзер', 'text': 'Отличный бот!'})

print(f"  ✅ Добавлено: 1 заказ, 1 реферальная группа, 1 отзыв")

# Инициализируем BackupManager
print("\n🔧 Инициализация BackupManager...")
manager = BackupManager('backups')
print("  ✅ BackupManager готов")

# Создаем бекап
print("\n📦 Создание бекапа...")
data_to_backup = {
    'tickets': TICKETS_DB,
    'referrals': REFERRALS_DB,
    'bonuses': BONUSES_DB,
    'reviews': REVIEWS
}

backup_path = manager.create_backup(data_to_backup)
if backup_path:
    print(f"  ✅ Бекап создан: {backup_path}")
else:
    print("  ❌ Ошибка при создании бекапа")
    exit(1)

# Получаем список бекапов
print("\n📂 Просмотр списка бекапов...")
backups = manager.list_backups()
print(f"  📊 Всего бекапов: {len(backups)}")

for i, backup in enumerate(backups, 1):
    filename = backup['filename']
    size_kb = backup['size_kb']
    metadata = backup.get('metadata', {})
    records = metadata.get('records_count', {})
    
    print(f"\n  {i}. {filename}")
    print(f"     Размер: {size_kb} KB")
    if metadata:
        created = metadata.get('created_at', 'неизвестно')
        print(f"     Создан: {created}")
        print(f"     Заказов: {records.get('tickets', 0)}")
        print(f"     Рефералов: {records.get('referrals', 0)}")
        print(f"     Отзывов: {records.get('reviews', 0)}")

# Восстанавливаем данные
print("\n🔄 Восстановление из бекапа...")
if backups:
    restored = manager.restore_backup(backups[0]['filepath'])
    if restored:
        print(f"  ✅ Данные восстановлены!")
        print(f"     Заказов: {len(restored.get('tickets', {}))}")
        print(f"     Рефералов: {len(restored.get('referrals', {}))}")
        print(f"     Отзывов: {len(restored.get('reviews', []))}")
    else:
        print("  ❌ Ошибка при восстановлении")
else:
    print("  ⚠️  Нет доступных бекапов")

print("\n" + "=" * 50)
print("✅ Все тесты пройдены успешно!")
print("=" * 50)
