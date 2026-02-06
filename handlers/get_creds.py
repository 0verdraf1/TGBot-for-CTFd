"""Запрос участником кредов."""
import os
import sys
import time

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from config import bot, try_delete
from models import User, async_session

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


get_creds = Router()


@get_creds.message(F.text == "🔐 Получить логин и пароль")
async def get_user_creds(message: types.Message, state: FSMContext):

    await try_delete(bot, message.chat.id, message.message_id)

    data = await state.get_data()
    current_time = time.time()

    last_click = data.get("last_creds_click", 0)
    if current_time - last_click < 30.0:
        return
    await state.update_data(last_creds_click=current_time)

    cached_login = data.get("cached_login")
    cached_pwd = data.get("cached_pwd")

    if cached_login and cached_pwd:
        if "last_creds_msg_id" in data:
            await try_delete(bot, message.chat.id, data["last_creds_msg_id"])

        msg = await message.answer(
            f"🚀 <b>Ваши данные для входа:</b>\n\n"
            f"👤 Логин: <code>{cached_login}</code>\n"
            f"🔑 Пароль: <code>{cached_pwd}</code>",
            parse_mode="HTML"
        )
        await state.update_data(last_creds_msg_id=msg.message_id)
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar()

        if not user:
            if "last_creds_msg_id" in data:
                await try_delete(bot, message.chat.id, data["last_creds_msg_id"])

            msg = await message.answer("❌ Вы еще не зарегистрированы!")
            await state.update_data(last_creds_msg_id=msg.message_id)
            return

        await state.update_data(
            cached_login=user.login_id,
            cached_pwd=user.plain_password
        )

        if "last_creds_msg_id" in data:
            await try_delete(bot, message.chat.id, data["last_creds_msg_id"])

        msg = await message.answer(
            f"🚀 <b>Ваши данные для входа:</b>\n\n"
            f"👤 Логин: <code>{user.login_id}</code>\n"
            f"🔑 Пароль: <code>{user.plain_password}</code>",
            parse_mode="HTML"
        )
        await state.update_data(last_creds_msg_id=msg.message_id)
