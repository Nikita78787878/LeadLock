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

    async def get_by_category(self, category: str) -> list[FAQItem]:
        """Получить активные элементы FAQ по категории."""
        stmt = (
            select(FAQItem)
            .where(FAQItem.is_active == True)
            .where(FAQItem.category == category)
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

    async def create(self, question: str, answer: str, order: int = 0, category: str = "faq") -> FAQItem:
        """
        Создать новый элемент FAQ.

        Args:
            question: Вопрос FAQ
            answer: Ответ на вопрос
            order: Порядок сортировки (по умолчанию 0)
            category: Категория FAQ (по умолчанию "faq")

        Returns:
            Созданный объект FAQItem
        """
        item = FAQItem(question=question, answer=answer, order=order, category=category)
        self.session.add(item)
        await self.session.flush()
        return item

    async def update(
        self,
        faq_id: int,
        question: str | None = None,
        answer: str | None = None,
    ) -> FAQItem | None:
        """
        Обновить элемент FAQ.

        Args:
            faq_id: ID элемента FAQ
            question: Новый вопрос (опционально)
            answer: Новый ответ (опционально)

        Returns:
            Обновленный объект FAQItem или None если элемент не найден
        """
        item = await self.get_by_id(faq_id)
        if not item:
            return None

        if question is not None:
            item.question = question
        if answer is not None:
            item.answer = answer

        await self.session.flush()
        return item

    async def delete(self, faq_id: int) -> bool:
        """
        Удалить элемент FAQ (мягкое удаление).

        Args:
            faq_id: ID элемента FAQ

        Returns:
            True если элемент удален, False если элемент не найден
        """
        item = await self.get_by_id(faq_id)
        if not item:
            return False

        item.is_active = False
        await self.session.flush()
        return True
