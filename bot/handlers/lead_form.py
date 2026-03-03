"""Хендлеры для формы сбора заявок."""

import asyncio

import structlog
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from bot.keyboards.inline import MainMenuCD, get_main_menu_kb
from bot.services.lead_service import LeadService
from bot.states.lead_states import LeadForm

logger = structlog.get_logger()

router = Router(name="lead_form")


# ============================================================================
# Функции для генерации клавиатур
# ============================================================================


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """
    Генерирует клавиатуру для запроса телефона.

    Содержит кнопку "Поделиться контактом" и кнопку "Отмена".

    Returns:
        ReplyKeyboardMarkup: Клавиатура для запроса телефона
    """
    buttons = [
        [
            KeyboardButton(
                text="📱 Поделиться контактом",
                request_contact=True,
            ),
        ],
        [
            KeyboardButton(text="❌ Отмена"),
        ],
    ]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """
    Генерирует клавиатуру только с кнопкой "Отмена".

    Returns:
        ReplyKeyboardMarkup: Клавиатура с кнопкой отмены
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ============================================================================
# Инициирование формы заявки
# ============================================================================


@router.callback_query(MainMenuCD.filter(F.action == "lead"))
async def start_lead_form(
    callback: CallbackQuery,
    state: FSMContext,
    session,
) -> None:
    """
    Инициирует форму сбора заявки.

    Отправляет первый вопрос (имя) и переводит FSM в состояние waiting_for_name.

    Args:
        callback: Callback query от пользователя
        state: FSM context
        session: Сессия БД (из middleware)
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Инициирование формы заявки",
        user_id=user_id,
    )

    # Очищаем старое состояние если оно есть
    await state.clear()

    # Отправляем первый вопрос (через answer, не edit)
    await callback.message.answer(
        text="📋 Давайте оформим заявку!\n\nКак вас зовут?",
        reply_markup=get_cancel_keyboard(),
    )

    # Устанавливаем состояние ожидания имени
    await state.set_state(LeadForm.waiting_for_name)

    await logger.ainfo(
        "Форма заявки инициирована, ожидание имени",
        user_id=user_id,
    )

    await callback.answer()


# ============================================================================
# Ввод имени
# ============================================================================


@router.message(LeadForm.waiting_for_name)
async def process_name(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    """
    Обработчик ввода имени заявителя.

    Валидирует имя, при ошибке повторяет запрос, при успехе переходит к телефону.

    Args:
        message: Сообщение от пользователя
        state: FSM context
        session: Сессия БД (из middleware)
    """
    user_id = message.from_user.id
    text = message.text

    await logger.ainfo(
        "Получен ввод имени",
        user_id=user_id,
        name=text,
    )

    # Проверка на отмену
    if text == "❌ Отмена":
        await state.clear()

        await logger.ainfo(
            "Заявка отменена при вводе имени",
            user_id=user_id,
        )

        await message.answer(
            text="❌ Заявка отменена.",
            reply_markup=get_main_menu_kb(),
        )
        return

    # Валидируем имя
    lead_service = LeadService(session)
    is_valid, error_text = lead_service.validate_name(text)

    if not is_valid:
        await logger.awarning(
            "Ошибка валидации имени",
            user_id=user_id,
            name=text,
            error=error_text,
        )

        await message.answer(
            text=f"❌ {error_text}\n\nПожалуйста, введите корректное имя:",
            reply_markup=get_cancel_keyboard(),
        )
        return

    # Сохраняем имя в state и переходим к телефону
    await state.update_data(name=text)

    await logger.ainfo(
        "Имя валидировано и сохранено",
        user_id=user_id,
        name=text,
    )

    await message.answer(
        text="✅ Спасибо!\n\nТеперь поделитесь своим номером телефона:",
        reply_markup=get_phone_keyboard(),
    )

    await state.set_state(LeadForm.waiting_for_phone)

    await logger.ainfo(
        "Переход к вводу телефона",
        user_id=user_id,
    )


# ============================================================================
# Ввод телефона — через контакт
# ============================================================================


@router.message(LeadForm.waiting_for_phone, F.contact)
async def process_phone_contact(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    """
    Обработчик получения телефона через кнопку "Поделиться контактом".

    Сохраняет номер телефона и переходит к вводу описания.

    Args:
        message: Сообщение от пользователя с контактом
        state: FSM context
        session: Сессия БД (из middleware)
    """
    user_id = message.from_user.id
    phone_number = message.contact.phone_number

    await logger.ainfo(
        "Получен телефон через контакт",
        user_id=user_id,
        phone=phone_number,
    )

    # Сохраняем телефон в state
    await state.update_data(phone=phone_number)

    await logger.ainfo(
        "Телефон сохранен в state",
        user_id=user_id,
        phone=phone_number,
    )

    await message.answer(
        text="✅ Телефон принят!\n\nОпишите вашу проблему или вопрос:",
        reply_markup=get_cancel_keyboard(),
    )

    await state.set_state(LeadForm.waiting_for_description)

    await logger.ainfo(
        "Переход к вводу описания",
        user_id=user_id,
    )


# ============================================================================
# Ввод телефона — через текст
# ============================================================================


@router.message(LeadForm.waiting_for_phone, F.text)
async def process_phone_text(
    message: Message,
    state: FSMContext,
    session,
) -> None:
    """
    Обработчик ввода телефона как текст.

    Валидирует номер, при ошибке повторяет запрос, при успехе переходит к описанию.

    Args:
        message: Сообщение от пользователя
        state: FSM context
        session: Сессия БД (из middleware)
    """
    user_id = message.from_user.id
    text = message.text

    await logger.ainfo(
        "Получен ввод телефона текстом",
        user_id=user_id,
        phone=text,
    )

    # Проверка на отмену
    if text == "❌ Отмена":
        await state.clear()

        await logger.ainfo(
            "Заявка отменена при вводе телефона",
            user_id=user_id,
        )

        await message.answer(
            text="❌ Заявка отменена.",
            reply_markup=get_main_menu_kb(),
        )
        return

    # Валидируем телефон
    lead_service = LeadService(session)
    is_valid, error_text = lead_service.validate_phone(text)

    if not is_valid:
        await logger.awarning(
            "Ошибка валидации телефона",
            user_id=user_id,
            phone=text,
            error=error_text,
        )

        await message.answer(
            text=f"❌ {error_text}\n\nПожалуйста, введите корректный номер телефона:",
            reply_markup=get_phone_keyboard(),
        )
        return

    # Сохраняем телефон в state и переходим к описанию
    await state.update_data(phone=text)

    await logger.ainfo(
        "Телефон валидирован и сохранен",
        user_id=user_id,
        phone=text,
    )

    await message.answer(
        text="✅ Спасибо!\n\nОпишите вашу проблему или вопрос:",
        reply_markup=get_cancel_keyboard(),
    )

    await state.set_state(LeadForm.waiting_for_description)

    await logger.ainfo(
        "Переход к вводу описания",
        user_id=user_id,
    )


# ============================================================================
# Ввод описания и сохранение заявки
# ============================================================================

@router.message(LeadForm.waiting_for_description)
async def process_description(
    message: Message,
    state: FSMContext,
    session,
    bot: Bot,
) -> None:
    from bot.database.repositories.user_repo import UserRepository
    from bot.services.google_sheets_service import GoogleSheetsService
    from bot.settings import settings

    user_id = message.from_user.id
    text = message.text

    await logger.ainfo("Получено описание заявки", user_id=user_id, description_length=len(text))

    # Проверка на отмену
    if text == "❌ Отмена":
        await state.clear()
        await message.answer(text="❌ Заявка отменена.", reply_markup=get_main_menu_kb())
        return

    # Получаем данные из state
    data = await state.get_data()
    name = data.get("name")
    phone = data.get("phone")

    await logger.ainfo("Данные заявки собраны", user_id=user_id, name=name, phone=phone)

    # Получаем внутренний id пользователя из БД
    user_repo = UserRepository(session)
    user = await user_repo.get_by_tg_id(user_id)
    if user is None:
        await message.answer("❌ Ошибка. Отправьте /start и попробуйте снова.", reply_markup=get_main_menu_kb())
        await state.clear()
        return

    # Подключаем Google Sheets
    sheets_service = GoogleSheetsService(
        credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
        sheet_id=settings.GOOGLE_SHEET_ID,
    )

    # Сохраняем заявку
    lead_service = LeadService(session, sheets_service=sheets_service, bot=bot)

    try:
        lead = await lead_service.save_lead(
            user_id=user.id,  # внутренний id, не telegram_id
            name=name,
            phone=phone,
            description=text,
        )
        await session.commit()

        await state.clear()

        await message.answer(
            text=f"✅ Заявка принята!\n\nМы свяжемся с вами в ближайшее время.\n\n{name}, спасибо за обращение!",
            reply_markup=ReplyKeyboardRemove(),
        )

        await asyncio.sleep(1)
        await message.answer(text="Чем я еще могу вам помочь?", reply_markup=get_main_menu_kb())

        await logger.ainfo("Заявка успешно сохранена", user_id=user_id, lead_id=lead.id)

    except Exception as e:
        await logger.aerror("Ошибка при сохранении заявки", user_id=user_id, error=str(e))
        await state.clear()
        await message.answer(
            text="❌ Произошла ошибка при сохранении заявки. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_menu_kb(),
        )
