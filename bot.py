"""
Telegram-бот для пересылки сообщений в группу с поддержкой ответов.
Использует aiogram 3.x, SQLite, антиспам.
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import init_db
from handlers import user_router, group_router

# ─── Логирование ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ─── Точка входа ────────────────────────────────────────────────────────────
async def main() -> None:
    logger.info("Инициализация базы данных...")
    await init_db()

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    dp.include_router(user_router)   # Сообщения от пользователей (личка)
    dp.include_router(group_router)  # Ответы из группы

    logger.info("Бот запущен. Ожидание сообщений...")
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    asyncio.run(main())
