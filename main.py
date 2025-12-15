"""
Точка входа для запуска бота.
"""
import asyncio
import nest_asyncio
import logging
import threading
import http.server
import socketserver
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from config import API_TOKEN, KEEPALIVE_PORT
from database.session import init_db
from utils.logging_config import setup_logging
from handlers import (
    register_common_handlers,
    register_start_handlers,
    register_workout_handlers,
    register_meal_handlers,
    register_weight_handlers,
    register_supplement_handlers,
    register_water_handlers,
    register_settings_handlers,
)

# Настраиваем логирование
setup_logging()

logger = logging.getLogger(__name__)


class ReusableTCPServer(socketserver.TCPServer):
    """TCP сервер с возможностью переиспользования адреса."""
    allow_reuse_address = True


def start_keepalive_server():
    """Запускает keep-alive HTTP сервер в отдельном потоке."""
    PORT = KEEPALIVE_PORT
    handler = http.server.SimpleHTTPRequestHandler
    with ReusableTCPServer(("", PORT), handler) as httpd:
        logger.info(f"✅ Keep-alive сервер запущен на порту {PORT}")
        httpd.serve_forever()


async def main():
    """Основная функция запуска бота."""
    # Инициализация БД
    logger.info("Инициализация базы данных...")
    init_db()
    
    # Создаём бота и диспетчер с FSM storage
    bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем обработчики
    logger.info("Регистрация обработчиков...")
    register_common_handlers(dp)
    register_start_handlers(dp)
    register_workout_handlers(dp)
    register_meal_handlers(dp)
    register_weight_handlers(dp)
    register_supplement_handlers(dp)
    register_water_handlers(dp)
    register_settings_handlers(dp)
    
    # Запускаем keep-alive сервер
    threading.Thread(target=start_keepalive_server, daemon=True).start()
    
    logger.info("🚀 Бот запущен и готов к работе!")
    
    # Запускаем polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())
