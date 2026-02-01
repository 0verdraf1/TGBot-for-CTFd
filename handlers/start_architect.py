"""Панель Архитектора: управление админами и рассылка кредов."""
import asyncio
import os
import sys

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, update

from config import ARCHITECT_ID, ArchitectState, admin_ids_set, bot
from keyboards import get_architect_kb, get_main_kb, get_search_method_kb
from models import User, CTFdUser, async_session

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

architect_router = Router()


@architect_router.message(F.text == "🛜 Панель Архитектора")
async def open_architect_panel(message: types.Message, state: FSMContext):
    """Вход в панель."""

    if message.from_user.id != ARCHITECT_ID:
        return
    await state.clear()
    await message.answer(
        "Добро пожаловать, Создатель.", reply_markup=get_architect_kb()
    )


@architect_router.message(F.text == "➕ Назначить админа")
async def start_promote(message: types.Message, state: FSMContext):
    """Выбор способа поиска будущего админа."""

    if message.from_user.id != ARCHITECT_ID:
        return
    await message.answer(
        "Как найти будущего админа?", reply_markup=get_search_method_kb()
    )
    await state.set_state(ArchitectState.waiting_for_promote_search_method)


@architect_router.callback_query(ArchitectState.waiting_for_promote_search_method)
async def promote_method_chosen(callback: types.CallbackQuery, state: FSMContext):
    """Поиск по id."""

    if callback.data == "search_by_id":
        await state.set_state(ArchitectState.waiting_for_promote_user_id)
        await callback.message.edit_text("Введите ID пользователя:")
    else:
        await state.set_state(ArchitectState.waiting_for_promote_username)
        await callback.message.edit_text("Введите @username пользователя:")
    await callback.answer()


@architect_router.message(ArchitectState.waiting_for_promote_user_id)
async def process_promote_id(message: types.Message, state: FSMContext):
    """Проверка id."""

    if not message.text.isdigit():
        await message.answer("ID должен быть числом.")
        return
    await process_promote_final(message, state, user_id=int(message.text))


@architect_router.message(ArchitectState.waiting_for_promote_username)
async def process_promote_username(message: types.Message, state: FSMContext):
    """Поиск по username."""

    if not message.text.startswith("@"):
        await message.answer("Нужен @username.")
        return
    username = message.text.strip().replace("@", "")
    await process_promote_final(message, state, username=username)


async def process_promote_final(
    message: types.Message, state: FSMContext, user_id=None, username=None
):
    async with async_session() as session:
        """Окончание процесса назначения админа."""

        query = select(User)
        if user_id:
            query = query.where(User.telegram_id == user_id)
        else:
            query = query.where(User.username == username)
        user = (await session.execute(query)).scalar()

        if not user:
            await message.answer("Пользователь не найден.")
            return

        if user.is_admin:
            await message.answer("Этот пользователь уже админ.")
            await state.clear()
            return

        user.is_admin = True

        stmt_ctfd = update(CTFdUser).where(CTFdUser.email == user.email).values(
            type="admin",
            hidden=True,
            verified=False
        )
        await session.execute(stmt_ctfd)

        await session.commit()

        admin_ids_set.add(user.telegram_id)

    await message.answer(
        f"✅ Пользователь {user.full_name} назначен АДМИНОМ.",
        reply_markup=get_architect_kb(),
    )

    try:
        await bot.send_message(
            user.telegram_id,
            "ℹ️ <b>Вам выданы права Администратора.</b>\nВ меню появилась кнопка 'Админ-панель'.",
            parse_mode="HTML",
            reply_markup=get_main_kb(user.telegram_id),
        )
    except Exception:
        pass

    await state.clear()


@architect_router.message(F.text == "➖ Снять админа")
async def start_demote(message: types.Message, state: FSMContext):
    """Старт процесса снятия админа."""

    if message.from_user.id != ARCHITECT_ID:
        return
    await message.answer(
        "Как найти админа для снятия?", reply_markup=get_search_method_kb()
    )
    await state.set_state(ArchitectState.waiting_for_demote_search_method)


@architect_router.callback_query(ArchitectState.waiting_for_demote_search_method)
async def demote_method_chosen(callback: types.CallbackQuery, state: FSMContext):
    """Старт процесса снятия админа."""

    if callback.data == "search_by_id":
        await state.set_state(ArchitectState.waiting_for_demote_user_id)
        await callback.message.edit_text("Введите ID админа:")
    else:
        await state.set_state(ArchitectState.waiting_for_demote_username)
        await callback.message.edit_text("Введите @username админа:")
    await callback.answer()


@architect_router.message(ArchitectState.waiting_for_demote_user_id)
async def process_demote_id(message: types.Message, state: FSMContext):
    """Поиск по id."""

    if not message.text.isdigit():
        await message.answer("ID должен быть числом.")
        return
    await process_demote_final(message, state, user_id=int(message.text))


@architect_router.message(ArchitectState.waiting_for_demote_username)
async def process_demote_username(message: types.Message, state: FSMContext):
    """Поиск по username."""

    if not message.text.startswith("@"):
        await message.answer("Нужен @username.")
        return
    username = message.text.strip().replace("@", "")
    await process_demote_final(message, state, username=username)


async def process_demote_final(
    message: types.Message, state: FSMContext, user_id=None, username=None
):
    async with async_session() as session:
        """Окончание процесса снятия админа."""

        query = select(User)
        if user_id:
            query = query.where(User.telegram_id == user_id)
        else:
            query = query.where(User.username == username)
        user = (await session.execute(query)).scalar()

        if not user:
            await message.answer("Пользователь не найден.")
            return

        if not user.is_admin:
            await message.answer("Этот пользователь не является админом.")
            await state.clear()
            return

        user.is_admin = False
        stmt_ctfd = update(CTFdUser).where(CTFdUser.email == user.email).values(
            type="user",
            hidden=False,
            verified=True
        )
        await session.execute(stmt_ctfd)

        await session.commit()

        if user.telegram_id in admin_ids_set:
            admin_ids_set.remove(user.telegram_id)

    await message.answer(
        f"✅ Пользователь {user.full_name} разжалован (права сняты).",
        reply_markup=get_architect_kb(),
    )

    try:
        await bot.send_message(
            user.telegram_id,
            "ℹ️ <b>Ваши права Администратора отозваны.</b>",
            parse_mode="HTML",
            reply_markup=get_main_kb(user.telegram_id),
        )
    except Exception:
        pass

    await state.clear()


@architect_router.message(F.text == "📨 Разослать креды")
async def broadcast_creds(message: types.Message):
    """
    Рассылка данных для входа.
    Забаненным пользователям данные НЕ отправляются.
    """

    if message.from_user.id != ARCHITECT_ID:
        return

    msg = await message.answer("⏳ Начинаю массовую рассылку логинов и паролей...")

    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_banned == False))
        users = result.scalars().all()

    count = 0
    for user in users:
        try:
            creds_text = (
                f"⏰ Олимпиада началась! ⏰\n\n"
                f"Ваши данные для входа:\n"
                f"🎩 Логин: `{user.login_id}`\n"
                f"🔑 Пароль: `{user.plain_password}`"
                f"🌐 Задания здесь: <ссылка на борду>\n\n"
                f"Используйте эти данные для входа на сайт по ссылке выше!"
            )
            await bot.send_message(user.telegram_id, creds_text, parse_mode="Markdown")
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await message.answer(
        f"✅ Рассылка завершена. Отправлено: {count} пользователям.",
        reply_markup=get_architect_kb(),
    )
    await msg.delete()
