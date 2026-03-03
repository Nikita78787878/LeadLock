"""Вспомогательные функции для админ-хендлеров."""

from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from .menu import show_admin_menu


async def cancel_edit(message: Message, state: FSMContext) -> None:
    """Отменить редактирование и вернуть в главное меню."""
    await state.clear()
    await message.answer("❌ Редактирование отменено", reply_markup=ReplyKeyboardRemove())
    await show_admin_menu(message)