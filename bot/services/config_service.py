"""Сервисный слой для работы с конфигурацией."""

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.config_repo import ConfigRepository

logger = structlog.get_logger()


class ConfigService:
    """Сервис для работы с конфигурацией бота."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация сервиса.

        Args:
            session: AsyncSession для операций с БД
        """
        self.repository = ConfigRepository(session)

    async def get_welcome_text(self) -> str:
        """
        Получить приветственный текст из БД.

        Returns:
            Приветственный текст
        """
        try:
            text = await self.repository.get_value(
                "welcome_text",
                default="Добро пожаловать! 👋",
            )
            await logger.ainfo("Получен приветственный текст из конфигурации")
            return text
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении приветственного текста",
                error=str(e),
            )
            # Возвращаем дефолтное значение в случае ошибки
            return "Добро пожаловать! 👋"

    async def get_config_value(self, key: str, default: str = "") -> str:
        """
        Получить значение конфигурации по ключу.

        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию

        Returns:
            Значение конфигурации
        """
        try:
            value = await self.repository.get_value(key, default)
            await logger.ainfo(
                "Получено значение конфигурации",
                key=key,
            )
            return value
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении значения конфигурации",
                key=key,
                error=str(e),
            )
            return default

    async def set_value(self, key: str, value: str) -> None:
        """
        Установить значение конфигурации.

        Args:
            key: Ключ конфигурации
            value: Значение конфигурации
        """
        try:
            await self.repository.set_value(key, value)
            await logger.ainfo(
                "Значение конфигурации установлено",
                key=key,
            )
        except Exception as e:
            await logger.aerror(
                "Ошибка при установке значения конфигурации",
                key=key,
                error=str(e),
            )
            raise

    async def get_contacts(self) -> str:
        """
        Получить контактные данные из БД.

        Returns:
            Контактные данные
        """
        try:
            contacts = await self.repository.get_value(
                "contacts",
                default="Контакты не указаны",
            )
            await logger.ainfo("Получены контакты из конфигурации")
            return contacts
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении контактов",
                error=str(e),
            )
            return "Контакты не указаны"

    async def get_all_settings(self) -> list:
        """
        Получить все настройки.

        Returns:
            Список всех настроек
        """
        try:
            settings = await self.repository.get_all()
            await logger.ainfo(
                "Получены все настройки",
                count=len(settings),
            )
            return settings
        except Exception as e:
            await logger.aerror(
                "Ошибка при получении настроек",
                error=str(e),
            )
            return []
