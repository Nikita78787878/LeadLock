"""Тесты для GoogleSheetsService."""

from unittest.mock import AsyncMock, patch

import pytest

from bot.services.google_sheets_service import GoogleSheetsService
from tests.conftest import make_lead


@pytest.fixture
def service():
    return GoogleSheetsService(
        credentials_path="test_credentials.json",
        sheet_id="test_sheet_id",
    )


@pytest.fixture
def mock_worksheet():
    ws = AsyncMock()
    ws.append_row = AsyncMock()
    ws.col_values = AsyncMock()
    ws.get_all_values = AsyncMock()
    ws.update_cell = AsyncMock()
    return ws


@pytest.fixture
def mock_spreadsheet(mock_worksheet):
    ss = AsyncMock()
    ss.worksheet = AsyncMock(return_value=mock_worksheet)
    ss.add_worksheet = AsyncMock(return_value=mock_worksheet)
    return ss


@pytest.fixture
def mock_client(mock_spreadsheet):
    client = AsyncMock()
    client.open_by_key = AsyncMock(return_value=mock_spreadsheet)
    return client


# ---------------------------------------------------------------------------
# get_existing_ids
# ---------------------------------------------------------------------------


class TestGetExistingIds:
    async def test_returns_ids_from_column(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID", "1", "2", "3"]
        service._client = mock_client

        result = await service.get_existing_ids()

        assert result == {1, 2, 3}

    async def test_skips_header_row(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID", "10", "20"]
        service._client = mock_client

        result = await service.get_existing_ids()

        assert "ID" not in str(result)
        assert result == {10, 20}

    async def test_skips_non_integer_values(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID", "1", "abc", "", "3"]
        service._client = mock_client

        result = await service.get_existing_ids()

        assert result == {1, 3}

    async def test_empty_sheet_returns_empty_set(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID"]
        service._client = mock_client

        result = await service.get_existing_ids()

        assert result == set()

    async def test_worksheet_not_found_returns_empty_set(
        self, service, mock_client, mock_spreadsheet
    ):
        from gspread.exceptions import WorksheetNotFound

        mock_spreadsheet.worksheet.side_effect = WorksheetNotFound("Заявки")
        service._client = mock_client

        result = await service.get_existing_ids()

        assert result == set()


# ---------------------------------------------------------------------------
# get_statuses_from_sheets
# ---------------------------------------------------------------------------


class TestGetStatusesFromSheets:
    async def test_returns_status_dict(self, service, mock_client, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["ID", "Дата", "Имя", "Телефон", "Описание", "User ID", "Статус"],
            ["1", "15.03.2026", "Иван", "+79991234567", "Текст", "100", "closed"],
            ["2", "15.03.2026", "Пётр", "+79991234568", "Текст", "101", "in_progress"],
        ]
        service._client = mock_client

        result = await service.get_statuses_from_sheets()

        assert result == {1: "closed", 2: "in_progress"}

    async def test_skips_rows_with_empty_status(self, service, mock_client, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["ID", "Дата", "Имя", "Телефон", "Описание", "User ID", "Статус"],
            ["1", "15.03.2026", "Иван", "+79991234567", "Текст", "100", ""],
            ["2", "15.03.2026", "Пётр", "+79991234568", "Текст", "101", "new"],
        ]
        service._client = mock_client

        result = await service.get_statuses_from_sheets()

        assert 1 not in result
        assert result[2] == "new"

    async def test_skips_rows_shorter_than_7_cols(self, service, mock_client, mock_worksheet):
        mock_worksheet.get_all_values.return_value = [
            ["ID", "Дата", "Имя", "Телефон", "Описание", "User ID", "Статус"],
            ["1", "15.03.2026", "Иван"],  # строка слишком короткая
        ]
        service._client = mock_client

        result = await service.get_statuses_from_sheets()

        assert result == {}

    async def test_worksheet_not_found_returns_empty_dict(
        self, service, mock_client, mock_spreadsheet
    ):
        from gspread.exceptions import WorksheetNotFound

        mock_spreadsheet.worksheet.side_effect = WorksheetNotFound("Заявки")
        service._client = mock_client

        result = await service.get_statuses_from_sheets()

        assert result == {}


# ---------------------------------------------------------------------------
# update_lead_status_in_sheets
# ---------------------------------------------------------------------------


class TestUpdateLeadStatusInSheets:
    async def test_updates_correct_cell(self, service, mock_client, mock_worksheet):
        # ID 2 находится на строке 3 (индекс 1 в данных + 2 для пропуска заголовка)
        mock_worksheet.col_values.return_value = ["ID", "1", "2", "3"]
        service._client = mock_client

        await service.update_lead_status_in_sheets(lead_id=2, status="closed")

        mock_worksheet.update_cell.assert_called_once_with(3, 7, "closed")

    async def test_updates_first_match(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID", "5"]
        service._client = mock_client

        await service.update_lead_status_in_sheets(lead_id=5, status="rejected")

        mock_worksheet.update_cell.assert_called_once_with(2, 7, "rejected")

    async def test_no_update_if_id_not_found(self, service, mock_client, mock_worksheet):
        mock_worksheet.col_values.return_value = ["ID", "1", "2"]
        service._client = mock_client

        await service.update_lead_status_in_sheets(lead_id=999, status="closed")

        mock_worksheet.update_cell.assert_not_called()

    async def test_worksheet_not_found_does_not_raise(
        self, service, mock_client, mock_spreadsheet
    ):
        from gspread.exceptions import WorksheetNotFound

        mock_spreadsheet.worksheet.side_effect = WorksheetNotFound("Заявки")
        service._client = mock_client

        # Не должно выбрасывать исключение
        await service.update_lead_status_in_sheets(lead_id=1, status="closed")


# ---------------------------------------------------------------------------
# append_lead
# ---------------------------------------------------------------------------


class TestAppendLead:
    async def test_appends_row_with_correct_data(
        self, service, mock_client, mock_worksheet, mock_spreadsheet
    ):
        service._client = mock_client
        lead = make_lead(id=1, user_id=100, name="Иван", phone="+79991234567")

        await service.append_lead(lead)

        mock_worksheet.append_row.assert_called_once()
        row = mock_worksheet.append_row.call_args[0][0]
        assert row[0] == "1"
        assert row[2] == "Иван"
        assert row[3] == "+79991234567"
        assert row[5] == "100"
        assert row[6] == "new"

    async def test_creates_worksheet_if_not_found(
        self, service, mock_client, mock_spreadsheet, mock_worksheet
    ):
        from gspread.exceptions import WorksheetNotFound

        mock_spreadsheet.worksheet.side_effect = WorksheetNotFound("Заявки")
        mock_spreadsheet.add_worksheet.return_value = mock_worksheet
        service._client = mock_client

        lead = make_lead()
        await service.append_lead(lead)

        mock_spreadsheet.add_worksheet.assert_called_once()
        # Первый вызов append_row — заголовки, второй — данные
        assert mock_worksheet.append_row.call_count == 2

    async def test_empty_description_uses_empty_string(
        self, service, mock_client, mock_worksheet
    ):
        service._client = mock_client
        lead = make_lead(description=None)

        await service.append_lead(lead)

        row = mock_worksheet.append_row.call_args[0][0]
        assert row[4] == ""


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


class TestHealthCheck:
    async def test_returns_true_on_success(self, service, mock_client):
        service._client = mock_client

        result = await service.health_check()

        assert result is True

    async def test_returns_false_on_error(self, service):
        service._client = None

        with patch.object(service, "_get_client", side_effect=Exception("no connection")):
            result = await service.health_check()

        assert result is False
