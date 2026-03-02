"""Хендлеры управления заявками."""

import structlog
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.settings import settings
from bot.services.lead_service import LeadService
from bot.services.google_sheets_service import GoogleSheetsService

logger = structlog.get_logger()

router = Router(name="admin_leads")


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
async def export_leads_to_sheets(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Выгрузить несинхронизированные заявки в Google Sheets."""
    # Показываем уведомление о начале выгрузки
    await callback.answer(
        text="⏳ Выгружаю...",
        show_alert=False,
    )

    # Создаём сервис Google Sheets
    sheets_service = GoogleSheetsService(
        credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
        sheet_id=settings.GOOGLE_SHEET_ID,
    )

    # Создаём сервис заявок и передаём сервис Google Sheets
    lead_service = LeadService(session, sheets_service=sheets_service)

    try:
        # Синхронизируем несинхронизированные заявки
        count = await lead_service.sync_unsynced_to_sheets()

        # Коммитим изменения в базе данных
        await session.commit()

        # Если выгружено 0 заявок - показываем соответствующее сообщение
        if count == 0:
            await callback.message.answer(
                "✅ Все заявки уже выгружены в Google Sheets"
            )
        # Иначе - показываем количество выгруженных заявок
        else:
            await callback.message.answer(
                f"✅ Выгружено <b>{count}</b> новых заявок в Google Sheets"
            )

    # Обрабатываем ошибки
    except Exception as e:
        await logger.aerror(
            "Ошибка при выгрузке заявок",
            error=str(e),
        )
        await callback.message.answer(
            "❌ Ошибка при выгрузке. Попробуйте позже."
        )
