"""Сервисный слой для работы с FAQ."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.faq_item import FAQItem
from bot.database.repositories.faq_repo import FAQRepository

logger = structlog.get_logger()


class FAQService:
    """Сервис для работы с FAQ."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session: AsyncSession для операций с БД
        """
        self.repository = FAQRepository(session)

    async def get_all_faq_items(self) -> list[FAQItem]:
        """
        Получить все активные элементы FAQ.

        Returns:
            Список активных FAQItem
        """
        try:
            faq_items = await self.repository.get_all()
            await logger.ainfo(
                "Получен список FAQ",
                count=len(faq_items),
            )
            return faq_items
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении списка FAQ",
                error=str(e),
            )
            raise

    async def get_faq_item_by_id(self, faq_id: int) -> FAQItem | None:
        """
        Получить элемент FAQ по ID.

        Args:
            faq_id: ID элемента FAQ

        Returns:
            Объект FAQItem если найден, иначе None
        """
        try:
            faq_item = await self.repository.get_by_id(faq_id)
            if faq_item:
                await logger.ainfo(
                    "Получен элемент FAQ",
                    faq_id=faq_id,
                    question=faq_item.question,
                )
            else:
                await logger.awarning(
                    "Элемент FAQ не найден",
                    faq_id=faq_id,
                )
            return faq_item
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении элемента FAQ",
                faq_id=faq_id,
                error=str(e),
            )
            raise
