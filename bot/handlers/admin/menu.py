"""Хендлеры главного меню админ-панели."""

import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = structlog.get_logger()

router = Router(name="admin_menu")


async def show_admin_menu(message: Message) -> None:
    """
    Отобразить главное меню админ-панели.

    Args:
        message: Message для отправки или редактирования
    """
    builder = InlineKeyboardBuilder()

    # Кнопка управления FAQ
    builder.button(
        text="📝 Управление FAQ",
        callback_data="admin:faq",
    )
    builder.button(
        text="📊 Последние заявки",
        callback_data="admin:leads",
    )
    builder.button(
        text="⚙️ Настройки",
        callback_data="admin:settings",
    )

    # По одной кнопке в строке
    builder.adjust(1)

    text = "⚙️ Панель администратора"

    # Пытаемся отредактировать или отправить новое сообщение
    try:
        await message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
        )
    except Exception:
        await message.answer(
            text=text,
            reply_markup=builder.as_markup(),
        )


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    """
    Обработчик команды /admin.

    Отображает главное меню админ-панели.

    Args:
        message: Сообщение от администратора
    """
    user_id = message.from_user.id

    await logger.ainfo(
        "Администратор открыл панель",
        user_id=user_id,
    )

    await show_admin_menu(message)


@router.callback_query(F.data == "admin:main")
async def handle_admin_main(callback: CallbackQuery) -> None:
    """
    Обработчик возврата в главное меню админ-панели.

    Args:
        callback: Callback query от администратора
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор вернулся в главное меню",
        user_id=user_id,
    )

    try:
        await show_admin_menu(callback.message)
        await callback.answer()
    except Exception as e:
        await logger.aerror(
            "Ошибка при возврате в главное меню",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )
