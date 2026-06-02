"""
Обработчик ответов (reply) из группы.
Когда участник группы отвечает на сообщение — бот пересылает ответ пользователю.
"""

import logging

from aiogram import Router, Bot, F
from aiogram.types import Message

from config import GROUP_ID
from database import get_user_id_by_group_message

logger = logging.getLogger(__name__)
router = Router()


def is_reply_to_bot_forward(message: Message) -> bool:
    """Проверяет, что сообщение — это reply на сообщение в нужной группе."""
    return (
        message.reply_to_message is not None
        and message.chat.id == GROUP_ID
    )


# ─── Текстовый ответ из группы ─────────────────────────────────────────────
@router.message(
    F.chat.id == GROUP_ID,
    F.reply_to_message.as_("replied"),
    F.text,
)
async def group_reply_text(message: Message, bot: Bot, replied: Message) -> None:
    """Пересылает текстовый ответ из группы пользователю."""
    group_msg_id = replied.message_id
    user_id = await get_user_id_by_group_message(group_msg_id)

    if not user_id:
        # Это reply не на сообщение от бота — игнорируем
        return

    responder = message.from_user.full_name or "Администратор"

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"📬 <b>Ответ от команды поддержки</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{responder}:</b>\n\n"
                f"{message.text}"
            ),
        )
        logger.info(f"Текстовый ответ из группы переслан пользователю {user_id}")
    except Exception as e:
        logger.error(f"Не удалось отправить текстовый ответ пользователю {user_id}: {e}")


# ─── Фото-ответ из группы ──────────────────────────────────────────────────
@router.message(
    F.chat.id == GROUP_ID,
    F.reply_to_message.as_("replied"),
    F.photo,
)
async def group_reply_photo(message: Message, bot: Bot, replied: Message) -> None:
    """Пересылает фото-ответ из группы пользователю."""
    group_msg_id = replied.message_id
    user_id = await get_user_id_by_group_message(group_msg_id)

    if not user_id:
        return

    responder = message.from_user.full_name or "Администратор"
    user_caption = message.caption or ""

    caption = (
        f"📬 <b>Ответ от команды поддержки</b>\n"
        f"{'─' * 30}\n"
        f"👤 <b>{responder}:</b>"
    )
    if user_caption:
        caption += f"\n{user_caption}"

    try:
        photo = message.photo[-1]
        await bot.send_photo(
            chat_id=user_id,
            photo=photo.file_id,
            caption=caption,
        )
        logger.info(f"Фото-ответ из группы переслан пользователю {user_id}")
    except Exception as e:
        logger.error(f"Не удалось отправить фото пользователю {user_id}: {e}")


# ─── Голосовой ответ из группы ─────────────────────────────────────────────
@router.message(
    F.chat.id == GROUP_ID,
    F.reply_to_message.as_("replied"),
    F.voice,
)
async def group_reply_voice(message: Message, bot: Bot, replied: Message) -> None:
    """Пересылает голосовой ответ из группы пользователю."""
    group_msg_id = replied.message_id
    user_id = await get_user_id_by_group_message(group_msg_id)

    if not user_id:
        return

    responder = message.from_user.full_name or "Администратор"

    try:
        await bot.send_voice(
            chat_id=user_id,
            voice=message.voice.file_id,
            caption=(
                f"📬 <b>Голосовой ответ от команды поддержки</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{responder}</b>"
            ),
        )
        logger.info(f"Голосовой ответ из группы переслан пользователю {user_id}")
    except Exception as e:
        logger.error(f"Не удалось отправить голосовое пользователю {user_id}: {e}")


# ─── Документ-ответ из группы ──────────────────────────────────────────────
@router.message(
    F.chat.id == GROUP_ID,
    F.reply_to_message.as_("replied"),
    F.document,
)
async def group_reply_document(message: Message, bot: Bot, replied: Message) -> None:
    """Пересылает документ-ответ из группы пользователю."""
    group_msg_id = replied.message_id
    user_id = await get_user_id_by_group_message(group_msg_id)

    if not user_id:
        return

    responder = message.from_user.full_name or "Администратор"
    user_caption = message.caption or ""

    caption = (
        f"📬 <b>Документ от команды поддержки</b>\n"
        f"{'─' * 30}\n"
        f"👤 <b>{responder}:</b>"
    )
    if user_caption:
        caption += f"\n{user_caption}"

    try:
        await bot.send_document(
            chat_id=user_id,
            document=message.document.file_id,
            caption=caption,
        )
        logger.info(f"Документ-ответ из группы переслан пользователю {user_id}")
    except Exception as e:
        logger.error(f"Не удалось отправить документ пользователю {user_id}: {e}")
