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
- `menu.py` — `/start`, главное меню, просмотр FAQ
- `lead_form.py` — сбор заявки через FSM (имя → телефон → описание)
- `admin/` — суб-роутеры панели администратора (заявки с пагинацией, CRUD FAQ, настройки)

**Services** (`bot/services/`) — вся бизнес-логика:
- `lead_service.py` — валидация/нормализация имени и телефона, сохранение заявки, синхронизация с Sheets и уведомление админов
- `google_sheets_service.py` — async gspread клиент; автоматически создаёт лист "Заявки" с заголовками при первом использовании
- `faq_service.py` / `config_service.py` — тонкие обёртки над репозиториями

**Repositories** (`bot/database/repositories/`) — только SQLAlchemy-запросы, никакой логики

**FSM States** (`bot/states/`):
- `LeadForm` — `waiting_for_name`, `waiting_for_phone`, `waiting_for_description`
- Состояния для многошаговых потоков в панели администратора

### Модели базы данных
| Модель | Ключевые поля |
|--------|--------------|
| `User` | `telegram_id` (unique), `is_blocked` |
| `Lead` | `user_id` FK, `name`, `phone` (формат +7), `status`, `synced_to_sheets` |
| `FAQItem` | `question`, `answer`, `order`, `category`, `is_active` |
| `Config` | `key` (unique), `value` (текстовое KV-хранилище) |
| `Operator` | `telegram_id` (unique), `is_active` |

### Конфигурация
Настройки загружаются из `.env` через pydantic-settings (`bot/settings.py`). Перед запуском скопируй `.env.example` в `.env`. Ключевые переменные: `BOT_TOKEN`, `DATABASE_URL` (формат asyncpg), `GOOGLE_SHEET_ID`, `GOOGLE_CREDENTIALS_JSON` (путь к файлу), `ADMIN_IDS` (через запятую), `VERSION` (LITE/PRO/AI).

### Логирование
Используется `structlog`. Всегда используй async-методы логирования: `await logger.ainfo(...)`, `await logger.awarning(...)`, `await logger.aerror(...)`.

### Валидация телефона
Телефоны нормализуются к формату `+7XXXXXXXXXX` (12 символов). `8XXXXXXXXXX` → `+7XXXXXXXXXX` автоматически.