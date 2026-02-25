"""User repository for database operations."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User


class UserRepository:
    """Repository for User model operations."""

    def __init__(self, session: AsyncSession):
        """
        Initialize the repository with a session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def get_by_tg_id(self, telegram_id: int) -> User | None:
        """
        Get a user by telegram ID.

        Args:
            telegram_id: Telegram user ID

        Returns:
            User object if found, None otherwise
        """
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
    ) -> User:
        """
        Create a new user.

        Args:
            telegram_id: Telegram user ID
            username: Optional username
            full_name: Optional full name

        Returns:
            Created User object
        """
        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_user(
        self,
        telegram_id: int,
        username: str | None = None,
        full_name: str | None = None,
        is_blocked: bool | None = None,
    ) -> User | None:
        """
        Update an existing user.

        Args:
            telegram_id: Telegram user ID
            username: Optional new username
            full_name: Optional new full name
            is_blocked: Optional new blocked status

        Returns:
            Updated User object if found, None otherwise
        """
        user = await self.get_by_tg_id(telegram_id)
        if user is None:
            return None

        if username is not None:
            user.username = username
        if full_name is not None:
            user.full_name = full_name
        if is_blocked is not None:
            user.is_blocked = is_blocked

        await self.session.flush()
        return user
