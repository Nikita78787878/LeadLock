# CLAUDE.md

Этот файл содержит инструкции для Claude Code (claude.ai/code) при работе с данным репозиторием.

## Обзор проекта

LeadLock — асинхронный Telegram-бот для управления заявками, построен на aiogram 3. Собирает заявки через многошаговую FSM-форму, сохраняет в PostgreSQL, синхронизирует с Google Sheets и предоставляет панель администратора. Поддерживает редакции LITE/PRO/AI через переменную окружения `VERSION`.

## Основные команды

```bash
# Установка зависимостей
pip install -r requirements.txt

# Применить миграции базы данных
alembic upgrade head

# Запустить бота
python main.py

# Создать новую миграцию после изменения моделей
alembic revision --autogenerate -m "описание"

# Откатить последнюю миграцию
alembic downgrade -1

# Форматирование кода
black bot/ main.py

# Линтинг
ruff bot/ main.py

# Проверка типов
mypy bot/ main.py

# Запуск тестов
pytest
pytest tests/путь/к/test_file.py::test_name  # один тест
pytest --cov                                  # с покрытием

# Docker (PostgreSQL + Bot)
docker-compose up
docker-compose down
```

## Архитектура

### Поток запроса
```
Telegram Update → aiogram Router → Handler → Service → Repository → PostgreSQL
                                                      ↓
                                               Google Sheets (async sync)
                                                      ↓
                                          Уведомление админу (Telegram)
```

### Основные слои

**Middleware** (`bot/middlewares/`) — выполняется перед каждым хэндлером:
- `DbSessionMiddleware` — внедряет `AsyncSession` в `data["session"]` для каждого события
- `AdminMiddleware` — защищает `admin_router`, проверяя `ADMIN_IDS`

**Handlers** (`bot/handlers/`) — aiogram-роутеры, тонкий слой, делегирующий логику сервисам:
- `menu.py` — `/start`, главное меню, FAQ, услуги, контакты, локация, навигация «назад»
- `lead_form.py` — сбор заявки через FSM (имя → телефон → описание)
- `admin/menu.py` — `/admin`, главное меню панели администратора
- `admin/leads.py` — список заявок с пагинацией, смена статуса
- `admin/faq.py` — CRUD FAQ (добавить/редактировать/удалить)
- `admin/settings.py` — редактирование конфигурации (welcome-текст, контакты, локация, maps URL)
- `admin/helpers.py` — вспомогательные функции для admin-хэндлеров

**Services** (`bot/services/`) — вся бизнес-логика:
- `lead_service.py` — валидация/нормализация имени и телефона, сохранение заявки, смена статуса (`update_lead_status`), синхронизация с Sheets (`sync_statuses_from_sheets`) и уведомление админов. Константа `VALID_STATUSES` определяет допустимые статусы.
- `google_sheets_service.py` — async gspread клиент; автоматически создаёт лист "Заявки" с заголовками при первом использовании; методы `get_statuses_from_sheets` и `update_lead_status_in_sheets` обеспечивают двустороннюю синхронизацию статусов.
- `faq_service.py` / `config_service.py` — тонкие обёртки над репозиториями

**Repositories** (`bot/database/repositories/`) — только SQLAlchemy-запросы, никакой логики

**Keyboards** (`bot/keyboards/`):
- `inline.py` — CallbackData-фабрики (`MainMenuCD`, `FAQItemCD`, `ServiceItemCD`, `BackCD`) и функции генерации inline-клавиатур
- `reply.py` — reply-клавиатуры (кнопка «Отмена», кнопка «Поделиться контактом»)

**FSM States** (`bot/states/`):
- `LeadForm` — `waiting_for_name`, `waiting_for_phone`, `waiting_for_description`
- `FAQEdit` — `selecting_item`, `waiting_for_question`, `waiting_for_answer`
- `FAQAdd` — `waiting_for_category`, `waiting_for_question`, `waiting_for_answer`
- `ConfigEdit` — `waiting_for_welcome`, `waiting_for_contacts`, `waiting_for_location`, `waiting_for_maps_url`

### Модели базы данных
| Модель | Ключевые поля |
|--------|--------------|
| `User` | `telegram_id` (unique), `is_blocked` |
| `Lead` | `user_id` FK, `name`, `phone` (формат +7), `status`, `synced_to_sheets` |
| `FAQItem` | `question`, `answer`, `order`, `category`, `is_active` |
| `Config` | `key` (unique), `value` (текстовое KV-хранилище) |
| `Operator` | `telegram_id` (unique), `is_active` |

### Конфигурация
Настройки загружаются из `.env` через pydantic-settings (`bot/settings.py`). Перед запуском скопируй `.env.example` в `.env`. Ключевые переменные: `BOT_TOKEN`, `DATABASE_URL` (формат asyncpg), `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` (путь к файлу), `ADMIN_IDS` (через запятую), `VERSION` (LITE/PRO/AI), `OPENAI_API_KEY` (только для AI), `LOG_LEVEL` (по умолчанию `INFO`).

### Логирование
Настройка в `bot/logging_config.py`. Используется `structlog`. Файлы: `logs/app.log` (DEBUG+, ротация 30 дней), `logs/errors.log` (ERROR+, ротация 90 дней). Всегда используй async-методы логирования: `await logger.ainfo(...)`, `await logger.awarning(...)`, `await logger.aerror(...)`. Логгеры aiogram/aiohttp/asyncio заглушены до WARNING.

### Валидация телефона
Телефоны нормализуются к формату `+7XXXXXXXXXX` (12 символов). `8XXXXXXXXXX` → `+7XXXXXXXXXX` автоматически.

### Статусы заявок
Допустимые значения (`VALID_STATUSES` в `lead_service.py`): `new`, `in_progress`, `closed`, `rejected`. Статус меняется через кнопки в карточке заявки (бот) или вручную в колонке G Google Sheets.

### Двусторонняя синхронизация статусов (Sheets ↔ DB)
- **Бот → Sheets:** `LeadService.update_lead_status` обновляет БД и вызывает `GoogleSheetsService.update_lead_status_in_sheets` — ищет строку по ID в колонке 1, обновляет колонку 7.
- **Sheets → DB:** фоновая корутина `sheets_sync_loop()` в `main.py` запускается при старте бота и каждые 600 секунд вызывает `LeadService.sync_statuses_from_sheets`. Таск хранится в `_sync_task` и gracefully отменяется при shutdown.

### Тесты
Тесты в `tests/`, конфигурация через `pyproject.toml` (`asyncio_mode = "auto"`). Общие фикстуры в `tests/conftest.py`: `mock_session` (AsyncMock), `sample_lead` (Lead без БД). Переменные окружения для тестов задаются через `os.environ.setdefault` в начале `conftest.py` до импорта модулей бота.