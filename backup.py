"""
Модуль для создания и восстановления бекапов данных бота
"""
import os
import json
import zipfile
from datetime import datetime
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class BackupManager:
    """Менеджер бекапов для сохранения данных бота"""
    
    def __init__(self, backup_dir: str = "backups"):
        """
        Инициализация менеджера бекапов
        
        Args:
            backup_dir: Директория для хранения бекапов
        """
        self.backup_dir = backup_dir
        self._ensure_backup_dir()
    
    def _ensure_backup_dir(self):
        """Создает директорию для бекапов если её нет"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Создана директория для бекапов: {self.backup_dir}")
    
    def create_backup(self, data_dict: Dict[str, any]) -> Optional[str]:
        """
        Создает бекап данных в формате ZIP
        
        Args:
            data_dict: Словарь с данными для бекапа
                Ключи: "tickets", "referrals", "bonuses", "reviews"
        
        Returns:
            Путь к созданному бекапу или None в случае ошибки
        """
        try:
            # Формируем имя файла с текущей датой и временем
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(self.backup_dir, backup_filename)
            
            # Создаем временный JSON файл с данными
            temp_json = os.path.join(self.backup_dir, "temp_data.json")
            
            # Подготавливаем данные для сериализации
            serializable_data = {}
            for key, value in data_dict.items():
                if value is not None:
                    serializable_data[key] = value
            
            # Сохраняем в JSON
            with open(temp_json, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, ensure_ascii=False, indent=2)
            
            # Создаем ZIP архив
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(temp_json, arcname="data.json")
                
                # Добавляем метаданные
                metadata = {
                    "created_at": datetime.now().isoformat(),
                    "backup_version": "1.0",
                    "records_count": {
                        "tickets": len(data_dict.get("tickets", {})),
                        "referrals": len(data_dict.get("referrals", {})),
                        "bonuses": len(data_dict.get("bonuses", {})),
                        "reviews": len(data_dict.get("reviews", []))
                    }
                }
                
                metadata_json = os.path.join(self.backup_dir, "temp_metadata.json")
                with open(metadata_json, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, ensure_ascii=False, indent=2)
                
                zipf.write(metadata_json, arcname="metadata.json")
                
                # Удаляем временные файлы
                os.remove(metadata_json)
            
            # Удаляем временный JSON
            os.remove(temp_json)
            
            logger.info(f"Создан бекап: {backup_filename}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании бекапа: {e}")
            return None
    
    def list_backups(self) -> List[Dict[str, any]]:
        """
        Возвращает список всех доступных бекапов
        
        Returns:
            Список словарей с информацией о бекапах
        """
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.zip') and filename.startswith('backup_'):
                    filepath = os.path.join(self.backup_dir, filename)
                    
                    # Получаем размер файла
                    size_bytes = os.path.getsize(filepath)
                    size_kb = round(size_bytes / 1024, 2)
                    
                    # Читаем метаданные из архива
                    metadata = None
                    try:
                        with zipfile.ZipFile(filepath, 'r') as zipf:
                            if 'metadata.json' in zipf.namelist():
                                with zipf.open('metadata.json') as f:
                                    metadata = json.load(f)
                    except Exception as e:
                        logger.warning(f"Не удалось прочитать метаданные из {filename}: {e}")
                    
                    backup_info = {
                        "filename": filename,
                        "filepath": filepath,
                        "size_kb": size_kb,
                        "metadata": metadata
                    }
                    
                    backups.append(backup_info)
            
            # Сортируем по имени файла (по дате создания)
            backups.sort(key=lambda x: x['filename'], reverse=True)
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка бекапов: {e}")
        
        return backups
    
    def restore_backup(self, backup_path: str) -> Optional[Dict[str, any]]:
        """
        Восстанавливает данные из бекапа
        
        Args:
            backup_path: Путь к файлу бекапа
        
        Returns:
            Словарь с восстановленными данными или None в случае ошибки
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Файл бекапа не найден: {backup_path}")
                return None
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Читаем данные
                with zipf.open('data.json') as f:
                    data = json.load(f)
                
                logger.info(f"Бекап восстановлен из {backup_path}")
                return data
                
        except Exception as e:
            logger.error(f"Ошибка при восстановлении бекапа: {e}")
            return None
    
    def delete_backup(self, backup_path: str) -> bool:
        """
        Удаляет файл бекапа
        
        Args:
            backup_path: Путь к файлу бекапа
        
        Returns:
            True если удаление успешно, False иначе
        """
        try:
            if os.path.exists(backup_path):
                os.remove(backup_path)
                logger.info(f"Бекап удален: {backup_path}")
                return True
            else:
                logger.warning(f"Файл бекапа не найден: {backup_path}")
                return False
        except Exception as e:
            logger.error(f"Ошибка при удалении бекапа: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10):
        """
        Удаляет старые бекапы, оставляя только последние N
        
        Args:
            keep_count: Количество последних бекапов для сохранения
        """
        try:
            backups = self.list_backups()
            
            if len(backups) > keep_count:
                backups_to_delete = backups[keep_count:]
                
                for backup in backups_to_delete:
                    self.delete_backup(backup['filepath'])
                
                logger.info(f"Удалено старых бекапов: {len(backups_to_delete)}")
                
        except Exception as e:
            logger.error(f"Ошибка при очистке старых бекапов: {e}")
