"""Хендлеры главного меню и навигации."""

import structlog
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.inline import (
    MainMenuCD,
    FAQItemCD,
    BackCD,
    get_main_menu_kb,
    get_faq_menu_kb,
    get_back_kb,
)
from bot.services.config_service import ConfigService
from bot.services.faq_service import FAQService

logger = structlog.get_logger()

router = Router(name="menu")


# ============================================================================
# Команда /start
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    from bot.database.repositories.user_repo import UserRepository

    user_id = message.from_user.id  # эта строка была потеряна
    username = message.from_user.username or "Пользователь"

    await logger.ainfo("Пользователь запустил бота", user_id=user_id, username=username)

    try:
        # Сохраняем пользователя в БД если не существует
        user_repo = UserRepository(session)
        user = await user_repo.get_by_tg_id(user_id)
        if user is None:
            user = await user_repo.create_user(
                telegram_id=user_id,
                username=message.from_user.username,
                full_name=message.from_user.full_name,
            )
            await session.commit()
            await logger.ainfo("Новый пользователь создан в БД", user_id=user_id)
        else:
            await logger.ainfo("Пользователь уже существует в БД", user_id=user_id)

        # Получаем приветственный текст через сервис
        config_service = ConfigService(session)
        welcome_text = await config_service.get_welcome_text()

        await message.answer(text=welcome_text, reply_markup=get_main_menu_kb())
        await logger.ainfo("Отправлено приветственное сообщение", user_id=user_id)

    except Exception as e:
        await logger.aerror("Ошибка при обработке команды /start", user_id=user_id, error=str(e))
        await message.answer(text="Добро пожаловать! 👋", reply_markup=get_main_menu_kb())
# ============================================================================
# Обработчик главного меню
# ============================================================================


@router.callback_query(MainMenuCD.filter())
async def handle_main_menu(
    callback: CallbackQuery,
    callback_data: MainMenuCD,
    session: AsyncSession,
) -> None:
    """
    Обработчик кнопок главного меню.

    Обрабатывает действия: "faq", "contact".
    Действие "lead" обрабатывается в lead_form.py.

    Args:
        callback: Callback query от пользователя
        callback_data: Данные callback с action
        session: Сессия БД
    """
    user_id = callback.from_user.id
    action = callback_data.action

    await logger.ainfo(
        "Выбрано действие в главном меню",
        user_id=user_id,
        action=action,
    )

    try:
        if action == "faq":
            # Получаем список FAQ через сервис
            faq_service = FAQService(session)
            faq_items = await faq_service.get_all_faq_items()

            if not faq_items:
                await callback.message.edit_text(
                    text="❓ FAQ пуст. Вопросы пока не добавлены.",
                    reply_markup=get_back_kb(back_to="main"),
                )
                await logger.awarning(
                    "Список FAQ пуст",
                    user_id=user_id,
                )
            else:
                await callback.message.edit_text(
                    text="❓ Часто задаваемые вопросы:\n\nВыберите интересующий вас вопрос:",
                    reply_markup=get_faq_menu_kb(faq_items),
                )
                await logger.ainfo(
                    "Отображен список FAQ",
                    user_id=user_id,
                    count=len(faq_items),
                )

        elif action == "contact":
            # TODO: Реализация отображения контактов
            await callback.message.edit_text(
                text="📞 Контактная информация будет доступна в следующей версии.",
                reply_markup=get_back_kb(back_to="main"),
            )
            await logger.ainfo(
                "Выбрана функция контактов",
                user_id=user_id,
            )

        else:
            await logger.awarning(
                "Неизвестное действие в главном меню",
                user_id=user_id,
                action=action,
            )

        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при обработке главного меню",
            user_id=user_id,
            action=action,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


# ============================================================================
# Обработчик просмотра элемента FAQ
# ============================================================================


@router.callback_query(FAQItemCD.filter())
async def handle_faq_item(
    callback: CallbackQuery,
    callback_data: FAQItemCD,
    session: AsyncSession,
) -> None:
    """
    Обработчик выбора элемента FAQ.

    Получает элемент FAQ из БД и отображает его с кнопкой "Назад".

    Args:
        callback: Callback query от пользователя
        callback_data: Данные callback с faq_id
        session: Сессия БД
    """
    user_id = callback.from_user.id
    faq_id = callback_data.faq_id

    await logger.ainfo(
        "Пользователь выбрал элемент FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    try:
        # Получаем элемент FAQ через сервис
        faq_service = FAQService(session)
        faq_item = await faq_service.get_faq_item_by_id(faq_id)

        if not faq_item:
            await callback.message.edit_text(
                text="❌ Элемент FAQ не найден.",
                reply_markup=get_back_kb(back_to="faq"),
            )
            await logger.awarning(
                "Элемент FAQ не найден",
                user_id=user_id,
                faq_id=faq_id,
            )
            await callback.answer(
                text="Элемент не найден",
                show_alert=True,
            )
            return

        # Формируем текст ответа
        text = f"❓ <b>{faq_item.question}</b>\n\n{faq_item.answer}"

        # Отправляем ответ с кнопкой "Назад"
        await callback.message.edit_text(
            text=text,
            reply_markup=get_back_kb(back_to="faq"),
            parse_mode="HTML",
        )

        await logger.ainfo(
            "Отображен элемент FAQ",
            user_id=user_id,
            faq_id=faq_id,
            question=faq_item.question,
        )

        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при отображении элемента FAQ",
            user_id=user_id,
            faq_id=faq_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


# ============================================================================
# Обработчик кнопки "Назад"
# ============================================================================


@router.callback_query(BackCD.filter())
async def handle_back(
    callback: CallbackQuery,
    callback_data: BackCD,
    session: AsyncSession,
) -> None:
    """
    Обработчик кнопки "Назад".

    Возвращает пользователя в нужный раздел в зависимости от target.

    Args:
        callback: Callback query от пользователя
        callback_data: Данные callback с target
        session: Сессия БД
    """
    user_id = callback.from_user.id
    target = callback_data.target

    await logger.ainfo(
        "Пользователь нажал кнопку Назад",
        user_id=user_id,
        target=target,
    )

    try:
        if target == "main":
            # Возврат в главное меню
            config_service = ConfigService(session)
            welcome_text = await config_service.get_welcome_text()

            await callback.message.edit_text(
                text=welcome_text,
                reply_markup=get_main_menu_kb(),
            )
            await logger.ainfo(
                "Возврат в главное меню",
                user_id=user_id,
            )

        elif target == "faq":
            # Возврат в список FAQ
            faq_service = FAQService(session)
            faq_items = await faq_service.get_all_faq_items()

            if not faq_items:
                await callback.message.edit_text(
                    text="❓ FAQ пуст. Вопросы пока не добавлены.",
                    reply_markup=get_back_kb(back_to="main"),
                )
            else:
                await callback.message.edit_text(
                    text="❓ Часто задаваемые вопросы:\n\nВыберите интересующий вас вопрос:",
                    reply_markup=get_faq_menu_kb(faq_items),
                )

            await logger.ainfo(
                "Возврат в список FAQ",
                user_id=user_id,
            )

        else:
            await logger.awarning(
                "Неизвестная цель возврата",
                user_id=user_id,
                target=target,
            )
            # По умолчанию возвращаемся в главное меню
            config_service = ConfigService(session)
            welcome_text = await config_service.get_welcome_text()

            await callback.message.edit_text(
                text=welcome_text,
                reply_markup=get_main_menu_kb(),
            )

        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при обработке кнопки Назад",
            user_id=user_id,
            target=target,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )
