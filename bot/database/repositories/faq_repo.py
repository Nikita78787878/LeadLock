"""Репозиторий для работы с FAQ."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.faq_item import FAQItem


class FAQRepository:
    """Репозиторий для операций с моделью FAQItem."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией.

        Args:
            session: AsyncSession для операций с БД
        """
        self.session = session

    async def get_all(self) -> list[FAQItem]:
        """
        Получить все активные элементы FAQ.

        Returns:
            Список активных FAQItem, отсортированных по полю order
        """
        stmt = (
            select(FAQItem)
            .where(FAQItem.is_active == True)
            .order_by(FAQItem.order, FAQItem.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, faq_id: int) -> FAQItem | None:
        """
        Получить элемент FAQ по ID.

        Args:
            faq_id: ID элемента FAQ

        Returns:
            Объект FAQItem если найден, иначе None
        """
        stmt = select(FAQItem).where(FAQItem.id == faq_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()
