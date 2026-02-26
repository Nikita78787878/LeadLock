"""
Основной модуль запуска Telegram бота.

Инициализирует диспетчер, регистрирует роутеры и запускает поллинг.
"""

import asyncio
from typing import Any, Awaitable, Callable

import structlog
from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.db_helper import async_session_maker, close_engine
from bot.handlers.admin import router as admin_router
from bot.handlers.lead_form import router as lead_form_router
from bot.handlers.menu import router as menu_router
from bot.middlewares.admin_middleware import AdminMiddleware
from bot.services.google_sheets_service import GoogleSheetsService
from bot.settings import settings

# Инициализация логгера
logger = structlog.get_logger(__name__)


# ============================================================================
# Middleware для управления сессией БД
# ============================================================================


class DbSessionMiddleware(BaseMiddleware):
    """
    Middleware для внедрения сессии БД в данные обработчика.

    Создаёт новую сессию БД для каждого события и делает её доступной
    для обработчиков через data["session"].
    """

    def __init__(self, session_factory):
        """
        Инициализация middleware.

        Args:
            session_factory: Factory для создания AsyncSession объектов
        """
        super().__init__()
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Выполняет middleware логику.

        Args:
            handler: Основной обработчик события
            event: Событие от Telegram
            data: Дополнительные данные

        Returns:
            Результат выполнения handler'а
        """
        # Создаём новую сессию для этого события
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)


# ============================================================================
# Обработчики жизненного цикла
# ============================================================================


async def on_startup(bot: Bot) -> None:
    """
    Функция инициализации при запуске бота.

    Инициализирует сервисы, проверяет подключения и логирует начало работы.

    Args:
        bot: Экземпляр бота
    """
    await logger.ainfo("🤖 Бот запускается...")

    try:
        # Создаём таблицы если не существуют
        from bot.database.db_helper import engine
        from bot.database.models.base import Base
        from bot.database.models import User, Lead, FAQItem, Config, Operator

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await logger.ainfo("✅ Таблицы БД проверены/созданы")

        # Инициализируем сервис Google Sheets
        sheets_service = GoogleSheetsService(
            credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
            sheet_id=settings.GOOGLE_SHEET_ID,
        )

        # Проверяем доступность Google Sheets
        try:
            health_check_result = await sheets_service.health_check()
        except FileNotFoundError as fnf:
            # Понятное сообщение при ошибочном пути к credentials
            await logger.awarning(
                "⚠️ Файл учетных данных Google не найден. Проверьте переменную окружения GOOGLE_CREDENTIALS_JSON в .env",
                credentials_path=str(settings.GOOGLE_CREDENTIALS_JSON),
                error=str(fnf),
            )
            # Разрешаем боту продолжить работу без интеграции с Google Sheets
            health_check_result = False

        if health_check_result:
            await logger.ainfo(
                "✅ Google Sheets сервис доступен",
                sheet_id=settings.GOOGLE_SHEET_ID,
            )
        else:
            await logger.awarning(
                "⚠️ Google Sheets сервис недоступен",
                sheet_id=settings.GOOGLE_SHEET_ID,
            )

        await logger.ainfo("✅ Бот успешно запущен")

    except Exception as e:
        await logger.aerror(
            "❌ Ошибка при запуске бота",
            error=str(e),
            exc_info=True,
        )
        raise


async def on_shutdown(bot: Bot) -> None:
    """
    Функция остановки при отключении бота.

    Закрывает все соединения и освобождает ресурсы.

    Args:
        bot: Экземпляр бота
    """
    await logger.ainfo("🔴 Бот останавливается...")

    try:
        # Закрываем engine и все соединения БД
        await close_engine()
        await logger.ainfo("✅ Бот успешно остановлен")
    except Exception as e:
        await logger.aerror(
            "❌ Ошибка при остановке бота",
            error=str(e),
            exc_info=True,
        )


# ============================================================================
# Инициализация приложения
# ============================================================================


async def main() -> None:
    """
    Основная функция инициализации и запуска бота.

    Создаёт бота, диспетчер, регистрирует роутеры и запускает поллинг.
    """
    await logger.ainfo(
        "🚀 Инициализация приложения",
        version=settings.VERSION,
        bot_token_exists=bool(settings.BOT_TOKEN),
    )

    # Создаём экземпляр бота с HTML парсингом по умолчанию
    bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)

    # Инициализируем диспетчер с MemoryStorage для FSM
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем обработчики жизненного цикла
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Регистрируем middleware для управления сессией БД
    # Это должно быть первым middleware для обеспечения сессии для остальных
    dp.update.middleware(DbSessionMiddleware(async_session_maker))

    # ========================================================================
    # Регистрация роутеров
    # ========================================================================

    # 1. Admin роутер с AdminMiddleware
    # AdminMiddleware проверяет права администратора перед каждым обработчиком
    admin_router.message.middleware(AdminMiddleware())
    admin_router.callback_query.middleware(AdminMiddleware())
    dp.include_router(admin_router)

    await logger.ainfo("✅ Admin роутер зарегистрирован")

    # 2. Lead Form роутер (форма заявок)
    dp.include_router(lead_form_router)
    await logger.ainfo("✅ Menu роутер зарегистрирован")

    # 3. Menu роутер (общедоступное меню)
    dp.include_router(menu_router)
    await logger.ainfo("✅ Lead Form роутер зарегистрирован")

    # ========================================================================
    # Запуск поллинга
    # ========================================================================

    await logger.ainfo("📡 Запуск поллинга...")

    try:
        # Запускаем поллинг и ждём завершения
        # drop_pending_updates=True игнорирует старые сообщения
        await dp.start_polling(
            bot,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
    except Exception as e:
        await logger.aerror(
            "❌ Ошибка при запуске поллинга",
            error=str(e),
            exc_info=True,
        )
        raise
    finally:
        # Гарантируем закрытие сессии бота
        await bot.session.close()


# ============================================================================
# Точка входа
# ============================================================================


if __name__ == "__main__":
    asyncio.run(main())
