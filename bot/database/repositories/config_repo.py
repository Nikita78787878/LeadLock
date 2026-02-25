"""Репозиторий для работы с конфигурацией бота."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.config import Config


class ConfigRepository:
    """Репозиторий для операций с моделью Config."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией.

        Args:
            session: AsyncSession для операций с БД
        """
        self.session = session

    async def get_by_key(self, key: str) -> Config | None:
        """
        Получить конфигурацию по ключу.

        Args:
            key: Ключ конфигурации

        Returns:
            Объект Config если найден, иначе None
        """
        stmt = select(Config).where(Config.key == key)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_value(self, key: str, default: str = "") -> str:
        """
        Получить значение конфигурации по ключу.

        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение конфигурации или default
        """
        config = await self.get_by_key(key)
        return config.value if config else default
