"""Система отправки сообщений о помощи."""
import os
import sys
from typing import List

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.media_group import MediaGroupBuilder

from config import Support, active_alerts, admin_ids_set, bot, try_delete
from keyboards import get_main_kb

sys.path.append(os.path.join(os.path.dirname(__file__), '...'))


user_help = Router()


@user_help.callback_query(F.data == "contact_support")
async def start_support(callback: types.CallbackQuery, state: FSMContext):
    """Ввод описания проблемы."""

    await state.set_state(Support.waiting_for_message)
    await callback.message.edit_text(
        "Опишите вашу проблему одним сообщением (можно прикрепить фото), "
        "и организатор ответит вам здесь.",
        reply_markup=None,
    )
    await state.update_data(last_bot_msg_id=callback.message.message_id)
    await callback.answer()


@user_help.message(Support.waiting_for_message)
async def forward_to_admin(
    message: types.Message,
    state: FSMContext,
    album: List[types.Message] = None
):
    """
    1. Формирование алерта запроса в поддержку;
    2. Рассылка алерта организаторам.
    """

    data = await state.get_data()

    user_text = ""
    if album:
        for msg in album:
            if msg.caption:
                user_text = msg.caption
                break
    else:
        user_text = message.text or message.caption or ""

    if not user_text and not album and not message.photo and not message.document:
        user_text = "Без текста"

    user_link = f"(@{message.from_user.username})" if message.from_user.username else "(Без username)"

    header_text = (
        f"🆘 <b>ВОПРОС В ПОДДЕРЖКУ</b>\n"
        f"От: ID <code>{message.from_user.id}</code> {user_link}\n\n"
    )

    full_text_msg = f"{header_text}Текст:\n{user_text}" if user_text else header_text + "Текст: (только медиа)"

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="💬 Ответить пользователю", callback_data=f"reply_{message.from_user.id}")
        ]]
    )

    sent_messages_info = []

    for admin_id in admin_ids_set:
        try:
            if album:
                media_group = MediaGroupBuilder()
                for msg in album:
                    if msg.photo:
                        media_group.add_photo(media=msg.photo[-1].file_id)
                    elif msg.document:
                        media_group.add_document(media=msg.document.file_id)
                    elif msg.video:
                        media_group.add_video(media=msg.video.file_id)

                await bot.send_media_group(chat_id=admin_id, media=media_group.build())

                sent_msg = await bot.send_message(
                    chat_id=admin_id,
                    text=full_text_msg,
                    parse_mode="HTML",
                    reply_markup=kb
                )

                sent_messages_info.append((admin_id, sent_msg.message_id))

            elif message.photo or message.document:
                common_params = {
                    "chat_id": admin_id,
                    "caption": full_text_msg,
                    "parse_mode": "HTML",
                    "reply_markup": kb
                }

                if message.photo:
                    sent_msg = await bot.send_photo(
                        photo=message.photo[-1].file_id,
                        **common_params
                    )
                else:
                    sent_msg = await bot.send_document(
                        document=message.document.file_id,
                        **common_params
                    )

                sent_messages_info.append((admin_id, sent_msg.message_id))

            else:
                sent_msg = await bot.send_message(
                    chat_id=admin_id,
                    text=full_text_msg,
                    parse_mode="HTML",
                    reply_markup=kb
                )
                sent_messages_info.append((admin_id, sent_msg.message_id))

        except Exception as e:
            print(f"Ошибка при отправке админу {admin_id}: {e}")

    if sent_messages_info:
        if message.from_user.id not in active_alerts:
            active_alerts[message.from_user.id] = []
        active_alerts[message.from_user.id].append(sent_messages_info)

    if "last_bot_msg_id" in data:
        await try_delete(bot, message.chat.id, data["last_bot_msg_id"])

    if album:
        for msg in album:
            await try_delete(bot, message.chat.id, msg.message_id)
    else:
        await try_delete(bot, message.chat.id, message.message_id)

    await state.clear()
    await message.answer("Сообщение отправлено. Ожидайте ответа.", reply_markup=get_main_kb(message.from_user.id))
