import structlog
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from bot.settings import settings

# Инициализация логгера
logger = structlog.get_logger(__name__)


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Проверяет права администратора перед выполнением обработчика.
        
        Args:
            handler: основной обработчик события
            event: событие (Message, CallbackQuery и т.д.)
            data: дополнительные данные
            
        Returns:
            Результат выполнения handler или None в случае отсутствия доступа
        """
        # Получить user из event
        user = None
        user_id = None
        is_message = isinstance(event, Message)
        is_callback = isinstance(event, CallbackQuery)

        if is_message:
            user = event.from_user
            user_id = event.from_user.id if event.from_user else None
        elif is_callback:
            user = event.from_user
            user_id = event.from_user.id if event.from_user else None
        else:
            # Для других типов событий пытаемся получить from_user
            user = getattr(event, "from_user", None)
            user_id = getattr(user, "id", None) if user else None

        # Логирование попытки доступа
        logger.debug(
            "admin_check_attempt",
            user_id=user_id,
            is_admin=user_id in settings.ADMIN_IDS if user_id else False,
            event_type=type(event).__name__,
        )

        # Проверить user.id в settings.ADMIN_IDS
        if user_id is None or user_id not in settings.ADMIN_IDS:
            # Логирование отказа в доступе
            logger.warning(
                "admin_access_denied",
                user_id=user_id,
                event_type=type(event).__name__,
            )

            # Если не админ: отправить сообщение об ошибке
            if is_message:
                await event.answer("⛔ Нет доступа")
            elif is_callback:
                await event.answer("⛔ Нет доступа", show_alert=True)

            return None

        # Логирование успешной проверки доступа
        logger.info(
            "admin_access_granted",
            user_id=user_id,
            event_type=type(event).__name__,
        )

        # Если админ: выполнить основной обработчик
        return await handler(event, data)
