"""Сервисный слой для работы с заявками (лидами)."""

import re
from typing import TYPE_CHECKING, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.lead import Lead
from bot.database.repositories.lead_repo import LeadRepository
from bot.settings import settings

if TYPE_CHECKING:
    from aiogram import Bot
    from bot.services.google_sheets_service import GoogleSheetsService

logger = structlog.get_logger()


class LeadService:
    """Сервис для работы с заявками."""

    def __init__(
        self,
        session: AsyncSession,
        sheets_service: "GoogleSheetsService | None" = None,
        bot: "Bot | None" = None,
    ):
        """
        Инициализация сервиса.

        Args:
            session: AsyncSession для операций с БД
            sheets_service: Сервис для работы с Google Sheets
            bot: Экземпляр aiogram Bot для отправки уведомлений
        """
        self.repository = LeadRepository(session)
        self.sheets_service = sheets_service
        self.bot = bot

    def validate_name(self, name: str) -> tuple[bool, str]:
        """
        Валидировать имя заявителя.

        Проверяет:
        - Длина от 2 до 50 символов
        - Содержит только буквы (кириллица и латиница) и пробелы

        Args:
            name: Имя для проверки

        Returns:
            Кортеж (True, "") если валидно, иначе (False, "текст ошибки")
        """
        if not name or len(name.strip()) < 2:
            return False, "Имя должно содержать минимум 2 символа"

        if len(name) > 50:
            return False, "Имя не должно превышать 50 символов"

        # Проверка только буквы (кириллица и латиница) и пробелы
        if not re.match(r"^[а-яёА-ЯЁa-zA-Z\s]+$", name):
            return False, "Имя должно содержать только буквы и пробелы"

        return True, ""

    def normalize_phone(self, phone: str) -> str:
        """
        Нормализировать номер телефона.

        Преобразует номер в формат +7XXXXXXXXXX:
        - Удаляет все нецифровые символы
        - Заменяет начальное 8 на 7
        - Добавляет + в начало

        Args:
            phone: Номер телефона в любом формате

        Returns:
            Нормализированный номер в формате +7XXXXXXXXXX

        Example:
            "8(999)123-45-67" → "+79991234567"
        """
        # Удаляем всё кроме цифр
        digits = re.sub(r"\D", "", phone)

        # Если начинается с 8, заменяем на 7
        if digits.startswith("8"):
            digits = "7" + digits[1:]

        # Добавляем + в начало
        return f"+{digits}"

    def validate_phone(self, phone: str) -> tuple[bool, str]:
        """
        Валидировать номер телефона.

        Проверяет:
        - После нормализации ровно 12 символов (+79999999999)
        - Начинается с +7

        Args:
            phone: Номер телефона для проверки

        Returns:
            Кортеж (True, "") если валидно, иначе (False, "текст ошибки")
        """
        normalized = self.normalize_phone(phone)

        if len(normalized) != 12:
            return False, "Номер телефона должен содержать 11 цифр"

        if not normalized.startswith("+7"):
            return False, "Номер телефона должен начинаться с +7"

        return True, ""

    async def save_lead(
        self,
        user_id: int,
        name: str,
        phone: str,
        description: Optional[str] = None,
    ) -> Lead:
        """
        Сохранить новую заявку.

        Нормализирует телефон, сохраняет в БД, уведомляет об интеграции.

        Args:
            user_id: ID пользователя
            name: Имя заявителя
            phone: Номер телефона
            description: Описание заявки

        Returns:
            Созданный объект Lead

        Raises:
            Exception: При ошибке сохранения в БД
        """
        normalized_phone = self.normalize_phone(phone)

        try:
            lead = await self.repository.create(
                user_id=user_id,
                name=name,
                phone=normalized_phone,
                description=description,
                status="new",
            )

            await logger.ainfo(
                "Заявка создана",
                lead_id=lead.id,
                user_id=user_id,
                name=name,
                phone=normalized_phone,
            )

            # Отправляем уведомления в интеграции и админам
            await self._notify_sheets(lead)
            await self._notify_admins(lead, description)

            return lead
        except Exception as e:
            await logger.aerror(
                "Ошибка при создании заявки",
                user_id=user_id,
                error=str(e),
            )
            raise

    async def _notify_sheets(self, lead: Lead) -> None:
        """
        Отправить заявку в Google Sheets.

        Args:
            lead: Объект заявки для отправки
        """
        if self.sheets_service is None:
            await logger.ainfo(
                "Google Sheets сервис не подключён",
                lead_id=lead.id,
            )
            return

        await self.sheets_service.append_lead(lead)

    async def _notify_admins(self, lead: Lead, description: Optional[str] = None) -> None:
        """
        Отправить уведомление администраторам о новой заявке.

        Args:
            lead: Объект заявки
            description: Описание заявки
        """
        if self.bot is None:
            await logger.ainfo(
                "Bot не подключён, уведомление админам не отправлено",
                lead_id=lead.id,
            )
            return

        message_text = (
            f"🔔 Новая заявка!\n\n"
            f"👤 {lead.name}\n"
            f"📞 {lead.phone}\n"
            f"📝 {description or '—'}\n"
            f"🕐 {lead.created_at:%d.%m.%Y %H:%M}"
        )

        for admin_id in settings.ADMIN_IDS:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message_text,
                )
                await logger.ainfo(
                    "Уведомление отправлено администратору",
                    admin_id=admin_id,
                    lead_id=lead.id,
                )
            except Exception as e:
                await logger.aerror(
                    "Ошибка при отправке уведомления администратору",
                    admin_id=admin_id,
                    lead_id=lead.id,
                    error=str(e),
                    error_type=type(e).__name__,
                )

    async def get_recent_leads(self, limit: int = 10) -> list[Lead]:
        """
        Получить последние заявки.

        Args:
            limit: Количество заявок (по умолчанию: 10)

        Returns:
            Список последних заявок, отсортированных по дате создания

        Raises:
            Exception: При ошибке получения данных
        """
        try:
            leads = await self.repository.get_recent(limit)

            await logger.ainfo(
                "Получены последние заявки",
                count=len(leads),
                limit=limit,
            )

            return leads
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении последних заявок",
                limit=limit,
                error=str(e),
            )
            raise
