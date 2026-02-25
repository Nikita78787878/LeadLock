"""Сервисный слой для работы с Google Sheets."""

import structlog
from google.oauth2.service_account import Credentials
from gspread_asyncio import AsyncioGspreadClientManager
from gspread.exceptions import WorksheetNotFound

from bot.database.models.lead import Lead

logger = structlog.get_logger()


class GoogleSheetsService:
    """Сервис для работы с Google Sheets."""

    SCOPES = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    WORKSHEET_NAME = "Заявки"
    HEADERS = ["Дата", "Имя", "Телефон", "Описание", "User ID", "Статус"]

    def __init__(self, credentials_path: str, sheet_id: str):
        """
        Инициализация сервиса.

        Args:
            credentials_path: Путь к файлу учетных данных Google
            sheet_id: ID Google таблицы
        """
        self.credentials_path = credentials_path
        self.sheet_id = sheet_id
        self._client = None  # кэш клиента

    async def _get_client(self):
        """Получить или создать авторизованный клиент gspread."""
        if self._client is not None:
            return self._client

        try:
            # Загрузить учетные данные из файла
            credentials = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=self.SCOPES,
            )

            # Создать асинхронный менеджер клиента
            auth_manager = AsyncioGspreadClientManager(auth=credentials)
            self._client = await auth_manager.authorize()

            await logger.ainfo(
                "Авторизация в Google Sheets выполнена успешно",
            )

            return self._client
        except Exception as e:
            await logger.aerror(
                "Ошибка при авторизации в Google Sheets",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    async def append_lead(self, lead: Lead) -> None:
        """Добавить заявку в Google Sheets."""
        try:
            # Получить клиент
            client = await self._get_client()

            # Открыть таблицу по ID
            spreadsheet = await client.open_by_key(self.sheet_id)

            # Попробовать открыть лист "Заявки"
            try:
                worksheet = await spreadsheet.worksheet(self.WORKSHEET_NAME)
            except WorksheetNotFound:
                # Если лист не существует — создать с заголовками
                worksheet = await spreadsheet.add_worksheet(
                    self.WORKSHEET_NAME,
                    rows=1000,
                    cols=len(self.HEADERS),
                )
                await worksheet.append_row(self.HEADERS)
                await logger.ainfo(
                    "Создан новый лист в Google Sheets",
                    worksheet_name=self.WORKSHEET_NAME,
                    headers=self.HEADERS,
                )

            # Подготовить строку с данными заявки
            row = [
                lead.created_at.strftime("%d.%m.%Y %H:%M"),
                lead.name,
                lead.phone,
                lead.description or "",
                str(lead.user_id),
                lead.status,
            ]

            # Добавить строку в таблицу
            await worksheet.append_row(row)

            await logger.ainfo(
                "Заявка добавлена в Google Sheets",
                lead_id=lead.id,
                user_id=lead.user_id,
                name=lead.name,
            )
        except Exception as e:
            # При ЛЮБОЙ ошибке только логировать, не бросать
            await logger.aerror(
                "Ошибка при добавлении заявки в Google Sheets",
                lead_id=lead.id,
                user_id=lead.user_id,
                error=str(e),
                error_type=type(e).__name__,
            )

    async def health_check(self) -> bool:
        """Проверить соединение с Google Sheets."""
        try:
            # Получить клиент
            client = await self._get_client()

            # Открыть таблицу и получить список листов
            spreadsheet = await client.open_by_key(self.sheet_id)
            worksheets = await spreadsheet.worksheets()

            await logger.ainfo(
                "Проверка соединения с Google Sheets успешна",
                worksheets_count=len(worksheets),
            )
            return True
        except Exception as e:
            # При ошибке только логировать и вернуть False
            await logger.aerror(
                "Ошибка при проверке соединения с Google Sheets",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
