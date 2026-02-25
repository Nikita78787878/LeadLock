"""Сервисный слой приложения."""

from .faq_service import FAQService
from .config_service import ConfigService

__all__ = ["FAQService", "ConfigService"]
