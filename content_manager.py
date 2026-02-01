"""
Модуль для управления контентом бота через JSON файлы
Позволяет администратору редактировать контент без доступа к серверу
"""

import json
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContentManager:
    """Менеджер контента - работа с JSON файлами"""
    
    def __init__(self, content_dir: str = "content"):
        """Инициализация менеджера контента"""
        self.content_dir = content_dir
        self._ensure_content_dir()
        
        # Пути к JSON файлам
        self.portfolio_file = os.path.join(content_dir, "portfolio.json")
        self.faq_file = os.path.join(content_dir, "faq.json")
        self.contacts_file = os.path.join(content_dir, "contacts.json")
        self.about_file = os.path.join(content_dir, "about.json")
    
    def _ensure_content_dir(self):
        """Создает директорию контента если её нет"""
        if not os.path.exists(self.content_dir):
            os.makedirs(self.content_dir)
            logger.info(f"Создана директория контента: {self.content_dir}")
    
    def _load_json(self, filepath: str, default: any) -> any:
        """Загружает JSON файл или возвращает значение по умолчанию"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке {filepath}: {e}")
        return default
    
    def _save_json(self, filepath: str, data: any) -> bool:
        """Сохраняет данные в JSON файл"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Сохранено: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении {filepath}: {e}")
            return False
    
    # ==================== ПОРТФОЛИО ====================
    
    def get_portfolio(self) -> List[Dict]:
        """Получить все кейсы портфолио"""
        return self._load_json(self.portfolio_file, [])
    
    def add_portfolio_case(self, title: str, desc: str, details: str) -> bool:
        """Добавить новый кейс в портфолио"""
        portfolio = self.get_portfolio()
        
        # Генерируем ID
        case_id = f"case_{len(portfolio) + 1}"
        
        new_case = {
            "id": case_id,
            "title": title,
            "desc": desc,
            "details": details,
            "added_date": datetime.now().isoformat()
        }
        
        portfolio.append(new_case)
        return self._save_json(self.portfolio_file, portfolio)
    
    def update_portfolio_case(self, case_id: str, title: str = None, desc: str = None, details: str = None) -> bool:
        """Редактировать существующий кейс"""
        portfolio = self.get_portfolio()
        
        for case in portfolio:
            if case["id"] == case_id:
                if title:
                    case["title"] = title
                if desc:
                    case["desc"] = desc
                if details:
                    case["details"] = details
                case["updated_date"] = datetime.now().isoformat()
                return self._save_json(self.portfolio_file, portfolio)
        
        logger.warning(f"Кейс {case_id} не найден")
        return False
    
    def delete_portfolio_case(self, case_id: str) -> bool:
        """Удалить кейс из портфолио"""
        portfolio = self.get_portfolio()
        portfolio = [c for c in portfolio if c["id"] != case_id]
        return self._save_json(self.portfolio_file, portfolio)
    
    # ==================== FAQ ====================
    
    def get_faq(self) -> List[Dict]:
        """Получить все Q&A"""
        return self._load_json(self.faq_file, [])
    
    def add_faq(self, question: str, answer: str) -> bool:
        """Добавить новый вопрос/ответ"""
        faq = self.get_faq()
        
        faq_id = f"faq_{len(faq) + 1}"
        
        new_faq = {
            "id": faq_id,
            "q": question,
            "a": answer,
            "added_date": datetime.now().isoformat()
        }
        
        faq.append(new_faq)
        return self._save_json(self.faq_file, faq)
    
    def update_faq(self, faq_id: str, question: str = None, answer: str = None) -> bool:
        """Редактировать вопрос/ответ"""
        faq = self.get_faq()
        
        for item in faq:
            if item["id"] == faq_id:
                if question:
                    item["q"] = question
                if answer:
                    item["a"] = answer
                item["updated_date"] = datetime.now().isoformat()
                return self._save_json(self.faq_file, faq)
        
        logger.warning(f"FAQ {faq_id} не найден")
        return False
    
    def delete_faq(self, faq_id: str) -> bool:
        """Удалить вопрос/ответ"""
        faq = self.get_faq()
        faq = [f for f in faq if f["id"] != faq_id]
        return self._save_json(self.faq_file, faq)
    
    # ==================== КОНТАКТЫ ====================
    
    def get_contacts(self) -> Dict:
        """Получить контакты"""
        return self._load_json(self.contacts_file, {
            "telegram": "@ваш_ник",
            "email": "email@example.com",
            "phone": "+7 (XXX) XXX-XX-XX",
            "whatsapp": ""
        })
    
    def update_contacts(self, **kwargs) -> bool:
        """Обновить контакты"""
        contacts = self.get_contacts()
        contacts.update(kwargs)
        contacts["updated_date"] = datetime.now().isoformat()
        return self._save_json(self.contacts_file, contacts)
    
    # ==================== О СЕБЕ ====================
    
    def get_about(self) -> str:
        """Получить текст 'О себе'"""
        about = self._load_json(self.about_file, {})
        return about.get("text", "👤 <b>О себе</b>\nИнформация будет добавлена администратором.")
    
    def update_about(self, text: str) -> bool:
        """Обновить текст 'О себе'"""
        about = {
            "text": text,
            "updated_date": datetime.now().isoformat()
        }
        return self._save_json(self.about_file, about)
    
    # ==================== ВСПОМОГАТЕЛЬНЫЕ ====================
    
    def get_stats(self) -> Dict:
        """Получить статистику контента"""
        return {
            "portfolio_count": len(self.get_portfolio()),
            "faq_count": len(self.get_faq()),
            "contacts_updated": self.get_contacts().get("updated_date", "никогда"),
            "about_updated": self._load_json(self.about_file, {}).get("updated_date", "никогда")
        }
    
    def export_all(self) -> Dict:
        """Экспортировать весь контент"""
        return {
            "portfolio": self.get_portfolio(),
            "faq": self.get_faq(),
            "contacts": self.get_contacts(),
            "about": self.get_about(),
            "exported_at": datetime.now().isoformat()
        }


# Глобальный экземпляр
content_manager = ContentManager()
