"""Тесты для ConfigService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.services.config_service import ConfigService


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_value = AsyncMock()
    repo.set_value = AsyncMock()
    repo.get_all = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session, mock_repo):
    svc = ConfigService(session=mock_session)
    svc.repository = mock_repo
    return svc


# ---------------------------------------------------------------------------
# get_welcome_text
# ---------------------------------------------------------------------------


class TestGetWelcomeText:
    async def test_returns_value_from_repo(self, service, mock_repo):
        mock_repo.get_value.return_value = "Привет!"

        result = await service.get_welcome_text()

        assert result == "Привет!"
        mock_repo.get_value.assert_called_once_with("welcome_text", default="Добро пожаловать! 👋")

    async def test_returns_default_on_error(self, service, mock_repo):
        mock_repo.get_value.side_effect = Exception("DB error")

        result = await service.get_welcome_text()

        assert result == "Добро пожаловать! 👋"


# ---------------------------------------------------------------------------
# get_contacts
# ---------------------------------------------------------------------------


class TestGetContacts:
    async def test_returns_value_from_repo(self, service, mock_repo):
        mock_repo.get_value.return_value = "+7 (999) 000-00-00"

        result = await service.get_contacts()

        assert result == "+7 (999) 000-00-00"
        mock_repo.get_value.assert_called_once_with("contacts", default="Контакты не указаны")

    async def test_returns_default_on_error(self, service, mock_repo):
        mock_repo.get_value.side_effect = Exception("DB error")

        result = await service.get_contacts()

        assert result == "Контакты не указаны"


# ---------------------------------------------------------------------------
# get_config_value
# ---------------------------------------------------------------------------


class TestGetConfigValue:
    async def test_returns_stored_value(self, service, mock_repo):
        mock_repo.get_value.return_value = "some_value"

        result = await service.get_config_value("some_key", default="fallback")

        assert result == "some_value"

    async def test_returns_custom_default_on_error(self, service, mock_repo):
        mock_repo.get_value.side_effect = Exception("DB error")

        result = await service.get_config_value("key", default="my_default")

        assert result == "my_default"

    async def test_default_is_empty_string(self, service, mock_repo):
        mock_repo.get_value.side_effect = Exception("DB error")

        result = await service.get_config_value("key")

        assert result == ""


# ---------------------------------------------------------------------------
# set_value
# ---------------------------------------------------------------------------


class TestSetValue:
    async def test_calls_repo_set_value(self, service, mock_repo):
        await service.set_value("welcome_text", "Привет!")

        mock_repo.set_value.assert_called_once_with("welcome_text", "Привет!")

    async def test_reraises_on_error(self, service, mock_repo):
        mock_repo.set_value.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            await service.set_value("key", "value")


# ---------------------------------------------------------------------------
# get_all_settings
# ---------------------------------------------------------------------------


class TestGetAllSettings:
    async def test_returns_list_from_repo(self, service, mock_repo):
        mock_settings = [MagicMock(), MagicMock()]
        mock_repo.get_all.return_value = mock_settings

        result = await service.get_all_settings()

        assert result == mock_settings

    async def test_returns_empty_list_on_error(self, service, mock_repo):
        mock_repo.get_all.side_effect = Exception("DB error")

        result = await service.get_all_settings()

        assert result == []
