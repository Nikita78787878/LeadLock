# LeadLock — Telegram-бот для управления заявками

Асинхронный Telegram-бот для автоматизации сбора и обработки клиентских заявок. Построен на **aiogram 3**, использует **PostgreSQL** для хранения данных, синхронизирует заявки с **Google Sheets** и предоставляет полноценную **панель администратора**.

Поддерживает три редакции через переменную окружения `VERSION`:

| Функция | LITE | PRO | AI |
|---------|:----:|:---:|:--:|
| Сбор заявок (FSM-форма) | ✅ | ✅ | ✅ |
| Управление FAQ | ✅ | ✅ | ✅ |
| Синхронизация с Google Sheets | ✅ | ✅ | ✅ |
| Панель администратора | ✅ | ✅ | ✅ |
| Смена статуса заявки (бот) | ✅ | ✅ | ✅ |
| Двусторонняя синхронизация статусов (Sheets ↔ DB) | ✅ | ✅ | ✅ |
| Система операторов / эстафета | ❌ | ✅ | ✅ |
| Массовые рассылки | ❌ | ✅ | ✅ |
| Дашборд аналитики (WebApp) | ❌ | ✅ | ✅ |
| AI-чат (OpenAI) | ❌ | ❌ | ✅ |

---

## Стек технологий

- **Python 3.12+**
- **aiogram 3** — асинхронный фреймворк для Telegram-ботов
- **SQLAlchemy 2 + asyncpg** — ORM и async-драйвер PostgreSQL
- **Alembic** — миграции базы данных
- **Pydantic v2 + pydantic-settings** — валидация и конфигурация
- **gspread + gspread-asyncio** — интеграция с Google Sheets
- **structlog** — структурированное логирование
- **Docker + docker-compose** — развёртывание

---

## Быстрый старт

### 1. Клонирование и установка зависимостей

```bash
git clone <repo-url>
cd LeadLock
pip install -r requirements.txt
```

### 2. Настройка окружения

```bash
cp .env.example .env
```

Заполни `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
VERSION=LITE                          # LITE / PRO / AI
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/leadlock_db
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_CREDENTIALS_JSON=/path/to/google-credentials.json
ADMIN_IDS=123456789,987654321
OPENAI_API_KEY=sk-...                 # только для VERSION=AI
LOG_LEVEL=INFO
```

### 3. Применение миграций

```bash
alembic upgrade head
```

### 4. Запуск

```bash
python main.py
```

### Docker (рекомендуется для локальной разработки)

```bash
docker-compose up        # поднять PostgreSQL + бот
docker-compose down      # остановить
```

---

## Архитектура

```
Telegram Update
    ↓
aiogram Dispatcher
    ↓
DbSessionMiddleware  ←  инжектирует AsyncSession в каждый хэндлер
AdminMiddleware      ←  защищает admin_router, проверяет ADMIN_IDS
    ↓
Handlers  (тонкий слой, делегирует логику)
    ↓
Services  (вся бизнес-логика, тестируема)
    ↓
Repositories  (только SQLAlchemy-запросы)
    ↓
PostgreSQL ──→ Google Sheets (async sync, двусторонняя)
              ↓
         Уведомление администратору

sheets_sync_loop() (фон, каждые 10 мин)
    ↓
Google Sheets (колонка «Статус») ──→ PostgreSQL
```

### Структура проекта

```
LeadLock/
├── main.py                        # Точка входа, регистрация роутеров и middleware
├── bot/
│   ├── settings.py                # Конфигурация (pydantic-settings)
│   ├── logging_config.py          # Настройка structlog (файлы + консоль)
│   ├── database/
│   │   ├── db_helper.py           # SQLAlchemy engine и фабрика сессий
│   │   ├── models/                # ORM-модели
│   │   └── repositories/          # Слой доступа к данным
│   ├── handlers/
│   │   ├── menu.py                # /start, главное меню, FAQ, услуги, контакты, локация
│   │   ├── lead_form.py           # FSM-форма сбора заявки
│   │   └── admin/                 # Панель администратора (заявки, FAQ, настройки)
│   ├── services/
│   │   ├── lead_service.py        # Валидация, сохранение, синхронизация статусов
│   │   ├── faq_service.py
│   │   ├── config_service.py
│   │   └── google_sheets_service.py
│   ├── keyboards/
│   │   ├── inline.py              # CallbackData-фабрики и inline-клавиатуры
│   │   └── reply.py               # Reply-клавиатуры (отмена, поделиться контактом)
│   ├── middlewares/               # DbSession и Admin middleware
│   ├── states/                    # FSM-состояния (LeadForm, FAQEdit, FAQAdd, ConfigEdit)
│   └── webapps/                   # WebApp HTML (PRO/AI)
├── alembic/                       # Миграции базы данных
└── tests/                         # Тесты (pytest + pytest-asyncio)
```

### Модели базы данных

| Модель | Назначение | Ключевые поля |
|--------|-----------|--------------|
| `User` | Пользователи | `telegram_id` (unique), `is_blocked` |
| `Lead` | Заявки | `user_id` FK, `name`, `phone`, `status` (`new`/`in_progress`/`closed`/`rejected`), `synced_to_sheets` |
| `FAQItem` | База FAQ | `question`, `answer`, `category`, `order`, `is_active` |
| `Operator` | Операторы (PRO/AI) | `telegram_id` (unique), `is_active` |
| `Config` | Настройки KV | `key` (unique), `value` |

---

## Поток сбора заявки (FSM)

```
/start → Главное меню
    ↓
[Оставить заявку]
    ↓
waiting_for_name → ввод имени (валидация)
    ↓
waiting_for_phone → ввод телефона (нормализация: 8XXXXXXXXXX → +7XXXXXXXXXX)
    ↓
waiting_for_description → описание проблемы
    ↓
Сохранение в PostgreSQL + Google Sheets + уведомление админу
```

---

## Команды разработки

```bash
# Форматирование кода
black bot/ main.py

# Линтинг
ruff bot/ main.py

# Проверка типов
mypy bot/ main.py

# Тесты
pytest
pytest --cov                                  # с покрытием
pytest tests/path/to/test_file.py::test_name  # один тест

# Миграции
alembic revision --autogenerate -m "описание"  # создать
alembic upgrade head                           # применить
alembic downgrade -1                           # откатить
```

---

## Настройка Google Sheets

1. Создай проект в [Google Cloud Console](https://console.cloud.google.com/).
2. Включи **Google Sheets API** и **Google Drive API**.
3. Создай сервисный аккаунт, скачай JSON-ключ.
4. Поделись таблицей с email сервисного аккаунта (права «Редактор»).
5. Укажи путь к JSON в `GOOGLE_CREDENTIALS_JSON` и ID таблицы в `GOOGLE_SHEET_ID`.

Лист «Заявки» с заголовками создаётся автоматически при первой синхронизации.

### Двусторонняя синхронизация статусов

Колонка **G («Статус»)** в таблице синхронизируется в обе стороны:

- **Бот → Sheets:** при смене статуса через кнопки в карточке заявки строка в таблице обновляется мгновенно.
- **Sheets → Бот:** фоновый процесс каждые **10 минут** читает статусы из таблицы и обновляет БД. Это позволяет оператору менять статус прямо в Google Sheets (например, во время обзвона) — и он автоматически появится в боте.

Допустимые значения в колонке «Статус»: `new`, `in_progress`, `closed`, `rejected`.

---

## Переменные окружения

| Переменная | Обязательна | Описание |
|-----------|:-----------:|---------|
| `BOT_TOKEN` | ✅ | Токен Telegram-бота ([@BotFather](https://t.me/BotFather)) |
| `VERSION` | ✅ | Редакция: `LITE`, `PRO` или `AI` |
| `DATABASE_URL` | ✅ | Строка подключения asyncpg |
| `ADMIN_IDS` | ✅ | Telegram ID администраторов через запятую |
| `GOOGLE_SHEET_ID` | ✅ | ID Google-таблицы |
| `GOOGLE_CREDENTIALS_JSON` | ✅ | Путь к JSON сервисного аккаунта |
| `OPENAI_API_KEY` | ⚠️ AI only | Ключ OpenAI API |
| `LOG_LEVEL` | ❌ | Уровень логирования (по умолчанию `INFO`) |

---

## Лицензия

MIT