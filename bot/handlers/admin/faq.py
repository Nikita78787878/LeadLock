"""Хендлеры управления FAQ."""

import structlog
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.faq_service import FAQService
from bot.states.admin_states import FAQEdit, FAQAdd
from .menu import show_admin_menu

logger = structlog.get_logger()

router = Router(name="admin_faq")


async def show_faq_list(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Отобразить список FAQ с кнопками управления.

    Args:
        callback: Callback query для редактирования сообщения
        session: Сессия БД
    """
    user_id = callback.from_user.id

    # Получаем список FAQ
    faq_service = FAQService(session)
    faq_items = await faq_service.get_all_faq_items()

    builder = InlineKeyboardBuilder()

    if not faq_items:
        # FAQ пуст - показываем только кнопку добавления
        text = "📝 FAQ пуст. Добавьте первый вопрос."

        builder.button(
            text="➕ Добавить FAQ",
            callback_data="admin:faq:add",
        )
        builder.button(
            text="⬅️ Назад",
            callback_data="admin:main",
        )
        builder.adjust(1)

        await logger.ainfo(
            "Отображена пустая панель FAQ",
            user_id=user_id,
        )
    else:
        # Формируем список FAQ
        text = "📝 Управление FAQ:\n\n"

        for i, item in enumerate(faq_items, start=1):
            # Обрезаем вопрос до 25 символов
            question_short = item.question
            if len(question_short) > 25:
                question_short = question_short[:25] + "..."

            text += f"{i}. {question_short}\n"

            # Кнопка просмотра
            builder.button(
                text=f"{i}. {question_short}",
                callback_data=f"admin:faq:view:{item.id}",
            )
            # Кнопки редактирования и удаления в одной строке
            builder.button(
                text="✏️",
                callback_data=f"admin:faq:edit:{item.id}",
            )
            builder.button(
                text="🗑️",
                callback_data=f"admin:faq:del:{item.id}",
            )
            builder.adjust(1, 2)

        # Кнопка добавления нового FAQ
        builder.button(
            text="➕ Добавить FAQ",
            callback_data="admin:faq:add",
        )
        builder.button(
            text="⬅️ Назад",
            callback_data="admin:main",
        )

        await logger.ainfo(
            "Отображен список FAQ",
            user_id=user_id,
            count=len(faq_items),
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "admin:faq")
async def handle_admin_faq(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик открытия раздела управления FAQ.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор открыл управление FAQ",
        user_id=user_id,
    )

    try:
        await show_faq_list(callback, session)
        await callback.answer()
    except Exception as e:
        await logger.aerror(
            "Ошибка при отображении списка FAQ",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("admin:faq:view:"))
async def handle_faq_view(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик просмотра элемента FAQ.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id
    faq_id = int(callback.data.split(":")[-1])

    await logger.ainfo(
        "Администратор просматривает FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    try:
        faq_service = FAQService(session)
        faq_item = await faq_service.get_faq_item_by_id(faq_id)

        if not faq_item:
            await callback.answer(
                text="Элемент FAQ не найден",
                show_alert=True,
            )
            return

        # Формируем текст с вопросом и ответом
        text = f"📝 <b>Вопрос:</b>\n{faq_item.question}\n\n<b>Ответ:</b>\n{faq_item.answer}"

        # Кнопки управления
        builder = InlineKeyboardBuilder()
        builder.button(
            text="✏️ Редактировать",
            callback_data=f"admin:faq:edit:{faq_id}",
        )
        builder.button(
            text="🗑️ Удалить",
            callback_data=f"admin:faq:del:{faq_id}",
        )
        builder.button(
            text="⬅️ К списку",
            callback_data="admin:faq",
        )
        builder.adjust(2, 1)

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при просмотре FAQ",
            user_id=user_id,
            faq_id=faq_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("admin:faq:del:"))
async def handle_faq_delete(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик удаления элемента FAQ.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id
    faq_id = int(callback.data.split(":")[-1])

    await logger.ainfo(
        "Администратор удаляет FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    try:
        faq_service = FAQService(session)

        # Удаляем через репозиторий
        await faq_service.repository.delete(faq_id)

        # Коммитим изменения
        await session.commit()

        await logger.ainfo(
            "FAQ успешно удалён",
            user_id=user_id,
            faq_id=faq_id,
        )

        # Показываем уведомление
        await callback.answer(
            text="✅ Пункт FAQ удалён",
            show_alert=True,
        )

        # Обновляем список FAQ
        await show_faq_list(callback, session)

    except Exception as e:
        await logger.aerror(
            "Ошибка при удалении FAQ",
            user_id=user_id,
            faq_id=faq_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка при удалении.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("admin:faq:edit:"))
async def handle_faq_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Обработчик начала редактирования FAQ.

    Запрашивает новый текст вопроса.

    Args:
        callback: Callback query от администратора
        state: Состояние FSM
    """
    user_id = callback.from_user.id
    faq_id = int(callback.data.split(":")[-1])

    await logger.ainfo(
        "Администратор начал редактирование FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    # Сохраняем ID редактируемого FAQ
    await state.update_data(editing_faq_id=faq_id)

    # Переходим к ожиданию вопроса
    await state.set_state(FAQEdit.waiting_for_question)

    await callback.message.edit_text(
        text="✏️ Введите новый текст ВОПРОСА:",
    )
    await callback.answer()


@router.message(FAQEdit.waiting_for_question)
async def handle_faq_edit_question(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Обработчик ввода нового вопроса при редактировании FAQ.

    Args:
        message: Сообщение с текстом вопроса
        state: Состояние FSM
    """
    user_id = message.from_user.id
    new_question = message.text

    await logger.ainfo(
        "Администратор ввёл новый вопрос",
        user_id=user_id,
        question_length=len(new_question),
    )

    # Сохраняем вопрос
    await state.update_data(new_question=new_question)

    # Переходим к ожиданию ответа
    await state.set_state(FAQEdit.waiting_for_answer)

    await message.answer(
        text="✏️ Теперь введите текст ОТВЕТА:",
    )


@router.message(FAQEdit.waiting_for_answer)
async def handle_faq_edit_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик ввода нового ответа при редактировании FAQ.

    Сохраняет изменения в БД.

    Args:
        message: Сообщение с текстом ответа
        state: Состояние FSM
        session: Сессия БД
    """
    user_id = message.from_user.id
    new_answer = message.text

    await logger.ainfo(
        "Администратор ввёл новый ответ",
        user_id=user_id,
        answer_length=len(new_answer),
    )

    try:
        # Получаем данные из состояния
        data = await state.get_data()
        faq_id = data["editing_faq_id"]
        new_question = data["new_question"]

        # Обновляем через репозиторий
        faq_service = FAQService(session)
        await faq_service.repository.update(
            faq_id=faq_id,
            question=new_question,
            answer=new_answer,
        )

        # Коммитим изменения
        await session.commit()

        # Очищаем состояние
        await state.clear()

        await logger.ainfo(
            "FAQ успешно обновлён",
            user_id=user_id,
            faq_id=faq_id,
        )

        await message.answer(
            text="✅ FAQ обновлён!",
        )

        # Возвращаем в главное меню админки
        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при обновлении FAQ",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()


@router.callback_query(F.data == "admin:faq:add")
async def handle_faq_add_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """
    Обработчик начала добавления нового FAQ.

    Запрашивает текст вопроса.

    Args:
        callback: Callback query от администратора
        state: Состояние FSM
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор начал добавление FAQ",
        user_id=user_id,
    )

    # Переходим к ожиданию вопроса
    await state.set_state(FAQAdd.waiting_for_question)

    await callback.message.edit_text(
        text="➕ Введите текст ВОПРОСА для нового FAQ:",
    )
    await callback.answer()


@router.message(FAQAdd.waiting_for_question)
async def handle_faq_add_question(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Обработчик ввода вопроса при добавлении FAQ.

    Args:
        message: Сообщение с текстом вопроса
        state: Состояние FSM
    """
    user_id = message.from_user.id
    new_question = message.text

    await logger.ainfo(
        "Администратор ввёл вопрос для нового FAQ",
        user_id=user_id,
        question_length=len(new_question),
    )

    # Сохраняем вопрос
    await state.update_data(new_question=new_question)

    # Переходим к ожиданию ответа
    await state.set_state(FAQAdd.waiting_for_answer)

    await message.answer(
        text="➕ Теперь введите текст ОТВЕТА:",
    )


@router.message(FAQAdd.waiting_for_answer)
async def handle_faq_add_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """
    Обработчик ввода ответа при добавлении FAQ.

    Создаёт новый элемент FAQ в БД.

    Args:
        message: Сообщение с текстом ответа
        state: Состояние FSM
        session: Сессия БД
    """
    user_id = message.from_user.id
    new_answer = message.text

    await logger.ainfo(
        "Администратор ввёл ответ для нового FAQ",
        user_id=user_id,
        answer_length=len(new_answer),
    )

    try:
        # Получаем данные из состояния
        data = await state.get_data()
        new_question = data["new_question"]

        # Создаём через репозиторий
        faq_service = FAQService(session)
        faq_item = await faq_service.repository.create(
            question=new_question,
            answer=new_answer,
        )

        # Коммитим изменения
        await session.commit()

        # Очищаем состояние
        await state.clear()

        await logger.ainfo(
            "Новый FAQ успешно добавлен",
            user_id=user_id,
            faq_id=faq_item.id,
        )

        await message.answer(
            text="✅ Новый FAQ добавлен!",
        )

        # Возвращаем в главное меню админки
        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при добавлении FAQ",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()
