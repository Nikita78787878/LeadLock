"""Тесты для LeadService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.services.lead_service import VALID_STATUSES, LeadService
from tests.conftest import make_lead


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.create = AsyncMock()
    repo.get_by_id = AsyncMock()
    repo.get_all = AsyncMock()
    repo.get_recent = AsyncMock()
    repo.get_unsynced = AsyncMock()
    repo.update_status = AsyncMock()
    repo.mark_synced = AsyncMock()
    return repo


@pytest.fixture
def service(mock_session, mock_repo):
    svc = LeadService(session=mock_session)
    svc.repository = mock_repo
    return svc


@pytest.fixture
def mock_sheets():
    sheets = MagicMock()
    sheets.append_lead = AsyncMock()
    sheets.get_existing_ids = AsyncMock()
    sheets.get_statuses_from_sheets = AsyncMock()
    sheets.update_lead_status_in_sheets = AsyncMock()
    return sheets


@pytest.fixture
def service_with_sheets(mock_session, mock_repo, mock_sheets):
    svc = LeadService(session=mock_session, sheets_service=mock_sheets)
    svc.repository = mock_repo
    return svc, mock_repo, mock_sheets


# ---------------------------------------------------------------------------
# validate_name
# ---------------------------------------------------------------------------


class TestValidateName:
    def test_valid_cyrillic(self, service):
        ok, msg = service.validate_name("Иван Иванов")
        assert ok is True
        assert msg == ""

    def test_valid_latin(self, service):
        ok, msg = service.validate_name("Ivan Ivanov")
        assert ok is True

    def test_single_char_fails(self, service):
        ok, msg = service.validate_name("И")
        assert ok is False
        assert "минимум 2" in msg

    def test_empty_string_fails(self, service):
        ok, msg = service.validate_name("")
        assert ok is False

    def test_whitespace_only_fails(self, service):
        ok, msg = service.validate_name("   ")
        assert ok is False

    def test_too_long_fails(self, service):
        ok, msg = service.validate_name("А" * 51)
        assert ok is False
        assert "50" in msg

    def test_exactly_50_chars_ok(self, service):
        ok, msg = service.validate_name("А" * 50)
        assert ok is True

    def test_digits_fail(self, service):
        ok, msg = service.validate_name("Иван123")
        assert ok is False
        assert "буквы" in msg

    def test_special_chars_fail(self, service):
        ok, msg = service.validate_name("Иван@Иванов")
        assert ok is False


# ---------------------------------------------------------------------------
# normalize_phone
# ---------------------------------------------------------------------------


class TestNormalizePhone:
    def test_8_prefix_converted(self, service):
        assert service.normalize_phone("89991234567") == "+79991234567"

    def test_7_prefix_kept(self, service):
        assert service.normalize_phone("79991234567") == "+79991234567"

    def test_plus7_prefix_kept(self, service):
        assert service.normalize_phone("+79991234567") == "+79991234567"

    def test_dashes_and_parens_stripped(self, service):
        assert service.normalize_phone("8(999)123-45-67") == "+79991234567"

    def test_spaces_stripped(self, service):
        assert service.normalize_phone("8 999 123 45 67") == "+79991234567"

    def test_all_separators(self, service):
        assert service.normalize_phone("+7 (999) 123-45-67") == "+79991234567"


# ---------------------------------------------------------------------------
# validate_phone
# ---------------------------------------------------------------------------


class TestValidatePhone:
    def test_valid_phone(self, service):
        ok, msg = service.validate_phone("+79991234567")
        assert ok is True
        assert msg == ""

    def test_8_prefix_valid(self, service):
        # 8XXXXXXXXXX нормализуется → +7XXXXXXXXXX
        ok, msg = service.validate_phone("89991234567")
        assert ok is True

    def test_too_short_fails(self, service):
        ok, msg = service.validate_phone("+7999123456")  # 11 chars, 10 digits
        assert ok is False
        assert "11" in msg

    def test_too_long_fails(self, service):
        ok, msg = service.validate_phone("+799912345678")  # 13 chars
        assert ok is False

    def test_wrong_country_code_fails(self, service):
        ok, msg = service.validate_phone("+38099123456")  # Украина, 12 цифр
        assert ok is False
        assert "+7" in msg

    def test_formatted_phone_valid(self, service):
        ok, msg = service.validate_phone("8(999)123-45-67")
        assert ok is True


# ---------------------------------------------------------------------------
# VALID_STATUSES
# ---------------------------------------------------------------------------


class TestValidStatuses:
    def test_expected_statuses(self):
        assert VALID_STATUSES == {"new", "in_progress", "closed", "rejected"}


# ---------------------------------------------------------------------------
# save_lead
# ---------------------------------------------------------------------------


class TestSaveLead:
    async def test_save_lead_without_sheets(self, service, mock_repo):
        lead = make_lead()
        mock_repo.create.return_value = lead

        result = await service.save_lead(
            user_id=100,
            name="Иван Иванов",
            phone="89991234567",
            description="Описание",
        )

        mock_repo.create.assert_called_once_with(
            user_id=100,
            name="Иван Иванов",
            phone="+79991234567",
            description="Описание",
            status="new",
        )
        assert result is lead

    async def test_save_lead_normalizes_phone(self, service, mock_repo):
        lead = make_lead(phone="+79991234567")
        mock_repo.create.return_value = lead

        await service.save_lead(user_id=1, name="Тест", phone="8(999)123-45-67")

        _, kwargs = mock_repo.create.call_args
        assert kwargs["phone"] == "+79991234567"

    async def test_save_lead_with_sheets_marks_synced(
        self, service_with_sheets, sample_lead
    ):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_repo.create.return_value = sample_lead

        await svc.save_lead(
            user_id=100,
            name="Иван",
            phone="+79991234567",
        )

        mock_sheets.append_lead.assert_called_once_with(sample_lead)
        mock_repo.mark_synced.assert_called_once_with(sample_lead.id)

    async def test_save_lead_sheets_error_does_not_raise(
        self, service_with_sheets, sample_lead
    ):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_repo.create.return_value = sample_lead
        mock_sheets.append_lead.side_effect = Exception("Sheets недоступен")

        # Ошибка Sheets не должна выбрасываться
        result = await svc.save_lead(
            user_id=100,
            name="Иван",
            phone="+79991234567",
        )
        assert result is sample_lead
        mock_repo.mark_synced.assert_not_called()

    async def test_save_lead_repo_error_reraises(self, service, mock_repo):
        mock_repo.create.side_effect = RuntimeError("DB error")

        with pytest.raises(RuntimeError, match="DB error"):
            await service.save_lead(user_id=1, name="Иван", phone="+79991234567")

    async def test_save_lead_notifies_admins_if_bot_set(self, mock_session, mock_repo):
        mock_bot = AsyncMock()
        svc = LeadService(session=mock_session, bot=mock_bot)
        svc.repository = mock_repo

        lead = make_lead()
        mock_repo.create.return_value = lead

        with patch("bot.services.lead_service.settings") as mock_settings:
            mock_settings.ADMIN_IDS = [111, 222]
            await svc.save_lead(user_id=1, name="Иван", phone="+79991234567")

        assert mock_bot.send_message.call_count == 2


# ---------------------------------------------------------------------------
# update_lead_status
# ---------------------------------------------------------------------------


class TestUpdateLeadStatus:
    async def test_valid_status_updates_db(self, service, mock_repo, sample_lead):
        mock_repo.update_status.return_value = sample_lead

        result = await service.update_lead_status(1, "in_progress")

        mock_repo.update_status.assert_called_once_with(1, "in_progress")
        assert result is sample_lead

    async def test_invalid_status_raises(self, service):
        with pytest.raises(ValueError, match="Недопустимый статус"):
            await service.update_lead_status(1, "unknown_status")

    async def test_lead_not_found_returns_none(self, service, mock_repo):
        mock_repo.update_status.return_value = None

        result = await service.update_lead_status(999, "closed")

        assert result is None

    async def test_all_valid_statuses_accepted(self, service, mock_repo, sample_lead):
        mock_repo.update_status.return_value = sample_lead

        for status in VALID_STATUSES:
            result = await service.update_lead_status(1, status)
            assert result is sample_lead

    async def test_updates_sheets_on_status_change(
        self, service_with_sheets, sample_lead
    ):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_repo.update_status.return_value = sample_lead

        await svc.update_lead_status(1, "closed")

        mock_sheets.update_lead_status_in_sheets.assert_called_once_with(1, "closed")

    async def test_sheets_error_does_not_raise(self, service_with_sheets, sample_lead):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_repo.update_status.return_value = sample_lead
        mock_sheets.update_lead_status_in_sheets.side_effect = Exception("Sheets error")

        result = await svc.update_lead_status(1, "closed")
        assert result is sample_lead


# ---------------------------------------------------------------------------
# sync_unsynced_to_sheets
# ---------------------------------------------------------------------------


class TestSyncUnsyncedToSheets:
    async def test_no_sheets_service_returns_zero(self, service):
        result = await service.sync_unsynced_to_sheets()
        assert result == 0

    async def test_nothing_to_sync_returns_zero(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_repo.get_unsynced.return_value = []

        result = await svc.sync_unsynced_to_sheets()
        assert result == 0
        mock_sheets.append_lead.assert_not_called()

    async def test_syncs_all_unsynced(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        leads = [make_lead(id=1), make_lead(id=2), make_lead(id=3)]
        mock_repo.get_unsynced.return_value = leads

        result = await svc.sync_unsynced_to_sheets()

        assert result == 3
        assert mock_sheets.append_lead.call_count == 3
        assert mock_repo.mark_synced.call_count == 3

    async def test_partial_sync_on_error(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        leads = [make_lead(id=1), make_lead(id=2)]
        mock_repo.get_unsynced.return_value = leads
        # Первая заявка — ошибка, вторая — успех
        mock_sheets.append_lead.side_effect = [Exception("fail"), None]

        result = await svc.sync_unsynced_to_sheets()

        assert result == 1
        mock_repo.mark_synced.assert_called_once_with(2)


# ---------------------------------------------------------------------------
# export_to_sheets
# ---------------------------------------------------------------------------


class TestExportToSheets:
    async def test_no_sheets_service_returns_zero(self, service):
        result = await service.export_to_sheets()
        assert result == 0

    async def test_all_already_in_sheets(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        leads = [make_lead(id=1), make_lead(id=2)]
        mock_repo.get_all.return_value = leads
        mock_sheets.get_existing_ids.return_value = {1, 2}

        result = await svc.export_to_sheets()

        assert result == 0
        mock_sheets.append_lead.assert_not_called()

    async def test_exports_missing_leads(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        leads = [make_lead(id=1), make_lead(id=2), make_lead(id=3)]
        mock_repo.get_all.return_value = leads
        mock_sheets.get_existing_ids.return_value = {1}  # id=2 и id=3 отсутствуют

        result = await svc.export_to_sheets()

        assert result == 2
        assert mock_sheets.append_lead.call_count == 2

    async def test_empty_sheets_exports_all(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        leads = [make_lead(id=i) for i in range(1, 4)]
        mock_repo.get_all.return_value = leads
        mock_sheets.get_existing_ids.return_value = set()

        result = await svc.export_to_sheets()

        assert result == 3


# ---------------------------------------------------------------------------
# sync_statuses_from_sheets
# ---------------------------------------------------------------------------


class TestSyncStatusesFromSheets:
    async def test_no_sheets_service_returns_zero(self, service):
        result = await service.sync_statuses_from_sheets()
        assert result == 0

    async def test_empty_sheets_returns_zero(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_sheets.get_statuses_from_sheets.return_value = {}

        result = await svc.sync_statuses_from_sheets()
        assert result == 0

    async def test_updates_changed_statuses(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets

        lead1 = make_lead(id=1, status="new")
        lead2 = make_lead(id=2, status="new")
        mock_repo.get_all.return_value = [lead1, lead2]
        mock_sheets.get_statuses_from_sheets.return_value = {
            1: "closed",
            2: "new",  # не изменился
        }

        result = await svc.sync_statuses_from_sheets()

        assert result == 1
        mock_repo.update_status.assert_called_once_with(1, "closed")

    async def test_ignores_invalid_statuses_from_sheets(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets

        lead = make_lead(id=1, status="new")
        mock_repo.get_all.return_value = [lead]
        mock_sheets.get_statuses_from_sheets.return_value = {1: "invalid_status"}

        result = await svc.sync_statuses_from_sheets()

        assert result == 0
        mock_repo.update_status.assert_not_called()

    async def test_sheets_error_returns_zero(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets
        mock_sheets.get_statuses_from_sheets.side_effect = Exception("Sheets error")

        result = await svc.sync_statuses_from_sheets()
        assert result == 0

    async def test_no_update_if_status_same(self, service_with_sheets):
        svc, mock_repo, mock_sheets = service_with_sheets

        lead = make_lead(id=1, status="in_progress")
        mock_repo.get_all.return_value = [lead]
        mock_sheets.get_statuses_from_sheets.return_value = {1: "in_progress"}

        result = await svc.sync_statuses_from_sheets()

        assert result == 0
        mock_repo.update_status.assert_not_called()
