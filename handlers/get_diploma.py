"""Выдача дипломов/сертификатов через опрос."""
import os
import sys
import time

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
from sqlalchemy import select, update

from config import (
    DiplomaSurvey,
    bot,
    try_delete,
    RESTRICTED_MODE,
    admin_ids_set,
    ARCHITECT_ID
)
from keyboards import (
    get_cancel_kb,
    get_main_kb,
    get_olymp_source_kb,
    get_enroll_intent_kb
)
from models import User, async_session

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

diploma_router = Router()

DIPLOMAS_DIR = "Diplomas"
COOLDOWN_SECONDS = 1800


@diploma_router.message(F.text == "🎓 Получить диплом/сертификат")
async def start_diploma_survey(message: types.Message, state: FSMContext):
    """Старт получения диплома (с защитой от DDOS в RAM)."""

    if not RESTRICTED_MODE:
        if message.from_user.id not in admin_ids_set and message.from_user.id != ARCHITECT_ID:
            await message.answer(
                "⛔ Эта функция сейчас недоступна.",
                reply_markup=get_main_kb(message.from_user.id)
            )
            return

    data = await state.get_data()
    next_attempt = data.get("diploma_next_attempt", 0)
    current_time = time.time()

    if current_time < next_attempt:
        remaining_minutes = int((next_attempt - current_time) / 60) + 1
        await try_delete(bot, message.chat.id, message.message_id)

        if "diploma_limit_msg_id" in data:
            await try_delete(bot, message.chat.id, data["diploma_limit_msg_id"])

        msg = await message.answer(
            f"⏳ <b>Лимит запросов.</b>\n"
            f"Скачать диплом повторно можно через {remaining_minutes} мин.",
            parse_mode="HTML"
        )
        await state.update_data(diploma_limit_msg_id=msg.message_id)
        return

    if not os.path.exists(DIPLOMAS_DIR):
        return

    user_file_path = os.path.join(DIPLOMAS_DIR, f"{message.from_user.id}.pdf")
    if not os.path.exists(user_file_path):
        await message.answer(
            "😔 К сожалению, ваш диплом/сертификат не найден.\n"
            "Возможно, он еще не готов или вы не участвовали в олимпиаде."
        )
        return

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar()

    if not user:
        await message.answer("Ошибка: пользователь не найден в базе.")
        return

    if user.impressions:
        await send_diploma_file(message, user.telegram_id, state)
        return

    await state.set_state(DiplomaSurvey.impressions)
    await try_delete(bot, message.chat.id, message.message_id)

    await message.answer(
        "Чтобы получить документ, ответьте на несколько вопросов.\n\n"
        "1️⃣ <b>Понравилась ли Вам олимпиада? Расскажите о своих впечатлениях.</b>\n"
        "(Ответьте текстовым сообщением)",
        parse_mode="HTML",
        reply_markup=get_cancel_kb()
    )


@diploma_router.message(DiplomaSurvey.impressions)
async def process_impressions(message: types.Message, state: FSMContext):
    if not message.text or message.text in ["🏠 На главную"]:
        if not message.text:
            await message.answer("Пожалуйста, пришлите текстовый ответ.")
        return

    await state.update_data(impressions=message.text)

    await state.set_state(DiplomaSurvey.olymp_source)
    await message.answer(
        "2️⃣ <b>Из каких источников узнали об олимпиаде?</b>",
        parse_mode="HTML",
        reply_markup=get_olymp_source_kb()
    )


@diploma_router.callback_query(DiplomaSurvey.olymp_source, F.data.startswith("source_"))
async def process_source_buttons(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора источника."""

    choice = callback.data
    source_text = ""

    if choice == "source_other":
        await state.set_state(DiplomaSurvey.olymp_source_text)
        await callback.message.edit_text(
            "✏️ <b>Напишите, откуда вы узнали об олимпиаде:</b>",
            parse_mode="HTML",
            reply_markup=None
        )
        await callback.answer()
        return

    sources_map = {
        "source_school": "Из школы",
        "source_vka": "Из Telegram-канала ВКА",
        "source_1t": "Из Telegram-канала 1Т Старт",
        "source_friends": "От знакомых",
        "source_previous": "Участвовал ранее"
    }
    source_text = sources_map.get(choice, "Неизвестно")

    await state.update_data(olymp_source=source_text)

    await ask_enrollment_question(callback.message, state)
    await callback.answer()


@diploma_router.message(DiplomaSurvey.olymp_source_text)
async def process_source_custom_text(message: types.Message, state: FSMContext):
    if not message.text:
        await message.answer("Пожалуйста, пришлите текстовый ответ.")
        return

    await state.update_data(olymp_source=f"Другое: {message.text}")
    await ask_enrollment_question(message, state)


async def ask_enrollment_question(message_obj: types.Message, state: FSMContext):
    """Вспомогательная функция для перехода к 3 вопросу."""
    await state.set_state(DiplomaSurvey.desire_to_enroll)

    await message_obj.answer(
        "3️⃣ <b>Планируете ли Вы поступать в ВКА им. А.Ф.Можайского?</b>",
        parse_mode="HTML",
        reply_markup=get_enroll_intent_kb()
    )


@diploma_router.callback_query(DiplomaSurvey.desire_to_enroll, F.data.startswith("enroll_"))
async def finish_survey_and_send_file(callback: types.CallbackQuery, state: FSMContext):
    """Финал: сохраняем ответы в БД, отправляем файл."""

    enroll_map = {
        "enroll_6": "Планирую на 6 факультет",
        "enroll_other": "Планирую на другой факультет",
        "enroll_no": "Не планирую"
    }
    choice_text = enroll_map.get(callback.data, "Неизвестно")

    data = await state.get_data()

    try:
        async with async_session() as session:
            stmt = update(User).where(User.telegram_id == callback.from_user.id).values(
                impressions=data.get("impressions"),
                olymp_source=data.get("olymp_source"),
                desire_to_enroll=choice_text
            )
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        print(f"Error saving survey: {e}")

    # await try_delete(bot, callback.message.chat.id, callback.message.message_id)

    user_file_path = os.path.join(DIPLOMAS_DIR, f"{callback.from_user.id}.pdf")
    try:
        file_to_send = FSInputFile(user_file_path)
        await callback.message.answer_document(
            file_to_send,
            caption="🎉 <b>Поздравляем!</b>\nСпасибо за участие!",
            parse_mode="HTML",
            reply_markup=get_main_kb(callback.from_user.id)
        )
    except Exception:
        await callback.message.answer("⚠️ Ошибка отправки файла.", reply_markup=get_main_kb(callback.from_user.id))

    await state.clear()

    current_time = time.time()
    await state.update_data(diploma_next_attempt=current_time + COOLDOWN_SECONDS)

    await callback.answer()


async def send_diploma_file(message: types.Message, user_id: int, state: FSMContext):
    """Отправка файла без опроса (для повторных скачиваний)."""

    user_file_path = os.path.join(DIPLOMAS_DIR, f"{user_id}.pdf")
    try:
        file_to_send = FSInputFile(user_file_path)
        await message.answer_document(
            file_to_send,
            caption="🎉 <b>Ваш диплом/сертификат.</b>",
            parse_mode="HTML",
            reply_markup=get_main_kb(user_id)
        )

        current_time = time.time()
        await state.update_data(diploma_next_attempt=current_time + COOLDOWN_SECONDS)

    except Exception:
        await message.answer("⚠️ Ошибка при отправке файла.")
