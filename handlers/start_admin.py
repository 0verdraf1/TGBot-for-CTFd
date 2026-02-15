"""Реакции на кнопки Админ-панели и Назад в меню."""
from datetime import datetime
import os
import sys

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import openpyxl
from sqlalchemy import select

from config import admin_ids_set
from keyboards import get_admin_panel_kb, get_main_kb
from models import User, async_session

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


start_admin = Router()


@start_admin.message(F.text == "🦾 Админ-панель")
async def open_admin_panel(message: types.Message, state: FSMContext):
    """Админ-панель."""

    if message.from_user.id not in admin_ids_set:
        return

    await state.clear()

    await message.answer("🦾 Админ-панель открыта.", reply_markup=get_admin_panel_kb())


@start_admin.message(F.text == "📊 Выгрузить результаты")
async def export_results(message: types.Message):
    """Генерация и отправка Excel-файла с результатами."""

    if message.from_user.id not in admin_ids_set:
        return

    msg = await message.answer("⏳ Формирую таблицу, пожалуйста подождите...")

    try:
        async with async_session() as session:
            result = await session.execute(
                select(User).order_by(User.points.desc(), User.full_name)
            )
            users = result.scalars().all()

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Результаты"

        headers = [
            "ID в БД",
            "Telegram ID",
            "Username",
            "ФИО",
            "Очки (Points)",
            "Телефон",
            "Населенный пункт",
            "Учебное заведение",
            "Класс/Курс",
            "Email",
            "Логин",
            "Пароль",
            "Статус бана",
            "Впечатления",
            "Откуда узнали",
            "Планирует поступать"
        ]
        ws.append(headers)

        for user in users:
            row = [
                user.id,
                user.telegram_id,
                f"@{user.username}" if user.username else "Нет",
                user.full_name,
                user.points,
                user.phone,
                user.place_of_study,
                user.school,
                user.grade,
                user.email,
                user.login_id,
                user.plain_password,
                "ЗАБАНЕН" if user.is_banned else "-",
                user.impressions,
                user.olymp_source,
                user.desire_to_enroll
            ]
            ws.append(row)

        for col_num, column_title in enumerate(headers, 1):
            letter = openpyxl.utils.get_column_letter(col_num)
            ws.column_dimensions[letter].width = 25

        filename = f"users_export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.xlsx"
        wb.save(filename)

        file_to_send = FSInputFile(filename)
        await message.answer_document(
            file_to_send,
            caption=f"📊 Выгрузка результатов.\nВсего участников: {len(users)}"
        )

        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при создании таблицы: {e}")
        print(f"Export Error: {e}")


@start_admin.message(F.text == "⬅️ Назад в меню")
async def exit_admin(message: types.Message, state: FSMContext):
    """Назад в меню."""

    await state.clear()
    await message.answer("Вышли в главное меню.", reply_markup=get_main_kb(message.from_user.id))
