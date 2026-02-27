"""Хендлеры административной панели."""

import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.settings import settings
from bot.services.faq_service import FAQService
from bot.services.lead_service import LeadService
from bot.services.google_sheets_service import GoogleSheetsService
from bot.services.config_service import ConfigService
from bot.states.admin_states import FAQEdit, FAQAdd, ConfigEdit

logger = structlog.get_logger()

router = Router(name="admin")


# ============================================================================
# Вспомогательные функции
# ============================================================================


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


# ============================================================================
# Блок 1: Главное меню админки
# ============================================================================


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


# ============================================================================
# Блок 2: Управление FAQ
# ============================================================================


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


# ============================================================================
# Блок 3: Заявки
# ============================================================================


@router.callback_query(F.data == "admin:leads")
async def handle_admin_leads(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик просмотра последних заявок.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор открыл раздел заявок",
        user_id=user_id,
    )

    try:
        # Получаем последние заявки
        lead_service = LeadService(session)
        leads = await lead_service.get_recent_leads(limit=10)

        if not leads:
            # Заявок нет
            text = "📊 Заявок пока нет."

            builder = InlineKeyboardBuilder()
            builder.button(
                text="⬅️ Назад",
                callback_data="admin:main",
            )

            await callback.message.edit_text(
                text=text,
                reply_markup=builder.as_markup(),
            )

            await logger.ainfo(
                "Заявок нет",
                user_id=user_id,
            )
        else:
            # Формируем список заявок
            text = "📊 Последние заявки:\n\n"

            for i, lead in enumerate(leads, start=1):
                text += (
                    f"#{i} <b>{lead.name}</b>\n"
                    f"📞 {lead.phone}\n"
                    f"📝 {lead.description or '—'}\n"
                    f"🕐 {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
                    f"{'─' * 30}\n\n"
                )

            # Кнопки управления
            builder = InlineKeyboardBuilder()
            builder.button(
                text="📤 Выгрузить в Google Sheets",
                callback_data="admin:leads:export",
            )
            builder.button(
                text="⬅️ Назад",
                callback_data="admin:main",
            )
            builder.adjust(1)

            await callback.message.edit_text(
                text=text,
                reply_markup=builder.as_markup(),
                parse_mode="HTML",
            )

            await logger.ainfo(
                "Отображены последние заявки",
                user_id=user_id,
                count=len(leads),
            )

        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при отображении заявок",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data == "admin:leads:export")
async def handle_leads_export(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """
    Обработчик экспорта заявок в Google Sheets.

    Args:
        callback: Callback query от администратора
        session: Сессия БД
    """
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор запустил экспорт заявок",
        user_id=user_id,
    )

    # Показываем уведомление о начале выгрузки
    await callback.answer(
        text="⏳ Выгружаю...",
        show_alert=False,
    )

    try:
        # Получаем все заявки
        lead_service = LeadService(session)
        leads = await lead_service.get_recent_leads(limit=100)

        if not leads:
            await callback.answer(
                text="Нет заявок для выгрузки",
                show_alert=True,
            )
            return

        # Создаём сервис Google Sheets
        sheets_service = GoogleSheetsService(
            credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
            sheet_id=settings.GOOGLE_SHEET_ID,
        )

        # Выгружаем каждую заявку
        exported_count = 0
        for lead in leads:
            try:
                await sheets_service.append_lead(lead)
                exported_count += 1
            except Exception as e:
                await logger.awarning(
                    "Ошибка при выгрузке отдельной заявки",
                    lead_id=lead.id,
                    error=str(e),
                )

        await logger.ainfo(
            "Экспорт заявок завершён",
            user_id=user_id,
            total=len(leads),
            exported=exported_count,
        )

        # Уведомляем об успешной выгрузке
        await callback.message.answer(
            text=f"✅ Выгружено {exported_count} заявок в Google Sheets",
        )

    except Exception as e:
        await logger.aerror(
            "Ошибка при экспорте заявок",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="❌ Произошла ошибка при экспорте.",
            show_alert=True,
        )


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


# ============================================================================
# Блок 4: Настройки
# ============================================================================


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
            text=f"Текущий текст:\n{current_text}\n\nВведите новый текст:",
        )
        await callback.answer()

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
            text=f"Текущие контакты:\n{current_contacts}\n\nВведите новые контакты:",
        )
        await callback.answer()

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
