"""Тесты для FAQService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.database.models.faq_item import FAQItem
from bot.services.faq_service import FAQService


def make_faq_item(
    id: int = 1,
    question: str = "Вопрос?",
    answer: str = "Ответ.",
    category: str = "faq",
    is_active: bool = True,
) -> FAQItem:
    item = FAQItem()
    item.id = id
    item.question = question
    item.answer = answer
    item.category = category
    item.is_active = is_active
    item.order = 0
    return item


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_all = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_by_category = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session, mock_repo):
    svc = FAQService(session=mock_session)
    svc.repository = mock_repo
    return svc


# ---------------------------------------------------------------------------
# get_all_faq_items
# ---------------------------------------------------------------------------


class TestGetAllFaqItems:
    async def test_returns_list_from_repo(self, service, mock_repo):
        items = [make_faq_item(id=1), make_faq_item(id=2)]
        mock_repo.get_all.return_value = items

        result = await service.get_all_faq_items()

        assert result == items
        mock_repo.get_all.assert_called_once()

    async def test_returns_empty_list_when_no_items(self, service, mock_repo):
        mock_repo.get_all.return_value = []

        result = await service.get_all_faq_items()

        assert result == []

    async def test_reraises_on_error(self, service, mock_repo):
        mock_repo.get_all.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            await service.get_all_faq_items()


# ---------------------------------------------------------------------------
# get_faq_item_by_id
# ---------------------------------------------------------------------------


class TestGetFaqItemById:
    async def test_returns_item_when_found(self, service, mock_repo):
        item = make_faq_item(id=5, question="Как оформить заявку?")
        mock_repo.get_by_id.return_value = item

        result = await service.get_faq_item_by_id(5)

        assert result is item
        mock_repo.get_by_id.assert_called_once_with(5)

    async def test_returns_none_when_not_found(self, service, mock_repo):
        mock_repo.get_by_id.return_value = None

        result = await service.get_faq_item_by_id(999)

        assert result is None

    async def test_reraises_on_error(self, service, mock_repo):
        mock_repo.get_by_id.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            await service.get_faq_item_by_id(1)


# ---------------------------------------------------------------------------
# get_faq_items_by_category
# ---------------------------------------------------------------------------


class TestGetFaqItemsByCategory:
    async def test_returns_items_for_category(self, service, mock_repo):
        items = [
            make_faq_item(id=1, category="general"),
            make_faq_item(id=2, category="general"),
        ]
        mock_repo.get_by_category.return_value = items

        result = await service.get_faq_items_by_category("general")

        assert result == items
        mock_repo.get_by_category.assert_called_once_with("general")

    async def test_returns_empty_list_for_unknown_category(self, service, mock_repo):
        mock_repo.get_by_category.return_value = []

        result = await service.get_faq_items_by_category("nonexistent")

        assert result == []

    async def test_reraises_on_error(self, service, mock_repo):
        mock_repo.get_by_category.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError):
            await service.get_faq_items_by_category("faq")
