# 🤖 Modular Business Telegram Bot (LITE/PRO/AI-Edition)

> Scalable, production-ready Telegram bot for small and medium businesses with support for FAQ automation, lead generation, and AI-powered customer support.

**Language:** English • **Code Comments:** Russian • **Target Audience:** Russian market (SMB automation)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API & Integration](#api--integration)
- [Development Guide](#development-guide)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

This project implements a **modular Telegram bot** designed to automate business processes for small and medium enterprises (SMEs) in the Russian market. The bot operates in three distinct modes:

### **LITE Edition** — Essential Communication
- FAQ-based information retrieval
- Lead generation through forms
- Basic user management
- Admin panel for FAQ editing

### **PRO Edition** — Advanced Team Management
- Everything in LITE +
- **Operator relay system** (user ↔ bot ↔ operator)
- Team management interface
- Broadcast system (text + media)
- Basic analytics dashboard (Telegram WebApp)

### **AI-Edition** — Intelligent Automation
- Everything in PRO +
- **LLM integration** (OpenAI / GigaChat API)
- Context-aware responses with RAG support
- Hybrid mode (AI → escalate to operator if needed)
- System prompt management via admin interface

The bot is **highly modular** and follows SOLID/DRY/KISS principles. You can deploy the same codebase with different feature sets just by changing the `VERSION` environment variable.

---

## ✨ Key Features

### Core Functionality

| Feature | LITE | PRO | AI-Edition |
|---------|:----:|:---:|:---------:|
| **FAQ Management** | ✅ | ✅ | ✅ |
| **Lead Generation Forms** | ✅ | ✅ | ✅ |
| **Google Sheets Integration** | ✅ | ✅ | ✅ |
| **Admin Panel in Telegram** | ✅ | ✅ | ✅ |
| **Operator Relay System** | ❌ | ✅ | ✅ |
| **Broadcast to Users** | ❌ | ✅ | ✅ |
| **Analytics Dashboard** | ❌ | ✅ | ✅ |
| **AI Chat Integration** | ❌ | ❌ | ✅ |
| **Hybrid Escalation** | ❌ | ❌ | ✅ |

### Technical Highlights

- ⚡ **Async/Await** architecture (aiogram 3.x)
- 🗄️ **PostgreSQL** with SQLAlchemy ORM
- 🔐 **Permission middleware** (admin/operator roles)
- 📊 **Structured logging** with Russian fluent messages
- 🎯 **FSM-based workflows** for complex user interactions
- 🔄 **Repository pattern** for clean data access
- 📦 **Pydantic v2** for robust data validation
- 🐳 **Docker & Docker Compose** ready
- 🧪 **Pytest** compatible test structure

---

## 🏗️ Architecture

### Design Principles

```
┌─────────────────────────────────────────────────┐
│           Telegram User Interface              │
└────────────────┬────────────────────────────────┘
                 │
         ┌───────▼────────┐
         │   Dispatcher   │
         │   (aiogram)    │
         └───────┬────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼──┐  ┌─────▼────┐  ┌───▼────┐
│Admin │  │Middlewares│  │ Handlers│
│Panel │  │           │  │         │
└──────┘  └───────────┘  └────┬────┘
                              │
                    ┌─────────▼──────────┐
                    │ Services Layer     │
                    │ (Business Logic)   │
                    └─────────┬──────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
         ┌────▼────┐    ┌────▼─────┐  ┌─────▼──┐
         │PostgreSQL    │Google     │  │ AI APIs│
         │Database  │   │ Sheets    │  │        │
         └──────────┘   └───────────┘  └────────┘
```

### Layered Structure

```
handlers/          # HTTP endpoint handlers & command/message handlers
  ├── admin/       # Admin commands & callbacks
  ├── menu.py      # Main menu & navigation
  └── lead_form.py # Lead generation workflow

services/          # Business logic (no Telegram-specific code)
  ├── faq_service.py
  ├── lead_service.py
  ├── config_service.py
  ├── google_sheets_service.py
  └── operator_relay_service.py (PRO/AI)

database/          # Data access layer
  ├── models/      # ORM entities
  │   ├── user.py
  │   ├── lead.py
  │   ├── faq_item.py
  │   ├── operator.py
  │   └── config.py
  └── repositories/ # Repository pattern
      ├── user_repo.py
      ├── lead_repo.py
      ├── faq_repo.py
      └── config_repo.py

keyboards/         # UI components
  ├── inline.py   # Inline buttons with callbacks
  └── reply.py    # Reply keyboard buttons

middlewares/       # Request/response interceptors
  ├── admin_middleware.py
  └── auth_middleware.py

states/            # FSM state definitions
  ├── lead_states.py
  └── admin_states.py

settings.py        # Configuration (Pydantic-settings)
```

---

## 🛠️ Tech Stack

| Layer | Technology | Version |
|-------|------------|---------|
| **Runtime** | Python | 3.12+ |
| **Telegram API** | aiogram | 3.x |
| **Web Framework** | FastAPI / Flask | (optional, for WebApp) |
| **Database** | PostgreSQL | 12+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Migrations** | Alembic | 1.12+ |
| **Validation** | Pydantic | 2.0+ |
| **Config** | pydantic-settings | 2.0+ |
| **Async Google Sheets** | gspread-asyncio | 1.5+ |
| **LLM APIs** | OpenAI / GigaChat | (pluggable) |
| **Logging** | structlog | 23.1+ |
| **Task Scheduling** | APScheduler | 3.10+ |
| **Containerization** | Docker | 20.10+ |

---

## 📂 Project Structure

```
telegram-bot-business/
├── bot/                          # Main bot package
│   ├── __init__.py
│   ├── settings.py              # Configuration (VERSION, secrets)
│   ├── handlers/                # Message & callback handlers
│   │   ├── __init__.py
│   │   ├── menu.py              # /start, main menu
│   │   ├── lead_form.py         # Lead generation FSM
│   │   └── admin/               # Admin-only handlers
│   │       ├── __init__.py
│   │       ├── menu.py          # Admin panel
│   │       ├── faq.py           # FAQ CRUD
│   │       ├── leads.py         # Lead management
│   │       ├── settings.py      # Bot configuration
│   │       └── helpers.py       # Shared utilities
│   ├── services/                # Business logic (NO telegram-specific)
│   │   ├── __init__.py
│   │   ├── faq_service.py       # FAQ operations
│   │   ├── lead_service.py      # Lead generation
│   │   ├── config_service.py    # Bot configuration
│   │   ├── google_sheets_service.py  # Google Sheets export
│   │   ├── operator_relay_service.py # PRO: relay & operator management
│   │   ├── broadcast_service.py     # PRO: bulk messaging
│   │   └── ai_service.py        # AI-Edition: LLM integration
│   ├── database/                # Data access layer
│   │   ├── __init__.py
│   │   ├── db_helper.py         # Session factory, migrations
│   │   ├── models/              # ORM entities
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # Base model class
│   │   │   ├── user.py
│   │   │   ├── lead.py
│   │   │   ├── faq_item.py
│   │   │   ├── operator.py
│   │   │   └── config.py
│   │   └── repositories/        # Repository pattern
│   │       ├── __init__.py
│   │       ├── user_repo.py
│   │       ├── lead_repo.py
│   │       ├── faq_repo.py
│   │       ├── config_repo.py
│   │       └── operator_repo.py
│   ├── keyboards/              # UI components
│   │   ├── __init__.py
│   │   ├── inline.py           # Inline button builders
│   │   └── reply.py            # Reply keyboard builders
│   ├── middlewares/            # Aiogram middlewares
│   │   ├── __init__.py
│   │   ├── admin_middleware.py  # Admin permission check
│   │   └── auth_middleware.py   # User registration/identification
│   ├── states/                 # FSM states
│   │   ├── __init__.py
│   │   ├── lead_states.py      # Lead form states
│   │   └── admin_states.py     # Admin panel states
│   └── webapps/                # WebApp HTML (PRO/AI)
│       └── stats.html          # Analytics dashboard
├── alembic/                     # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   ├── alembic.ini
│   └── versions/               # Migration files
├── tests/                       # Unit & integration tests
│   ├── __init__.py
│   ├── test_services/
│   ├── test_handlers/
│   └── test_repositories/
├── main.py                      # Entry point
├── seed_detailing.py            # DB seed script (development)
├── requirements.txt             # Pinned dependencies
├── pyproject.toml              # Project metadata & build config
├── docker-compose.yml          # Local dev environment
├── Dockerfile                  # Container image
├── .env.example                # Environment template
├── .gitignore
├── alembic.ini
├── SETUP.md                    # Setup instructions
└── README.md                   # This file

```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL 12+
- Docker & Docker Compose (optional)
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/your-org/telegram-bot-business.git
cd telegram-bot-business

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or with dev tools:
pip install -e ".[dev]"
```

### 2. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials:
# BOT_TOKEN=your_telegram_bot_token_here
# DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/bot_db
# VERSION=LITE  # or PRO, AI
# GOOGLE_SHEET_ID=your_google_sheet_id
# GOOGLE_CREDENTIALS_JSON=/path/to/credentials.json
# OPENAI_API_KEY=sk-...  # Required for AI-Edition
# ADMIN_IDS=123456789,987654321
```

### 3. Database Setup

```bash
# Create PostgreSQL database
createdb bot_db

# Run migrations
alembic upgrade head

# (Optional) Seed demo data
python seed_detailing.py
```

### 4. Run the Bot

```bash
# Start bot
python main.py
```

### 5. Using Docker Compose (Recommended)

```bash
# Start PostgreSQL + Bot
docker-compose up -d

# View logs
docker-compose logs -f bot

# Stop services
docker-compose down
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Required
BOT_TOKEN=<your_telegram_bot_token>
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/db_name
VERSION=LITE|PRO|AI  # Feature set to enable

# Google Sheets API (for lead export)
GOOGLE_SHEET_ID=<google_sheet_id>
GOOGLE_CREDENTIALS_JSON=path/to/service-account.json

# AI Integration (required for AI-Edition)
OPENAI_API_KEY=sk-...
# Or for GigaChat:
GIGACHAT_API_KEY=...

# Administration
ADMIN_IDS=123456789,987654321  # Comma-separated telegram user IDs
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR
```

### Version-Specific Features

Edit `.env` to switch between editions:

```bash
# LITE Edition - Minimal footprint
VERSION=LITE

# PRO Edition - Team management
VERSION=PRO

# AI-Edition - Full intelligence
VERSION=AI
```

The same codebase handles all three modes. Feature flags in handlers automatically enable/disable functionality based on the VERSION setting.

---

## 🔌 API & Integration

### Google Sheets API

Leads are automatically exported to a Google Sheet. Required setup:

1. Create Google Cloud project
2. Enable Google Sheets API
3. Create Service Account with `service_account.json`
4. Share Google Sheet with service account email
5. Set `GOOGLE_CREDENTIALS_JSON` path in `.env`

### Telegram API

Uses **aiogram 3.x** for async interactions with Telegram API.

Key interactions:
- Commands: `/start`, `/help`, `/admin`
- Callbacks: FAQ selection, form submission
- File uploads: Lead attachments
- WebApps: Analytics dashboard (PRO/AI)

### LLM Integration (AI-Edition)

Supported providers (pluggable):
- **OpenAI API** (GPT-4, GPT-3.5-turbo)
- **GigaChat API** (Russian-optimized, requires Sber account)

System prompts and RAG context stored in `config` table.

### External APIs

| Service | Purpose | Integration |
|---------|---------|-------------|
| Telegram Bot API | Bot control | aiogram client |
| Google Sheets API | Lead export | gspread-asyncio |
| OpenAI / GigaChat | AI responses | aiohttp client |

---

## 👨‍💻 Development Guide

### Project Standards

- **Language:** English (code, function names, variables)
- **Comments:** Russian (explain business logic)
- **Logging:** Russian fluent messages (user-facing)
- **Code Style:** Black (100 char line), isort, ruff
- **Type Hints:** MyPy-compatible

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=bot tests/

# Specific test file
pytest tests/test_services/test_faq_service.py -v

# Async tests
pytest -v --asyncio-mode=auto
```

### Code Structure Rules

**Handlers** (clean, thin):
```python
# handlers/menu.py
async def cmd_start(message: Message, state: FSMContext):
    # Only: user input → service → response
    user_data = await user_service.get_or_create_user(message.from_user.id)
    keyboard = await faq_service.get_main_menu_keyboard()
    await message.answer("Welcome!", reply_markup=keyboard)
```

**Services** (business logic, testable):
```python
# services/faq_service.py
async def get_main_menu_keyboard(self) -> InlineKeyboardMarkup:
    # Pure business logic, no telegram imports except for types
    faqs = await self.repo.list_active()
    buttons = [InlineKeyboardButton(text=faq.question, callback_data=f"faq_{faq.id}") 
               for faq in faqs]
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
```

**Repositories** (data access only):
```python
# database/repositories/faq_repo.py
async def list_active(self) -> list[FAQItem]:
    stmt = select(FAQItem).where(FAQItem.is_active == True)
    result = await self.session.execute(stmt)
    return result.scalars().all()
```

### Extending the Bot

**Add a new FAQ category:**

1. Create database migration (Alembic)
2. Add `category` field to `FAQItem` model
3. Update `faq_repo.py` with category filtering
4. Update `faq_service.py` to handle categories
5. Update handlers & keyboards
6. Write tests

**Add an API integration (e.g., CRM):**

1. Create `crm_service.py` in services/
2. Implement async methods (no TG-specific code)
3. Call from handlers/services as needed
4. Add error handling & logging

---

## 🐳 Deployment

### Local Development

```bash
# Terminal 1: PostgreSQL
docker run --name bot-postgres \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=bot_db \
  -p 5432:5432 \
  postgres:15

# Terminal 2: Bot
python main.py
```

### Docker Compose (Recommended)

```bash
docker-compose up -d
```

Includes: PostgreSQL, pgAdmin (optional), Bot service.

### Production Deployment

1. **Use managed PostgreSQL** (AWS RDS, Azure Database, etc.)
2. **Deploy bot as systemd service or Kubernetes pod**
3. **Environment variables via secrets manager**
4. **Enable structured logging to ELK/Datadog**
5. **Set up monitoring (Sentry for errors)**

Example systemd service:

```ini
[Unit]
Description=Business Telegram Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/opt/bot
Environment="PATH=/opt/bot/venv/bin"
EnvironmentFile=/opt/bot/.env
ExecStart=/opt/bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📊 Database Schema

### Key Tables

**users**
- `id`: UUID (PK)
- `telegram_id`: int (unique)
- `username`: str (nullable)
- `first_name`: str
- `is_admin`: bool
- `is_operator`: bool (PRO/AI)
- `created_at`: datetime
- `updated_at`: datetime

**leads**
- `id`: UUID (PK)
- `user_id`: UUID (FK → users)
- `name`: str
- `phone`: str
- `description`: text (nullable)
- `status`: enum (new, contacted, converted, rejected)
- `created_at`: datetime
- `updated_at`: datetime

**faq_items**
- `id`: UUID (PK)
- `question`: str
- `answer`: str
- `category`: str (nullable)
- `order`: int
- `is_active`: bool
- `created_at`: datetime
- `updated_at`: datetime

**operators** (PRO/AI)
- `id`: UUID (PK)
- `telegram_id`: int (FK → users.telegram_id)
- `name`: str
- `is_active`: bool
- `created_at`: datetime

**config** (AI-Edition)
- `id`: UUID (PK)
- `key`: str (unique)
- `value`: text
- `data_type`: enum (string, json, bool)
- `updated_at`: datetime

---

## 🛡️ Security

- ✅ Admin middleware validates user permissions
- ✅ Input validation via Pydantic models
- ✅ SQL injection prevention (SQLAlchemy parameterization)
- ✅ Secrets stored in `.env` (not in code)
- ✅ Rate limiting support (can add aiogram built-ins)
- ✅ HTTPS enforced for Google Sheets / AI APIs

---

## 📝 License

MIT License. See [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome-feature`)
3. Follow the [code style guide](#development-guide)
4. Write tests for new features
5. Submit a Pull Request

---

## 📚 Additional Resources

- **Aiogram Documentation:** https://docs.aiogram.dev/
- **SQLAlchemy AsyncIO:** https://docs.sqlalchemy.org/asyncio/
- **Pydantic Documentation:** https://docs.pydantic.dev/
- **Alembic Migration Guide:** https://alembic.sqlalchemy.org/

---

## ❓ FAQ

**Q: Can I use this with other databases?**  
A: Yes, but you'll need to update SQLAlchemy connection string and ensure asyncpg support (or use async driver for your DB).

**Q: How do I add more AI providers?**  
A: Implement the `AIProvider` interface in `services/ai_service.py` and add a factory method.

**Q: Can I deploy this without Docker?**  
A: Yes, install dependencies and run `python main.py`, but you'll need PostgreSQL running separately.

**Q: What's the user limit for one instance?**  
A: Depends on infrastructure, but aiogram can handle 10k+ concurrent users with proper resource allocation.

---
