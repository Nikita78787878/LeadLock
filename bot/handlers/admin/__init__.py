"""Админ-панель."""

from aiogram import Router

from .menu import router as menu_router
from .faq import router as faq_router
from .leads import router as leads_router
from .settings import router as settings_router

router = Router(name="admin")
router.include_router(menu_router)
router.include_router(faq_router)
router.include_router(leads_router)
router.include_router(settings_router)

__all__ = ["router"]
