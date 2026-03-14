"""Lead repository for database operations."""

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.lead import Lead


class LeadRepository:
    """Repository for Lead model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def create(
        self,
        user_id: int,
        name: str,
        phone: str,
        description: str | None = None,
        status: str = "new",
    ) -> Lead:
        """
        Create a new lead.

        Args:
            user_id: User ID associated with the lead
            name: Lead name
            phone: Lead phone number
            description: Optional lead description
            status: Lead status (default: "new")

        Returns:
            Created Lead object
        """
        lead = Lead(
            user_id=user_id,
            name=name,
            phone=phone,
            description=description,
            status=status,
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def get_by_user_id(self, user_id: int) -> list[Lead]:
        """
        Get all leads for a specific user.

        Args:
            user_id: User ID

        Returns:
            List of Lead objects
        """
        stmt = select(Lead).where(Lead.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_all(self) -> list[Lead]:
        """
        Get all leads.

        Returns:
            List of all Lead objects
        """
        stmt = select(Lead)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def update_status(self, lead_id: int, status: str) -> Lead | None:
        """
        Update lead status.

        Args:
            lead_id: Lead ID
            status: New status

        Returns:
            Updated Lead object if found, None otherwise
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        result = await self.session.execute(stmt)
        lead = result.scalars().first()

        if lead is None:
            return None

        lead.status = status
        await self.session.flush()
        return lead

    async def get_recent(self, limit: int = 10) -> list[Lead]:
        """
        Получить последние N заявок, отсортированных по дате создания.

        Args:
            limit: Количество заявок для получения (по умолчанию: 10)

        Returns:
            Список объектов Lead, отсортированных по дате создания в порядке убывания
        """
        stmt = select(Lead).order_by(desc(Lead.created_at)).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_unsynced(self) -> list[Lead]:
        """
        Получить заявки не выгруженные в Google Sheets.

        Returns:
            Список объектов Lead, не синхронизированных с Google Sheets
        """
        stmt = select(Lead).where(Lead.synced_to_sheets == False).order_by(Lead.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_synced(self, lead_id: int) -> None:
        """
        Пометить заявку как выгруженную в Google Sheets.

        Args:
            lead_id: ID заявки для пометки как синхронизированной
        """
        stmt = select(Lead).where(Lead.id == lead_id)
        result = await self.session.execute(stmt)
        lead = result.scalars().first()
        if lead:
            lead.synced_to_sheets = True
            await self.session.flush()

    async def get_page(self, page: int, page_size: int = 5) -> list[Lead]:
        """
        Получить заявки постранично, отсортированные от новых к старым.

        Args:
            page: номер страницы, начиная с 0
            page_size: количество заявок на странице

        Returns:
            Список объектов Lead для данной страницы
        """
        stmt = (
            select(Lead)
            .order_by(desc(Lead.created_at))
            .offset(page * page_size)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        """
        Подсчитать общее количество заявок.

        Returns:
            Количество заявок
        """
        from sqlalchemy import func
        stmt = select(func.count()).select_from(Lead)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
