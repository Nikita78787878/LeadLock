"""Reply-клавиатуры для бота."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def get_cancel_kb() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )