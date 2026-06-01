# config.py - Конфигурация приложения
import os

# Базовая директория проекта
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Класс конфигурации приложения"""

    # Секретный ключ для сессий и CSRF
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'pifstroiactiv-secret-key-2024-very-secure'

    # Настройки базы данных SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Настройки загрузки файлов
    UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # Максимум 16 МБ
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    # Пагинация
    PRODUCTS_PER_PAGE = 10
    ORDERS_PER_PAGE = 10
    USERS_PER_PAGE = 20