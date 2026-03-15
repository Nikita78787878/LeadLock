"""Общие фикстуры для тестов.

ВАЖНО: переменные окружения нужно задать ДО импорта любых модулей бота,
потому что bot/settings.py вызывает Settings() на уровне модуля.
"""

import os

os.environ.setdefault("BOT_TOKEN", "1234567890:AAEtest_token_for_tests_only")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/testdb")
os.environ.setdefault("VERSION", "LITE")
os.environ.setdefault("GOOGLE_SHEET_ID", "test_sheet_id")
os.environ.setdefault("GOOGLE_CREDENTIALS_JSON", "test_credentials.json")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
os.environ.setdefault("ADMIN_IDS", "[123456789, 987654321]")

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from bot.database.models.lead import Lead


def make_lead(
    id: int = 1,
    user_id: int = 100,
    name: str = "Иван Иванов",
    phone: str = "+79991234567",
    description: str = "Тестовая заявка",
    status: str = "new",
    synced_to_sheets: bool = False,
) -> Lead:
    """Создать объект Lead без обращения к БД."""
    lead = Lead()
    lead.id = id
    lead.user_id = user_id
    lead.name = name
    lead.phone = phone
    lead.description = description
    lead.status = status
    lead.synced_to_sheets = synced_to_sheets
    lead.created_at = datetime(2026, 3, 15, 12, 0, 0)
    return lead


@pytest.fixture
def mock_session():
    """Мок AsyncSession."""
    return AsyncMock()


@pytest.fixture
def sample_lead():
    """Образец заявки для тестов."""
    return make_lead()
