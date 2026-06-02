"""
Работа с SQLite базой данных.
Хранит пользователей и связку message_id (группа) ↔ user_id.
"""

import aiosqlite
import logging

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"


async def init_db() -> None:
    """Создаёт таблицы при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                last_name   TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Таблица для антиспама: время последнего сообщения
        await db.execute("""
            CREATE TABLE IF NOT EXISTS antispam (
                user_id     INTEGER PRIMARY KEY,
                last_msg_at REAL NOT NULL
            )
        """)

        # Таблица связки: message_id в группе → user_id
        # Нужна чтобы знать, кому отправить reply из группы
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_map (
                group_message_id  INTEGER PRIMARY KEY,
                user_id           INTEGER NOT NULL,
                created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await db.commit()
    logger.info("База данных инициализирована.")


async def save_user(user_id: int, username: str | None,
                    first_name: str | None, last_name: str | None) -> None:
    """Сохраняет или обновляет пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name
        """, (user_id, username, first_name, last_name))
        await db.commit()


async def get_antispam_time(user_id: int) -> float | None:
    """Возвращает timestamp последнего сообщения пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT last_msg_at FROM antispam WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def update_antispam_time(user_id: int, timestamp: float) -> None:
    """Обновляет время последнего сообщения для антиспама."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO antispam (user_id, last_msg_at)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_msg_at = excluded.last_msg_at
        """, (user_id, timestamp))
        await db.commit()


async def save_message_map(group_message_id: int, user_id: int) -> None:
    """Сохраняет связку: ID сообщения в группе → ID пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO message_map (group_message_id, user_id)
            VALUES (?, ?)
        """, (group_message_id, user_id))
        await db.commit()


async def get_user_id_by_group_message(group_message_id: int) -> int | None:
    """Возвращает user_id по ID сообщения в группе."""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user_id FROM message_map WHERE group_message_id = ?",
            (group_message_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
