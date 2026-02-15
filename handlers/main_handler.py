"""Сбор всех роутеров в один."""
from aiogram import Router

from .admin_ban import admin_ban_router
from .admin_reply import router_reply
from .admin_to_user import admin_to_user
from .call_organizer import call
from .common import common_router
from .get_creds import get_creds
from .registration import registration
from .search_dialog import search
from .start_admin import start_admin
from .start_architect import architect_router
from .start_broadcast import broad
from .type_call.help import user_help
from .type_call.report import user_rep
from .user_ban_appeal import ban_appeal_router
from .user_to_admin import user_to_admin
from .get_diploma import diploma_router


router = Router()

# 1. Выход, Бан, Апелляция
router.include_router(common_router)
router.include_router(ban_appeal_router)
router.include_router(admin_ban_router)
router.include_router(architect_router)

# 2. Диалоги
router.include_router(admin_to_user)
router.include_router(user_to_admin)
router.include_router(router_reply)

# 3. Основной функционал
router.include_router(call)
router.include_router(get_creds)
router.include_router(diploma_router)
router.include_router(registration)
router.include_router(search)
router.include_router(start_admin)
router.include_router(broad)
router.include_router(user_rep)
router.include_router(user_help)
