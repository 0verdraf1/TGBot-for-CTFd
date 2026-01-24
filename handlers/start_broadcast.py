"""Рассылка сообщений участникам."""
import asyncio
import os
import sys
from typing import List

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.utils.media_group import MediaGroupBuilder
from sqlalchemy import select

from config import AdminPanel, admin_ids_set, bot
from keyboards import get_admin_panel_kb
from models import User, async_session

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


broad = Router()


@broad.message(F.text == "📢 Разослать всем")
async def start_broadcast(message: types.Message, state: FSMContext):
    """Реакция на нажатие кнопки и ввод сообщения."""

    if message.from_user.id not in admin_ids_set:
        return
    await state.set_state(AdminPanel.waiting_for_broadcast_content)
    await message.answer(
        "Отправьте сообщение (текст, фото, альбом, файл), которое "
        "нужно разослать всем участникам.",
        reply_markup=types.ReplyKeyboardRemove(),
    )


@broad.message(AdminPanel.waiting_for_broadcast_content)
async def process_broadcast(
    message: types.Message,
    state: FSMContext,
    album: List[types.Message] = None
):
    """
    Начало рассылки сообщений участникам.
    Забанненым пользователям рассылка не происходит.
    """

    async with async_session() as session:
        users_result = await session.execute(
            select(User.telegram_id).where(User.is_banned is False)
            )
        users_ids = users_result.scalars().all()

    count = 0
    await message.answer(f"⏳ Начинаю рассылку на {len(users_ids)} пользователей...")
    is_album = False

    if album:
        is_album = True
        builder = MediaGroupBuilder()
        for element in album:
            if element.photo:
                builder.add_photo(
                    media=element.photo[-1].file_id,
                    caption=element.caption,
                    caption_entities=element.caption_entities
                )
            elif element.video:
                builder.add_video(
                    media=element.video.file_id,
                    caption=element.caption,
                    caption_entities=element.caption_entities
                )
            elif element.document:
                builder.add_document(
                    media=element.document.file_id,
                    caption=element.caption,
                    caption_entities=element.caption_entities
                )
            elif element.audio:
                builder.add_audio(
                    media=element.audio.file_id,
                    caption=element.caption,
                    caption_entities=element.caption_entities
                )

        album_data = []
        for element in album:
            if element.photo:
                album_data.append(('photo', element.photo[-1].file_id, element.caption, element.caption_entities))
            elif element.video:
                album_data.append(('video', element.video.file_id, element.caption, element.caption_entities))
            elif element.document:
                album_data.append(('document', element.document.file_id, element.caption, element.caption_entities))

    for user_id in users_ids:
        try:
            if is_album:
                mb = MediaGroupBuilder()
                for m_type, m_id, m_cap, m_ents in album_data:
                    if m_type == 'photo':
                        mb.add_photo(m_id, caption=m_cap, caption_entities=m_ents)
                    elif m_type == 'video':
                        mb.add_video(m_id, caption=m_cap, caption_entities=m_ents)
                    elif m_type == 'document':
                        mb.add_document(m_id, caption=m_cap, caption_entities=m_ents)

                await bot.send_media_group(chat_id=user_id, media=mb.build())

            else:
                await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                )

            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(
        f"✅ Рассылка завершена. Отправлено пользователям: {count}",
        reply_markup=get_admin_panel_kb(),
    )
    await state.clear()
