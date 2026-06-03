"""
Обработчик личного чата пользователя.
Добавляет две кнопки: «Связь со службой» и «Реклама»,
и поддерживает пересылку сообщений в группу поддержки.
"""

import time
import logging

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)

from config import GROUP_ID, ANTISPAM_DELAY
from database import (
    save_user,
    save_message_map,
    get_antispam_time,
    update_antispam_time,
)

logger = logging.getLogger(__name__)
router = Router()


def format_user_info(message: Message) -> str:
    user = message.from_user
    username = f"@{user.username}" if user.username else "не указан"
    full_name = user.full_name or "—"
    return (
        f"📨 <b>Новое сообщение</b>\n"
        f"{'─' * 30}\n"
        f"👤 <b>Пользователь:</b> {full_name}\n"
        f"🔗 <b>Username:</b> {username}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"{'─' * 30}\n"
    )


# Временное хранилище ожиданий: user_id -> {'action': 'support'|'ads', 'days': int|None}
pending_action: dict[int, dict] = {}


def main_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Связь со службой", callback_data="support")],
        [InlineKeyboardButton(text="Реклама", callback_data="ads")],
    ])
    return kb


def ads_days_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 день", callback_data="ads_1")],
        [InlineKeyboardButton(text="3 дня", callback_data="ads_3")],
        [InlineKeyboardButton(text="7 дней", callback_data="ads_7")],
    ])
    return kb


@router.message(CommandStart(), F.chat.type == "private")
async def cmd_start(message: Message) -> None:
    await save_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Выберите цель обращения — мы поможем быстрее.\n",
        reply_markup=main_keyboard(),
    )


@router.callback_query(F.data == "support")
async def on_support(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    pending_action[user_id] = {"action": "support"}
    await cb.answer("Вы выбрали: служба поддержки", show_alert=False)
    await cb.message.answer(
        "✉️ Напишите ваше сообщение — мы перенаправим его в службу поддержки."
    )


@router.callback_query(F.data == "ads")
async def on_ads(cb: CallbackQuery) -> None:
    await cb.answer("Выберите период размещения", show_alert=False)
    await cb.message.answer(
        "📣 На сколько дней вы хотите разместить рекламу?",
        reply_markup=ads_days_keyboard(),
    )


@router.callback_query(F.data.in_(["ads_1", "ads_3", "ads_7"]))
async def on_ads_days(cb: CallbackQuery) -> None:
    user_id = cb.from_user.id
    days = int(cb.data.split("_")[1])
    pending_action[user_id] = {"action": "ads", "days": days}
    await cb.answer(f"Вы выбрали {days} дней", show_alert=False)
    await cb.message.answer(
        f"📎 Отправьте материал рекламы:\n"
        f"• Видео\n"
        f"• Фото\n"
        f"• Ссылку или текст\n\n"
        f"(Период: <b>{days} дн.</b>)"
    )


async def check_antispam(user_id: int) -> float | None:
    last_time = await get_antispam_time(user_id)
    if last_time is None:
        return None
    elapsed = time.time() - last_time
    if elapsed < ANTISPAM_DELAY:
        return ANTISPAM_DELAY - elapsed
    return None


@router.message(F.chat.type == "private")
async def handle_private_message(message: Message, bot: Bot) -> None:
    user_id = message.from_user.id

    # Если пользователь не выбирал действие — показываем меню
    action_data = pending_action.get(user_id)
    if not action_data:
        await message.answer(
            "Выберите, пожалуйста, цель обращения:",
            reply_markup=main_keyboard(),
        )
        return

    action = action_data.get("action")

    # Антиспам
    wait_time = await check_antispam(user_id)
    if wait_time:
        await message.answer(f"⏳ Пожалуйста, подождите ещё <b>{wait_time:.1f} сек.</b>")
        return

    await update_antispam_time(user_id, time.time())

    # ─────────────────────────────────────────────────────────────────────────
    # ПОДДЕРЖКА: текстовое сообщение
    # ─────────────────────────────────────────────────────────────────────────
    if action == "support" and message.text:
        tag = "[Поддержка]"
        caption = format_user_info(message) + f"{tag}\n\n{message.text}"

        try:
            sent = await bot.send_message(chat_id=GROUP_ID, text=caption)
            await save_message_map(sent.message_id, user_id)
            await message.answer("✅ Ваше сообщение отправлено. Спасибо!")
            logger.info(f"Поддержка: user={user_id} -> group_msg={sent.message_id}")
        except Exception as e:
            logger.error(f"Ошибка при отправке в группу: {e}")
            await message.answer("❌ Не удалось отправить. Попробуйте позже.")

        pending_action.pop(user_id, None)
        return

    # ─────────────────────────────────────────────────────────────────────────
    # РЕКЛАМА: видео, фото или текст
    # ─────────────────────────────────────────────────────────────────────────
    if action == "ads":
        days = action_data.get("days", "?")
        user = message.from_user
        username = f"@{user.username}" if user.username else "не указан"
        full_name = user.full_name or "—"

        # Текст / ссылка
        if message.text:
            caption = (
                f"📣 <b>Запрос на рекламу</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{full_name}</b> ({username})\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"📅 <b>Период:</b> {days} дней\n"
                f"{'─' * 30}\n"
                f"💬 <b>Материал:</b>\n{message.text}"
            )
            try:
                sent = await bot.send_message(chat_id=GROUP_ID, text=caption)
                await save_message_map(sent.message_id, user_id)
                await message.answer("✅ Запрос на рекламу отправлен!")
                logger.info(f"Реклама (текст): user={user_id} -> group_msg={sent.message_id}")
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await message.answer("❌ Ошибка отправки.")

        # Видео
        elif message.video:
            header = (
                f"📣 <b>Запрос на рекламу</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{full_name}</b> ({username})\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"📅 <b>Период:</b> {days} дней\n"
                f"{'─' * 30}\n"
                f"🎬 <b>Видео</b>"
            )
            user_caption = message.caption or ""
            if user_caption:
                header += f"\n📝 <b>Описание:</b> {user_caption}"

            try:
                sent = await bot.send_video(
                    chat_id=GROUP_ID,
                    video=message.video.file_id,
                    caption=header,
                )
                await save_message_map(sent.message_id, user_id)
                await message.answer("✅ Видео рекламы отправлено!")
                logger.info(f"Реклама (видео): user={user_id} -> group_msg={sent.message_id}")
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await message.answer("❌ Ошибка отправки видео.")

        # Фото
        elif message.photo:
            header = (
                f"📣 <b>Запрос на рекламу</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{full_name}</b> ({username})\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"📅 <b>Период:</b> {days} дней\n"
                f"{'─' * 30}\n"
                f"🖼 <b>Фото</b>"
            )
            user_caption = message.caption or ""
            if user_caption:
                header += f"\n📝 <b>Описание:</b> {user_caption}"

            try:
                photo = message.photo[-1]
                sent = await bot.send_photo(
                    chat_id=GROUP_ID,
                    photo=photo.file_id,
                    caption=header,
                )
                await save_message_map(sent.message_id, user_id)
                await message.answer("✅ Фото рекламы отправлено!")
                logger.info(f"Реклама (фото): user={user_id} -> group_msg={sent.message_id}")
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await message.answer("❌ Ошибка отправки фото.")

        # Документ
        elif message.document:
            header = (
                f"📣 <b>Запрос на рекламу</b>\n"
                f"{'─' * 30}\n"
                f"👤 <b>{full_name}</b> ({username})\n"
                f"🆔 User ID: <code>{user.id}</code>\n"
                f"📅 <b>Период:</b> {days} дней\n"
                f"{'─' * 30}\n"
                f"📎 <b>Документ:</b> {message.document.file_name or 'файл'}"
            )
            user_caption = message.caption or ""
            if user_caption:
                header += f"\n📝 <b>Описание:</b> {user_caption}"

            try:
                sent = await bot.send_document(
                    chat_id=GROUP_ID,
                    document=message.document.file_id,
                    caption=header,
                )
                await save_message_map(sent.message_id, user_id)
                await message.answer("✅ Материал рекламы отправлен!")
                logger.info(f"Реклама (документ): user={user_id} -> group_msg={sent.message_id}")
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await message.answer("❌ Ошибка отправки документа.")

        else:
            await message.answer(
                "❌ Пожалуйста, отправьте текст, видео, фото или документ."
            )
            return

        pending_action.pop(user_id, None)
        return

    # Если тип действия неизвестен
    await message.answer(
        "⚠️ Неизвестное действие. Выберите цель обращения:",
        reply_markup=main_keyboard(),
    )

