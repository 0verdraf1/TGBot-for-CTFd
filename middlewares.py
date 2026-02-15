"""Посредники."""
import asyncio
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from config import active_dialogs, banned_ids, RESTRICTED_MODE, admin_ids_set, ARCHITECT_ID
from keyboards import get_banned_kb, get_main_kb


BLOCKED_BUTTONS = [
    "📝 Зарегистрироваться",
    "🔐 Получить логин и пароль",
    "🔔 Связь с организаторами",
    "🦾 Админ-панель",
    "🏠 На главную",
    "👀 Сообщить о нарушении правил",
    "🆘 У меня проблема"
]


class BanMiddleware(BaseMiddleware):
    """Блокирует доступ забаненным пользователям."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        if user.id in banned_ids:

            if user.id in active_dialogs:

                if isinstance(event, CallbackQuery):
                    await event.answer(
                        "⛔ Вы забанены и находитесь в диалоге с организатором.",
                        show_alert=True
                    )
                    return

                if isinstance(event, Message) and event.text in BLOCKED_BUTTONS:
                    await event.answer(
                        "⛔ Вы забанены и находитесь в диалоге с организатором."
                    )
                    return

                return await handler(event, data)

            if isinstance(event, CallbackQuery):
                if event.data == "banned_appeal":
                    return await handler(event, data)
                else:
                    await event.answer("⛔ Вы забанены.", show_alert=True)
                    return

            if isinstance(event, Message):
                await event.answer(
                    "⛔ <b>Вы забанены.</b>\n"
                    "Вы не можете использовать бота.",
                    parse_mode="HTML",
                    reply_markup=get_banned_kb()
                )
                return

        return await handler(event, data)


class AccessMiddleware(BaseMiddleware):
    """
    Ограничивает функционал для не-админов, если включен RESTRICTED_MODE.
    Оставляет только: /start, Связь с оргнизаторами, Репорты.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        if not RESTRICTED_MODE:
            return await handler(event, data)

        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)

        if user.id in admin_ids_set or user.id == ARCHITECT_ID:
            return await handler(event, data)

        allowed_texts = [
            "🔔 Связь с организаторами",
            "👀 Сообщить о нарушении правил",
            "🆘 У меня проблема",
            "🏠 На главную",
            "🎓 Получить диплом/сертификат"
        ]

        if isinstance(event, Message):
            state = data.get("state")
            current_state = await state.get_state() if state else None

            if current_state and (
                current_state.startswith("Report:") or
                current_state.startswith("Support:") or
                current_state.startswith("UserState:") or
                current_state.startswith("DiplomaSurvey:")
            ):
                return await handler(event, data)

            msg_text = event.text or ""

            if msg_text.startswith("/start"):
                return await handler(event, data)

            if msg_text and msg_text not in allowed_texts:
                await event.answer(
                    "⛔ В данный момент эта функция отключена.",
                    reply_markup=get_main_kb(user.id)
                )
                return

        if isinstance(event, CallbackQuery):
            if (
                event.data in ["contact_support", "report_violation"]
                or event.data.startswith("reply_")
                or event.data.startswith("enroll_")
            ):
                return await handler(event, data)

            await event.answer("Функция недоступна.", show_alert=True)
            return

        return await handler(event, data)


class MediaGroupMiddleware(BaseMiddleware):
    """Собирает медиа в альбом для отправки группой."""

    def __init__(self, latency: float = 0.5):
        self.latency = latency
        self.album_data: Dict[str, List[Message]] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:

        if not isinstance(event, Message):
            return await handler(event, data)

        if not event.media_group_id:
            return await handler(event, data)

        media_group_id = event.media_group_id

        if media_group_id not in self.album_data:
            self.album_data[media_group_id] = [event]
            await asyncio.sleep(self.latency)

            album = self.album_data.pop(media_group_id)
            data["album"] = album

            return await handler(event, data)

        self.album_data[media_group_id].append(event)
        return
