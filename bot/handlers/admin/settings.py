"""Хендлеры управления настройками бота."""

import structlog
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.config_service import ConfigService
from bot.states.admin_states import ConfigEdit
from .helpers import cancel_edit
from .menu import show_admin_menu
from ...keyboards.reply import get_cancel_kb

logger = structlog.get_logger()

router = Router(name="admin_settings")


@router.callback_query(F.data == "admin:settings")
async def handle_admin_settings(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик открытия раздела настроек.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор открыл настройки",
        user_id=user_id,
    )

    try:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✏️ Приветственный текст",
            callback_data="admin:settings:welcome",
        )
        builder.button(
            text="📞 Контакты",
            callback_data="admin:settings:contacts",
        )
        builder.button(
            text="📍 Где мы находимся",
            callback_data="admin:settings:location",
        )
        builder.button(
            text="🗺 Ссылка на карту",
            callback_data="admin:settings:maps_url",
        )
        builder.button(
            text="⬅️ Назад",
            callback_data="admin:main",
        )
        builder.adjust(1)

        await callback.message.edit_text(
            text="⚙️ Настройки бота",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при отображении настроек",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data == "admin:settings:welcome")
async def handle_settings_welcome(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик редактирования приветственного текста.

    Args:
        callback: Callback query от администратора
        state: Состояние FSM
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор начал редактирование приветственного текста",
        user_id=user_id,
    )

    try:
        # Получаем текущий текст
        config_service = ConfigService(session)
        current_text = await config_service.get_welcome_text()

        # Переходим к ожиданию нового текста
        await state.set_state(ConfigEdit.waiting_for_welcome)

        await callback.message.edit_text(
            text=(
                f"Текущий текст (нажмите чтобы скопировать):\n\n"
                f"<code>{current_text}</code>\n\n"
                f"Введите новый текст или нажмите Отмена\n\n"
                f"💡 Используйте <code>{{name}}</code> для имени пользователя"
            ),
            parse_mode="HTML",
        )
        await callback.message.answer("👇", reply_markup=get_cancel_kb())

    except Exception as e:
        await logger.aerror(
            "Ошибка при редактировании приветственного текста",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data == "admin:settings:contacts")
async def handle_settings_contacts(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик редактирования контактов.

    Args:
        callback: Callback query от администратора
        state: Состояние FSM
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор начал редактирование контактов",
        user_id=user_id,
    )

    try:
        # Получаем текущие контакты
        config_service = ConfigService(session)
        current_contacts = await config_service.get_contacts()

        # Переходим к ожиданию новых контактов
        await state.set_state(ConfigEdit.waiting_for_contacts)

        await callback.message.edit_text(
            text=(
                f"Текущие контакты (нажмите чтобы скопировать):\n\n"
                f"<code>{current_contacts}</code>\n\n"
                f"Введите новые контакты или нажмите Отмена:"
            ),
            parse_mode="HTML",
        )
        await callback.message.answer("👇", reply_markup=get_cancel_kb())

    except Exception as e:
        await logger.aerror(
            "Ошибка при редактировании контактов",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data == "admin:settings:location")
async def handle_settings_location(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик редактирования блока 'Где мы находимся'.
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор начал редактирование блока 'Где мы находимся'",
        user_id=user_id,
    )

    try:
        config_service = ConfigService(session)
        current_location = await config_service.get_config_value("location")

        await state.set_state(ConfigEdit.waiting_for_location)

        await callback.message.edit_text(
            text=(
                f"Текущий адрес (нажмите чтобы скопировать):\n\n"
                f"<code>{current_location or 'Не задано'}</code>\n\n"
                f"Введите новый адрес или нажмите Отмена:"
            ),
            parse_mode="HTML",
        )
        await callback.message.answer("👇", reply_markup=get_cancel_kb())

    except Exception as e:
        await logger.aerror(
            "Ошибка при открытии редактирования местоположения",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.message(ConfigEdit.waiting_for_welcome)
async def handle_config_welcome_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик ввода нового приветственного текста.

    Args:
        message: Сообщение с текстом
        state: Состояние FSM
        session: Сессия БД
    """
    if message.text == "❌ Отмена":
        await cancel_edit(message, state)
        return

    user_id = message.from_user.id
    new_text = message.text

    await logger.ainfo(
        "Администратор ввёл новый приветственный текст",
        user_id=user_id,
        text_length=len(new_text),
    )

    try:
        # Сохраняем новый текст
        config_service = ConfigService(session)
        await config_service.set_value("welcome_text", new_text)
        await session.commit()

        # Очищаем состояние
        await state.clear()

        await logger.ainfo(
            "Приветственный текст обновлён",
            user_id=user_id,
        )

        await message.answer(
            text="✅ Приветственный текст обновлён",
        )

        # Возвращаем в главное меню
        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при сохранении приветственного текста",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()


@router.message(ConfigEdit.waiting_for_contacts)
async def handle_config_contacts_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик ввода новых контактов.

    Args:
        message: Сообщение с контактами
        state: Состояние FSM
        session: Сессия БД
    """

    if message.text == "❌ Отмена":
        await cancel_edit(message, state)
        return

    user_id = message.from_user.id
    new_contacts = message.text

    await logger.ainfo(
        "Администратор ввёл новые контакты",
        user_id=user_id,
        contacts_length=len(new_contacts),
    )

    try:
        # Сохраняем новые контакты
        config_service = ConfigService(session)
        await config_service.set_value("contacts", new_contacts)
        await session.commit()

        # Очищаем состояние
        await state.clear()

        await logger.ainfo(
            "Контакты обновлены",
            user_id=user_id,
        )

        await message.answer(
            text="✅ Контакты обновлены",
        )

        # Возвращаем в главное меню
        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при сохранении контактов",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()


@router.message(ConfigEdit.waiting_for_location)
async def handle_config_location_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик ввода нового значения 'Где мы находимся'.
    """

    if message.text == "❌ Отмена":
        await cancel_edit(message, state)
        return

    user_id = message.from_user.id
    new_location = message.text

    await logger.ainfo(
        "Администратор ввёл новое местоположение",
        user_id=user_id,
        text_length=len(new_location),
    )

    try:
        config_service = ConfigService(session)
        await config_service.set_value("location", new_location)
        await session.commit()

        await state.clear()

        await logger.ainfo(
            "Местоположение обновлено",
            user_id=user_id,
        )

        await message.answer(
            text="✅ Местоположение обновлено",
        )

        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при сохранении местоположения",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()


@router.callback_query(F.data == "admin:settings:maps_url")
async def handle_settings_maps_url(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Редактирование ссылки на карту."""
    config_service = ConfigService(session)
    current = await config_service.get_config_value("maps_url")
    await state.set_state(ConfigEdit.waiting_for_maps_url)
    await callback.message.edit_text(
        text=(
            f"Текущая ссылка (нажмите чтобы скопировать):\n\n"
            f"<code>{current or 'Не задана'}</code>\n\n"
            f"Вставьте новую ссылку на 2GIS или нажмите Отмена:"
        ),
        parse_mode="HTML",
    )
    await callback.message.answer("👇", reply_markup=get_cancel_kb())


@router.message(ConfigEdit.waiting_for_maps_url)
async def handle_config_maps_url_input(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохранение новой ссылки на карту."""

    if message.text == "❌ Отмена":
        await cancel_edit(message, state)
        return

    config_service = ConfigService(session)
    await config_service.set_value("maps_url", message.text)
    await session.commit()
    await state.clear()
    await message.answer("✅ Ссылка на карту обновлена")
    await show_admin_menu(message)
