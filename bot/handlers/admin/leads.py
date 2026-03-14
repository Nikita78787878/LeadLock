"""Хендлеры управления заявками с пагинацией и карточками."""

import math

import structlog
from aiogram import Router, F
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.settings import settings
from bot.services.lead_service import LeadService
from bot.services.google_sheets_service import GoogleSheetsService
from bot.database.repositories.lead_repo import LeadRepository

logger = structlog.get_logger()
router = Router(name="admin_leads")

PAGE_SIZE = 5  # заявок на одной странице


# ============================================================================
# CallbackData
# ============================================================================

class LeadsPageCD(CallbackData, prefix="leads_page"):
    page: int


class LeadDetailCD(CallbackData, prefix="lead_detail"):
    lead_id: int
    page: int  # чтобы вернуться на ту же страницу


# ============================================================================
# Вспомогательная функция: клавиатура списка заявок
# ============================================================================

def _build_leads_keyboard(
    leads,
    page: int,
    total: int,
) -> object:
    """
    Строит клавиатуру для списка заявок.

    Структура:
    - Кнопка на каждую заявку (имя + дата)
    - Строка навигации: [← Пред] [страница/всего] [След →]
    - Кнопка экспорта и назад
    """
    total_pages = max(1, math.ceil(total / PAGE_SIZE))
    builder = InlineKeyboardBuilder()

    # Кнопка на каждую заявку
    for lead in leads:
        date_str = lead.created_at.strftime("%d.%m %H:%M")
        builder.button(
            text=f"👤 {lead.name} — {date_str}",
            callback_data=LeadDetailCD(lead_id=lead.id, page=page).pack(),
        )

    # Навигационная строка
    nav_buttons = []

    if page > 0:
        nav_buttons.append(("⬅️", LeadsPageCD(page=page - 1).pack()))
    else:
        nav_buttons.append(("·", "noop"))

    nav_buttons.append((f"{page + 1}/{total_pages}", "noop"))

    if page + 1 < total_pages:
        nav_buttons.append(("➡️", LeadsPageCD(page=page + 1).pack()))
    else:
        nav_buttons.append(("·", "noop"))

    for text, cb in nav_buttons:
        builder.button(text=text, callback_data=cb)

    # Нижние кнопки
    builder.button(text="📤 Экспорт в Google Sheets", callback_data="admin:leads:export")
    builder.button(text="⬅️ Назад", callback_data="admin:main")

    # Динамический adjust: по 1 на каждую заявку, 3 nav-кнопки в ряд, 2 нижних по 1
    rows = [1] * len(leads) + [3, 1, 1]
    builder.adjust(*rows)

    return builder.as_markup()


# ============================================================================
# Список заявок (первая страница)
# ============================================================================

@router.callback_query(F.data == "admin:leads")
async def handle_admin_leads(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Открыть раздел заявок — первая страница."""
    await _show_leads_page(callback, session, page=0)


# ============================================================================
# Список заявок (пагинация)
# ============================================================================

@router.callback_query(LeadsPageCD.filter())
async def handle_leads_page(
    callback: CallbackQuery,
    callback_data: LeadsPageCD,
    session: AsyncSession,
) -> None:
    """Перейти на указанную страницу списка заявок."""
    await _show_leads_page(callback, session, page=callback_data.page)


# ============================================================================
# Общая функция отображения страницы
# ============================================================================

async def _show_leads_page(
    callback: CallbackQuery,
    session: AsyncSession,
    page: int,
) -> None:
    """Отображает страницу списка заявок."""
    repo = LeadRepository(session)
    total = await repo.count_all()

    if total == 0:
        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️ Назад", callback_data="admin:main")
        await callback.message.edit_text(
            text="📊 Заявок пока нет.",
            reply_markup=builder.as_markup(),
        )
        await callback.answer()
        return

    total_pages = max(1, math.ceil(total / PAGE_SIZE))

    # Защита от выхода за границы
    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    leads = await repo.get_page(page=page, page_size=PAGE_SIZE)

    # Считаем номера заявок для отображения
    start_num = page * PAGE_SIZE + 1
    end_num = start_num + len(leads) - 1

    text = (
        f"📊 <b>Заявки</b> ({start_num}–{end_num} из {total})\n"
        f"Нажмите на заявку чтобы открыть подробности.\n"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=_build_leads_keyboard(leads, page, total),
        parse_mode="HTML",
    )
    await callback.answer()


# ============================================================================
# Карточка заявки
# ============================================================================

@router.callback_query(LeadDetailCD.filter())
async def handle_lead_detail(
    callback: CallbackQuery,
    callback_data: LeadDetailCD,
    session: AsyncSession,
) -> None:
    """Показать полную карточку заявки."""
    from sqlalchemy import select
    from bot.database.models.lead import Lead

    repo = LeadRepository(session)

    stmt = select(Lead).where(Lead.id == callback_data.lead_id)
    result = await session.execute(stmt)
    lead = result.scalars().first()

    if lead is None:
        await callback.answer("Заявка не найдена", show_alert=True)
        return

    status_map = {
        "new": "🆕 Новая",
        "in_progress": "🔄 В работе",
        "closed": "✅ Закрыта",
        "rejected": "❌ Отклонена",
    }
    status_label = status_map.get(lead.status, lead.status)
    synced_label = "✅ Да" if lead.synced_to_sheets else "⏳ Нет"

    text = (
        f"📋 <b>Заявка #{lead.id}</b>\n\n"
        f"👤 <b>Имя:</b> {lead.name}\n"
        f"📞 <b>Телефон:</b> {lead.phone}\n"
        f"📝 <b>Комментарий:</b> {lead.description or '—'}\n"
        f"📌 <b>Статус:</b> {status_label}\n"
        f"🕐 <b>Создана:</b> {lead.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📤 <b>В Sheets:</b> {synced_label}"
    )

    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ К списку",
        callback_data=LeadsPageCD(page=callback_data.page).pack(),
    )
    builder.adjust(1)

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )
    await callback.answer()


# ============================================================================
# Заглушка для noop-кнопок (счётчик страниц)
# ============================================================================

@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """Пустой обработчик для декоративных кнопок."""
    await callback.answer()


# ============================================================================
# Экспорт в Google Sheets
# ============================================================================

@router.callback_query(F.data == "admin:leads:export")
async def export_leads_to_sheets(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    """Выгрузить несинхронизированные заявки в Google Sheets."""
    await callback.answer(text="⏳ Выгружаю...", show_alert=False)

    sheets_service = GoogleSheetsService(
        credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
        sheet_id=settings.GOOGLE_SHEET_ID,
    )
    lead_service = LeadService(session, sheets_service=sheets_service)

    try:
        count = await lead_service.export_to_sheets()
        await session.commit()

        if count == 0:
            await callback.message.answer("✅ Все заявки уже присутствуют в Google Sheets")
        else:
            await callback.message.answer(
                f"✅ Добавлено <b>{count}</b> заявок в Google Sheets",
                parse_mode="HTML",
            )
    except Exception as e:
        await logger.aerror("Ошибка при выгрузке заявок", error=str(e))
        await callback.message.answer("❌ Ошибка при выгрузке. Попробуйте позже.")
