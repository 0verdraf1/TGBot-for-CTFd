import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv


load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")

env_admin_ids_str = os.getenv("ENV_ADMIN_IDS", "")
ENV_ADMIN_IDS = [int(id) for id in env_admin_ids_str.split()] if env_admin_ids_str else []

architect_id_str = os.getenv("ARCHITECT_ID", "")
ARCHITECT_ID = int(architect_id_str) if architect_id_str else 0

RESTRICTED_MODE = False

DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

active_alerts: dict[int, list[list[tuple[int, int]]]] = {}
active_dialogs: dict[int, int] = {}

banned_ids: set[int] = set()

admin_ids_set: set[int] = set(ENV_ADMIN_IDS)
if ARCHITECT_ID:
    admin_ids_set.add(ARCHITECT_ID)

GRADES = [f"{i} класс" for i in range(8, 12)] + [f"{i} курс" for i in range(1, 5)]


class Registration(StatesGroup):
    """Состояния для регистрации."""

    full_name = State()
    phone = State()
    place_of_study = State()
    school = State()
    grade = State()
    email = State()
    waiting_for_agreement = State()
    confirm = State()


class Report(StatesGroup):
    """Состояния для репортов (сообщений о нарушениях)."""

    offender_username = State()
    description = State()
    proof = State()
    last_bot_msg_id = State()


class Support(StatesGroup):
    """Состояния для обращения по поводу бана."""

    waiting_for_message = State()
    last_bot_msg_id = State()


class AdminPanel(StatesGroup):
    """Состояния для админ панели."""

    waiting_for_broadcast_content = State()
    waiting_for_user_search = State()
    waiting_for_user_id = State()
    in_dialog = State()


class AdminBanSystem(StatesGroup):
    """Состояния для системы бана/разбана."""

    waiting_for_ban_search_method = State()
    waiting_for_ban_user_id = State()
    waiting_for_ban_username = State()
    waiting_for_ban_reason = State()
    waiting_for_ban_proof = State()

    waiting_for_unban_search_method = State()
    waiting_for_unban_user_id = State()
    waiting_for_unban_username = State()


class AdminState(StatesGroup):
    """Состояние для админа."""

    waiting_for_reply = State()


class ArchitectState(StatesGroup):
    """Состояние для архитектора."""

    waiting_for_promote_search_method = State()
    waiting_for_promote_user_id = State()
    waiting_for_promote_username = State()

    waiting_for_demote_search_method = State()
    waiting_for_demote_user_id = State()
    waiting_for_demote_username = State()


class UserState(StatesGroup):
    in_dialog_with_admin = State()


async def try_delete(bot: Bot, chat_id: int, message_id: int):
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass
