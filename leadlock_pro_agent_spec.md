# LeadLock PRO — Техническое задание для ИИ-агента
**Версия:** 2.0 (исправленная и дополненная)  
**Статус:** Готово к исполнению  
**Режим:** Пошаговое выполнение. Каждый шаг — атомарный. Не переходить к следующему до завершения текущего.

---

## КОНТЕКСТ ПРОЕКТА (прочитать перед началом)

### Стек
- **Framework:** aiogram 3.3.0
- **DB:** PostgreSQL + SQLAlchemy 2.0 async + Alembic
- **FSM Storage:** MemoryStorage (заменить на Redis в PRO)
- **Логирование:** structlog
- **Конфиг:** pydantic-settings + таблица `Config` в БД

### Текущая структура
```
bot/
  database/
    db_helper.py
    models/
      __init__.py       ← экспортирует все модели
      base.py
      config.py         ← key/value хранилище настроек
      faq_item.py
      lead.py
      operator.py       ← модель есть, но НЕ используется в логике
      user.py
    repositories/
      config_repo.py
      faq_repo.py
      lead_repo.py
      user_repo.py
  handlers/
    __init__.py
    admin/
      __init__.py       ← собирает роутеры: menu, faq, leads, settings
      faq.py
      helpers.py
      leads.py
      menu.py
      settings.py
    lead_form.py
    menu.py
  keyboards/
    inline.py
    reply.py
  middlewares/
    admin_middleware.py ← проверяет ADMIN_IDS из settings.py
  services/
    __init__.py
    config_service.py
    faq_service.py
    google_sheets_service.py
    lead_service.py
  settings.py           ← pydantic BaseSettings, читает .env
  states/
    admin_states.py
    lead_states.py
main.py
alembic/
  versions/
    6c336403d496_init.py  ← единственная существующая миграция
```

### Ключевые особенности существующего кода
1. **Сессия БД** передаётся через `DbSessionMiddleware` как `data["session"]` в каждый хендлер
2. **AdminMiddleware** проверяет `telegram_id` в `settings.ADMIN_IDS` (список из .env) — это НЕ операторы, это технические администраторы
3. **Config** — таблица key/value. Методы: `get_value(key, default)`, `set_value(key, value)`
4. **Lead.status** сейчас строка `"new"`. Нет статусов PRO
5. **Operator** — модель существует в БД, но никак не используется в сервисах и хендлерах
6. **MemoryStorage** для FSM — состояния теряются при рестарте
7. `settings.VERSION` уже есть: `Literal["LITE", "PRO", "AI"]` — но нигде не используется
8. **commit()** делается в хендлерах, не в сервисах — это паттерн проекта, не нарушать

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА (обязательны для каждого шага)

1. **НЕ удалять и НЕ изменять** существующую LITE-логику
2. **НЕ перемещать** файлы — только добавлять новые или дополнять существующие
3. **Бизнес-логика только в services** — хендлеры вызывают сервис и отвечают пользователю
4. **DB-операции только через repositories** — сервисы не пишут SQL/ORM напрямую
5. **commit()** — только в хендлерах (паттерн проекта)
6. **Все новые исключения** — явные классы (не `raise Exception("text")`)
7. **Логирование** — через structlog, как в существующем коде
8. **Режим PRO/LITE** проверяется **один раз** — в точке входа в сервис. Не размазывать по хендлерам
9. **После каждого шага** — убедиться что импорты корректны и нет циклических зависимостей

---

## ШАГ 1 — Расширение моделей БД

### 1.1 Обновить `bot/database/models/lead.py`

Добавить три поля. **Не трогать существующие поля.**

```python
# Добавить импорт в начало файла:
from sqlalchemy.orm import relationship  # уже есть

# Добавить поля в класс Lead (после поля synced_to_sheets):
assigned_operator_id = Column(Integer, ForeignKey("operators.id"), nullable=True)
closed_at = Column(DateTime, nullable=True)
updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# Добавить relationship (после существующего user = relationship(...)):
assigned_operator = relationship("Operator", foreign_keys=[assigned_operator_id])
```

> ⚠️ `onupdate=datetime.utcnow` — передаётся callable, не вызов. Без скобок.

### 1.2 Обновить `bot/database/models/operator.py`

Добавить одно поле. **Не трогать существующие поля.**

```python
# Добавить в класс Operator:
role: Mapped[str] = mapped_column(String(20), nullable=False, default="operator")
# Допустимые значения: "operator" | "owner"
```

### 1.3 Создать `bot/database/models/lead_message.py`

```python
"""Модель сообщений диалога по заявке."""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from bot.database.models.base import Base


class LeadMessage(Base):
    __tablename__ = "lead_messages"

    id = Column(Integer, primary_key=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False)
    sender_role = Column(String(20), nullable=False)  # "user" | "operator" | "system"
    sender_id = Column(Integer, nullable=True)        # telegram_id отправителя, None для system
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    lead = relationship("Lead", back_populates="messages")

    def __repr__(self):
        return f"<LeadMessage(id={self.id}, lead_id={self.lead_id}, role='{self.sender_role}')>"
```

Также добавить в `Lead` обратный relationship:
```python
messages = relationship("LeadMessage", back_populates="lead", order_by="LeadMessage.created_at")
```

### 1.4 Обновить `bot/database/models/__init__.py`

```python
from .user import User
from .lead import Lead
from .lead_message import LeadMessage
from .faq_item import FAQItem
from .operator import Operator
from .config import Config

__all__ = ["User", "Lead", "LeadMessage", "FAQItem", "Operator", "Config"]
```

### 1.5 Создать `bot/database/repositories/lead_message_repo.py`

```python
"""Репозиторий для работы с сообщениями диалога."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.lead_message import LeadMessage


class LeadMessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        lead_id: int,
        sender_role: str,
        text: str,
        sender_id: int | None = None,
    ) -> LeadMessage:
        """Создать новое сообщение в диалоге."""
        message = LeadMessage(
            lead_id=lead_id,
            sender_role=sender_role,
            sender_id=sender_id,
            text=text,
        )
        self.session.add(message)
        await self.session.flush()
        return message

    async def get_by_lead(self, lead_id: int) -> list[LeadMessage]:
        """Получить все сообщения по заявке, отсортированные по дате."""
        stmt = (
            select(LeadMessage)
            .where(LeadMessage.lead_id == lead_id)
            .order_by(LeadMessage.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
```

---

## ШАГ 2 — Миграция БД

### 2.1 Создать файл миграции вручную

Создать `alembic/versions/0002_pro_schema.py`:

```python
"""PRO schema: lead_messages, lead fields, operator role

Revision ID: 0002_pro_schema
Revises: 6c336403d496
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_pro_schema'
down_revision: Union[str, None] = '6c336403d496'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавить поля в таблицу leads
    op.add_column('leads',
        sa.Column('assigned_operator_id', sa.Integer(), nullable=True)
    )
    op.add_column('leads',
        sa.Column('closed_at', sa.DateTime(), nullable=True)
    )
    op.add_column('leads',
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now())
    )
    op.create_foreign_key(
        'fk_leads_assigned_operator',
        'leads', 'operators',
        ['assigned_operator_id'], ['id']
    )

    # Добавить поле role в таблицу operators
    op.add_column('operators',
        sa.Column('role', sa.String(length=20), nullable=False,
                  server_default='operator')
    )

    # Создать таблицу lead_messages
    op.create_table(
        'lead_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('lead_id', sa.Integer(),
                  sa.ForeignKey('leads.id'), nullable=False),
        sa.Column('sender_role', sa.String(length=20), nullable=False),
        sa.Column('sender_id', sa.Integer(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index('ix_lead_messages_lead_id', 'lead_messages', ['lead_id'])


def downgrade() -> None:
    op.drop_index('ix_lead_messages_lead_id', table_name='lead_messages')
    op.drop_table('lead_messages')
    op.drop_column('operators', 'role')
    op.drop_constraint('fk_leads_assigned_operator', 'leads', type_='foreignkey')
    op.drop_column('leads', 'updated_at')
    op.drop_column('leads', 'closed_at')
    op.drop_column('leads', 'assigned_operator_id')
```

> ⚠️ Миграция должна быть безопасной: существующие лиды сохраняются, новые поля nullable или имеют server_default.

---

## ШАГ 3 — Кастомные исключения

Создать `bot/exceptions.py`:

```python
"""Кастомные исключения приложения."""


class LeadLockError(Exception):
    """Базовое исключение приложения."""


class LeadNotFoundError(LeadLockError):
    """Заявка не найдена."""


class OperatorNotFoundError(LeadLockError):
    """Оператор не найден."""


class AccessDeniedError(LeadLockError):
    """Недостаточно прав для выполнения операции."""


class InvalidStatusTransitionError(LeadLockError):
    """Недопустимый переход статуса заявки."""
    def __init__(self, from_status: str, to_status: str):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Нельзя перевести заявку из '{from_status}' в '{to_status}'")


class ActiveLeadNotFoundError(LeadLockError):
    """У пользователя нет активной заявки."""


class SystemModeError(LeadLockError):
    """Операция недоступна в текущем режиме системы."""
```

---

## ШАГ 4 — Расширение ConfigService

### 4.1 Дополнить `bot/services/config_service.py`

Добавить новые методы в существующий класс `ConfigService`. **Не удалять существующие методы.**

```python
# Константы режимов — добавить в начало файла (после импортов)
SYSTEM_MODE_LITE = "lite"
SYSTEM_MODE_PRO = "pro"

# Добавить методы в класс ConfigService:

async def get_system_mode(self) -> str:
    """
    Получить текущий режим системы.
    
    Returns:
        "lite" или "pro"
    """
    return await self.repository.get_value("system_mode", default=SYSTEM_MODE_LITE)

async def set_system_mode(self, mode: str) -> None:
    """
    Установить режим системы.
    
    Args:
        mode: "lite" или "pro"
        
    Raises:
        ValueError: если mode не является допустимым значением
    """
    if mode not in (SYSTEM_MODE_LITE, SYSTEM_MODE_PRO):
        raise ValueError(f"Недопустимый режим: {mode}. Допустимо: lite, pro")
    await self.repository.set_value("system_mode", mode)
    await logger.ainfo("Режим системы изменён", mode=mode)

async def get_operator_group_chat_id(self) -> int | None:
    """
    Получить ID группового чата операторов.
    
    Returns:
        chat_id или None если не настроен
    """
    value = await self.repository.get_value("operator_group_chat_id", default="")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        await logger.awarning("Некорректный operator_group_chat_id в Config", value=value)
        return None

async def is_auto_assign_enabled(self) -> bool:
    """Включено ли автоназначение операторов."""
    value = await self.repository.get_value("auto_assign_enabled", default="false")
    return value.lower() == "true"

async def get_owner_telegram_id(self) -> int | None:
    """Получить telegram_id владельца бизнеса."""
    value = await self.repository.get_value("owner_telegram_id", default="")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
```

---

## ШАГ 5 — Расширение LeadRepository

Добавить новые методы в `bot/database/repositories/lead_repo.py`. **Не трогать существующие методы.**

```python
# Добавить импорты (если не хватает):
from datetime import datetime
from sqlalchemy import func, and_

# Добавить методы в класс LeadRepository:

async def get_by_id(self, lead_id: int) -> Lead | None:
    """Получить заявку по ID."""
    stmt = select(Lead).where(Lead.id == lead_id)
    result = await self.session.execute(stmt)
    return result.scalars().first()

async def get_active_by_user_id(self, user_id: int) -> Lead | None:
    """
    Получить активную заявку пользователя.
    Активная = статус не 'closed' и не 'rejected'.
    """
    stmt = (
        select(Lead)
        .where(
            and_(
                Lead.user_id == user_id,
                Lead.status.notin_(["closed", "rejected"]),
            )
        )
        .order_by(Lead.created_at.desc())
        .limit(1)
    )
    result = await self.session.execute(stmt)
    return result.scalars().first()

async def get_by_operator(self, operator_id: int) -> list[Lead]:
    """Получить все заявки назначенные на оператора."""
    stmt = (
        select(Lead)
        .where(Lead.assigned_operator_id == operator_id)
        .order_by(Lead.created_at.desc())
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def get_by_status(self, status: str) -> list[Lead]:
    """Получить все заявки с определённым статусом."""
    stmt = select(Lead).where(Lead.status == status).order_by(Lead.created_at.desc())
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def count_by_status(self, status: str) -> int:
    """Подсчитать заявки по статусу."""
    stmt = select(func.count()).where(Lead.status == status)
    result = await self.session.execute(stmt)
    return result.scalar() or 0

async def count_created_after(self, dt: datetime) -> int:
    """Подсчитать заявки созданные после указанной даты."""
    stmt = select(func.count()).where(Lead.created_at >= dt)
    result = await self.session.execute(stmt)
    return result.scalar() or 0

async def get_avg_processing_time_seconds(self) -> float | None:
    """
    Среднее время обработки закрытых заявок в секундах.
    Считается как avg(closed_at - created_at) для лидов со статусом 'closed'.
    """
    stmt = (
        select(func.avg(
            func.extract('epoch', Lead.closed_at) - func.extract('epoch', Lead.created_at)
        ))
        .where(and_(Lead.status == "closed", Lead.closed_at.isnot(None)))
    )
    result = await self.session.execute(stmt)
    return result.scalar()
```

---

## ШАГ 6 — Создать OperatorRepository

Создать `bot/database/repositories/operator_repo.py`:

```python
"""Репозиторий для работы с операторами."""

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.operator import Operator
from bot.database.models.lead import Lead


class OperatorRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, operator_id: int) -> Operator | None:
        """Получить оператора по внутреннему ID."""
        stmt = select(Operator).where(Operator.id == operator_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_telegram_id(self, telegram_id: int) -> Operator | None:
        """Получить оператора по telegram_id."""
        stmt = select(Operator).where(Operator.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all_active(self) -> list[Operator]:
        """Получить всех активных операторов."""
        stmt = select(Operator).where(Operator.is_active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        telegram_id: int,
        username: str | None = None,
        role: str = "operator",
    ) -> Operator:
        """Создать нового оператора."""
        operator = Operator(
            telegram_id=telegram_id,
            username=username,
            is_active=True,
            role=role,
        )
        self.session.add(operator)
        await self.session.flush()
        return operator

    async def deactivate(self, telegram_id: int) -> Operator | None:
        """Деактивировать оператора."""
        operator = await self.get_by_telegram_id(telegram_id)
        if operator:
            operator.is_active = False
            await self.session.flush()
        return operator

    async def get_least_loaded(self) -> Operator | None:
        """
        Получить активного оператора с наименьшим числом активных заявок.
        Используется для автоназначения.
        """
        # Подзапрос: считаем активные заявки для каждого оператора
        active_leads_subq = (
            select(Lead.assigned_operator_id, func.count(Lead.id).label("lead_count"))
            .where(Lead.status.notin_(["closed", "rejected"]))
            .group_by(Lead.assigned_operator_id)
            .subquery()
        )

        stmt = (
            select(Operator)
            .outerjoin(
                active_leads_subq,
                Operator.id == active_leads_subq.c.assigned_operator_id,
            )
            .where(Operator.is_active == True)
            .order_by(func.coalesce(active_leads_subq.c.lead_count, 0).asc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
```

---

## ШАГ 7 — Расширить LeadService

Дополнить `bot/services/lead_service.py`. **Не трогать существующие методы.**

```python
# Добавить импорты в начало файла:
from datetime import datetime
from bot.exceptions import (
    LeadNotFoundError,
    AccessDeniedError,
    InvalidStatusTransitionError,
    ActiveLeadNotFoundError,
)
from bot.database.repositories.operator_repo import OperatorRepository

# Добавить константы переходов статусов:
ALLOWED_STATUS_TRANSITIONS = {
    "new": ["in_progress"],
    "in_progress": ["waiting_client", "closed", "rejected"],
    "waiting_client": ["in_progress"],
    "closed": [],
    "rejected": [],
}

# Добавить методы в класс LeadService:

def _validate_status_transition(self, current: str, new: str) -> None:
    """
    Проверить допустимость перехода статуса.
    
    Raises:
        InvalidStatusTransitionError: если переход недопустим
    """
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current, [])
    if new not in allowed:
        raise InvalidStatusTransitionError(current, new)

async def assign_operator(
    self,
    lead_id: int,
    operator_id: int,
    actor_telegram_id: int,
) -> Lead:
    """
    Назначить оператора на заявку.
    
    Args:
        lead_id: ID заявки
        operator_id: ID оператора (внутренний)
        actor_telegram_id: telegram_id того, кто выполняет действие
        
    Raises:
        LeadNotFoundError: заявка не найдена
        AccessDeniedError: нет прав
    """
    lead = await self.repository.get_by_id(lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Заявка {lead_id} не найдена")

    operator_repo = OperatorRepository(self.repository.session)
    actor = await operator_repo.get_by_telegram_id(actor_telegram_id)

    # Проверка прав: owner может назначить на любого, operator — только себя
    if actor is None or (actor.role != "owner" and actor.id != operator_id):
        raise AccessDeniedError("Недостаточно прав для назначения оператора")

    lead.assigned_operator_id = operator_id
    if lead.status == "new":
        lead.status = "in_progress"
    await self.repository.session.flush()

    await logger.ainfo(
        "Оператор назначен на заявку",
        lead_id=lead_id,
        operator_id=operator_id,
    )
    return lead

async def change_status(
    self,
    lead_id: int,
    new_status: str,
    actor_telegram_id: int,
) -> Lead:
    """
    Изменить статус заявки с проверкой прав и допустимости перехода.
    
    Args:
        lead_id: ID заявки
        new_status: новый статус
        actor_telegram_id: telegram_id исполнителя
        
    Raises:
        LeadNotFoundError: заявка не найдена
        AccessDeniedError: нет прав
        InvalidStatusTransitionError: недопустимый переход
    """
    lead = await self.repository.get_by_id(lead_id)
    if lead is None:
        raise LeadNotFoundError(f"Заявка {lead_id} не найдена")

    operator_repo = OperatorRepository(self.repository.session)
    actor = await operator_repo.get_by_telegram_id(actor_telegram_id)

    if actor is None:
        raise AccessDeniedError("Только операторы могут менять статус заявок")

    # Owner может менять любой лид, operator — только свой
    if actor.role != "owner" and lead.assigned_operator_id != actor.id:
        raise AccessDeniedError("Оператор может изменять только назначенные ему заявки")

    self._validate_status_transition(lead.status, new_status)

    lead.status = new_status
    if new_status in ("closed", "rejected"):
        lead.closed_at = datetime.utcnow()

    await self.repository.session.flush()

    # Синхронизация в Google Sheets при закрытии (PRO)
    if new_status == "closed" and self.sheets_service:
        try:
            await self._notify_sheets(lead)
            await self.repository.mark_synced(lead.id)
        except Exception as e:
            await logger.awarning(
                "Не удалось синхронизировать закрытую заявку с Sheets",
                lead_id=lead_id,
                error=str(e),
            )

    await logger.ainfo(
        "Статус заявки изменён",
        lead_id=lead_id,
        new_status=new_status,
        actor=actor_telegram_id,
    )
    return lead

async def get_active_lead_by_user(self, user_id: int) -> Lead | None:
    """
    Получить активную заявку пользователя (для PRO диалога).
    
    Args:
        user_id: внутренний ID пользователя (не telegram_id)
        
    Returns:
        Lead или None
    """
    return await self.repository.get_active_by_user_id(user_id)

async def get_lead_dialogue(self, lead_id: int) -> list:
    """
    Получить историю сообщений по заявке.
    
    Returns:
        Список LeadMessage отсортированный по created_at
    """
    from bot.database.repositories.lead_message_repo import LeadMessageRepository
    msg_repo = LeadMessageRepository(self.repository.session)
    return await msg_repo.get_by_lead(lead_id)

async def auto_assign_if_enabled(self, lead: Lead) -> Lead:
    """
    Автоматически назначить оператора если auto_assign_enabled = true.
    Вызывается после создания заявки в PRO режиме.
    
    Returns:
        Обновлённый lead (с или без назначения)
    """
    from bot.services.config_service import ConfigService
    config_service = ConfigService(self.repository.session)
    
    if not await config_service.is_auto_assign_enabled():
        return lead

    operator_repo = OperatorRepository(self.repository.session)
    operator = await operator_repo.get_least_loaded()

    if operator is None:
        await logger.awarning("Нет доступных операторов для автоназначения", lead_id=lead.id)
        return lead

    lead.assigned_operator_id = operator.id
    lead.status = "in_progress"
    await self.repository.session.flush()

    await logger.ainfo(
        "Автоназначение оператора",
        lead_id=lead.id,
        operator_id=operator.id,
    )
    return lead
```

---

## ШАГ 8 — Создать DialogueService

Создать `bot/services/dialogue_service.py`:

```python
"""Сервис двустороннего диалога клиент ↔ оператор."""

from typing import TYPE_CHECKING

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.lead_message_repo import LeadMessageRepository
from bot.database.repositories.lead_repo import LeadRepository
from bot.database.repositories.user_repo import UserRepository
from bot.database.repositories.operator_repo import OperatorRepository
from bot.exceptions import (
    LeadNotFoundError,
    AccessDeniedError,
    ActiveLeadNotFoundError,
)

if TYPE_CHECKING:
    from aiogram import Bot

logger = structlog.get_logger()


class DialogueService:
    """
    Управляет двусторонним диалогом между клиентом и оператором.
    
    Обязанности:
    - Сохранять сообщения в LeadMessage
    - Маршрутизировать: клиент → оператор, оператор → клиент
    - Проверять права доступа
    """

    def __init__(self, session: AsyncSession, bot: "Bot"):
        self.session = session
        self.bot = bot
        self.msg_repo = LeadMessageRepository(session)
        self.lead_repo = LeadRepository(session)
        self.user_repo = UserRepository(session)
        self.operator_repo = OperatorRepository(session)

    async def send_user_message(
        self,
        user_telegram_id: int,
        text: str,
    ) -> None:
        """
        Обработать входящее сообщение от клиента.
        
        Сохраняет в LeadMessage и пересылает назначенному оператору.
        
        Args:
            user_telegram_id: telegram_id клиента
            text: текст сообщения
            
        Raises:
            ActiveLeadNotFoundError: у пользователя нет активной заявки
        """
        user = await self.user_repo.get_by_tg_id(user_telegram_id)
        if user is None:
            raise ActiveLeadNotFoundError("Пользователь не найден в БД")

        lead = await self.lead_repo.get_active_by_user_id(user.id)
        if lead is None:
            raise ActiveLeadNotFoundError(
                f"У пользователя {user_telegram_id} нет активной заявки"
            )

        # Сохраняем сообщение
        await self.msg_repo.create(
            lead_id=lead.id,
            sender_role="user",
            sender_id=user_telegram_id,
            text=text,
        )

        await logger.ainfo(
            "Сообщение клиента сохранено",
            lead_id=lead.id,
            user_id=user_telegram_id,
        )

        # Пересылаем оператору
        if lead.assigned_operator_id:
            operator = await self.operator_repo.get_by_id(lead.assigned_operator_id)
            if operator:
                try:
                    await self.bot.send_message(
                        chat_id=operator.telegram_id,
                        text=(
                            f"💬 Сообщение от клиента по заявке #{lead.id}\n\n"
                            f"👤 {lead.name}\n"
                            f"📝 {text}"
                        ),
                    )
                except Exception as e:
                    await logger.awarning(
                        "Не удалось отправить сообщение оператору",
                        operator_id=operator.telegram_id,
                        lead_id=lead.id,
                        error=str(e),
                    )
        else:
            await logger.awarning(
                "Заявка без назначенного оператора, сообщение не доставлено",
                lead_id=lead.id,
            )

    async def send_operator_message(
        self,
        operator_telegram_id: int,
        lead_id: int,
        text: str,
    ) -> None:
        """
        Обработать исходящее сообщение от оператора клиенту.
        
        Args:
            operator_telegram_id: telegram_id оператора
            lead_id: ID заявки
            text: текст ответа
            
        Raises:
            LeadNotFoundError: заявка не найдена
            AccessDeniedError: оператор не назначен на эту заявку
        """
        lead = await self.lead_repo.get_by_id(lead_id)
        if lead is None:
            raise LeadNotFoundError(f"Заявка {lead_id} не найдена")

        operator = await self.operator_repo.get_by_telegram_id(operator_telegram_id)
        if operator is None:
            raise AccessDeniedError("Отправитель не является оператором")

        # Owner может отвечать в любую заявку, оператор — только в свою
        if operator.role != "owner" and lead.assigned_operator_id != operator.id:
            raise AccessDeniedError(
                f"Оператор {operator_telegram_id} не назначен на заявку {lead_id}"
            )

        # Сохраняем сообщение
        await self.msg_repo.create(
            lead_id=lead_id,
            sender_role="operator",
            sender_id=operator_telegram_id,
            text=text,
        )

        # Получаем telegram_id клиента
        user = await self.user_repo.get_by_id(lead.user_id)
        if user is None:
            await logger.awarning("Пользователь заявки не найден", lead_id=lead_id)
            return

        # Отправляем клиенту
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    f"📩 Ответ по вашей заявке #{lead_id}:\n\n"
                    f"{text}"
                ),
            )
            await logger.ainfo(
                "Ответ оператора отправлен клиенту",
                lead_id=lead_id,
                user_telegram_id=user.telegram_id,
            )
        except Exception as e:
            await logger.aerror(
                "Не удалось отправить ответ клиенту",
                lead_id=lead_id,
                user_id=user.telegram_id,
                error=str(e),
            )
            raise
```

> ⚠️ UserRepository нужно добавить метод `get_by_id(user_id: int)`. Проверить его наличие в `user_repo.py`. Если нет — добавить.

---

## ШАГ 9 — Создать OperatorRelayService

Создать `bot/services/operator_relay_service.py`:

```python
"""Сервис уведомления операторов о новых заявках."""

from typing import TYPE_CHECKING

import structlog
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.lead import Lead
from bot.services.config_service import ConfigService

if TYPE_CHECKING:
    from aiogram import Bot

logger = structlog.get_logger()


class OperatorRelayService:
    """
    Отвечает за отправку карточек лидов операторам.
    Не содержит бизнес-логики — только форматирование и отправка.
    """

    def __init__(self, session: AsyncSession, bot: "Bot"):
        self.session = session
        self.bot = bot
        self.config_service = ConfigService(session)

    def _build_lead_card_text(self, lead: Lead) -> str:
        """Сформировать текст карточки лида."""
        return (
            f"🔔 <b>Новая заявка #{lead.id}</b>\n\n"
            f"👤 Имя: {lead.name}\n"
            f"📞 Телефон: {lead.phone}\n"
            f"📝 Описание: {lead.description or '—'}\n"
            f"🕐 Создана: {lead.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

    def _build_lead_card_keyboard(self, lead_id: int) -> InlineKeyboardMarkup:
        """Сформировать inline-клавиатуру для карточки лида."""
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Взять в работу",
                callback_data=f"lead:take:{lead_id}",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"lead:reject:{lead_id}",
            ),
        ]])

    async def notify_new_lead(self, lead: Lead) -> None:
        """
        Отправить карточку нового лида в группу операторов.
        
        В LITE режиме — не вызывается.
        В PRO режиме — отправляет в operator_group_chat_id.
        """
        group_chat_id = await self.config_service.get_operator_group_chat_id()

        if group_chat_id is None:
            await logger.awarning(
                "operator_group_chat_id не настроен, карточка лида не отправлена",
                lead_id=lead.id,
            )
            return

        try:
            await self.bot.send_message(
                chat_id=group_chat_id,
                text=self._build_lead_card_text(lead),
                reply_markup=self._build_lead_card_keyboard(lead.id),
                parse_mode="HTML",
            )
            await logger.ainfo(
                "Карточка лида отправлена в группу операторов",
                lead_id=lead.id,
                group_chat_id=group_chat_id,
            )
        except Exception as e:
            await logger.aerror(
                "Ошибка отправки карточки лида",
                lead_id=lead.id,
                error=str(e),
            )
```

---

## ШАГ 10 — Создать StatsService

Создать `bot/services/stats_service.py`:

```python
"""Сервис статистики для owner-дашборда."""

from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.lead_repo import LeadRepository
from bot.database.repositories.operator_repo import OperatorRepository

logger = structlog.get_logger()


class StatsService:
    def __init__(self, session: AsyncSession):
        self.lead_repo = LeadRepository(session)
        self.operator_repo = OperatorRepository(session)

    async def get_owner_dashboard(self) -> dict:
        """
        Агрегированная статистика для owner.
        
        Returns:
            dict с ключами: total, closed, in_progress, new, 
                           rejected, conversion_pct, avg_time_hours,
                           today, week
        """
        now = datetime.utcnow()

        total_leads = len(await self.lead_repo.get_all())
        closed = await self.lead_repo.count_by_status("closed")
        in_progress = await self.lead_repo.count_by_status("in_progress")
        new = await self.lead_repo.count_by_status("new")
        rejected = await self.lead_repo.count_by_status("rejected")
        today = await self.lead_repo.count_created_after(now.replace(hour=0, minute=0, second=0))
        week = await self.lead_repo.count_created_after(now - timedelta(days=7))
        avg_seconds = await self.lead_repo.get_avg_processing_time_seconds()

        conversion = round((closed / total_leads * 100), 1) if total_leads > 0 else 0.0
        avg_hours = round(avg_seconds / 3600, 1) if avg_seconds else None

        return {
            "total": total_leads,
            "closed": closed,
            "in_progress": in_progress,
            "new": new,
            "rejected": rejected,
            "conversion_pct": conversion,
            "avg_time_hours": avg_hours,
            "today": today,
            "week": week,
        }

    async def get_operator_stats(self, operator_id: int) -> dict:
        """
        Статистика по конкретному оператору.
        
        Returns:
            dict с ключами: total_assigned, closed, in_progress, conversion_pct
        """
        leads = await self.lead_repo.get_by_operator(operator_id)
        total = len(leads)
        closed = sum(1 for l in leads if l.status == "closed")
        in_progress = sum(1 for l in leads if l.status == "in_progress")
        conversion = round((closed / total * 100), 1) if total > 0 else 0.0

        return {
            "total_assigned": total,
            "closed": closed,
            "in_progress": in_progress,
            "conversion_pct": conversion,
        }
```

---

## ШАГ 11 — Обновить `lead_form.py` (PRO ветка)

В хендлере `process_description` в `bot/handlers/lead_form.py` добавить PRO-ветку после сохранения лида. **Не изменять существующую LITE-логику.**

```python
# В функции process_description, после строки:
# lead = await lead_service.save_lead(...)

# Добавить:
from bot.services.config_service import ConfigService, SYSTEM_MODE_PRO
from bot.services.operator_relay_service import OperatorRelayService

config_service = ConfigService(session)
mode = await config_service.get_system_mode()

if mode == SYSTEM_MODE_PRO:
    # PRO: уведомляем группу операторов через relay
    relay = OperatorRelayService(session, bot)
    await relay.notify_new_lead(lead)
    
    # Автоназначение если включено
    lead = await lead_service.auto_assign_if_enabled(lead)
    
    # Создаём системное сообщение о создании заявки
    from bot.database.repositories.lead_message_repo import LeadMessageRepository
    msg_repo = LeadMessageRepository(session)
    await msg_repo.create(
        lead_id=lead.id,
        sender_role="system",
        text=f"Заявка создана. Имя: {name}, телефон: {phone}",
    )
else:
    # LITE: существующая логика уже выполнена через lead_service.save_lead()
    pass
```

---

## ШАГ 12 — Обработчик входящих сообщений от клиента (PRO)

Добавить в `bot/handlers/menu.py` новый хендлер. **Добавлять в конец файла.**

```python
# Добавить импорты:
from bot.services.config_service import ConfigService, SYSTEM_MODE_PRO
from bot.services.dialogue_service import DialogueService
from bot.exceptions import ActiveLeadNotFoundError

# Добавить хендлер (ВАЖНО: он должен быть зарегистрирован ПОСЛЕДНИМ
# в роутере, чтобы не перехватывать FSM-состояния):

@router.message(F.text)
async def handle_user_text_message(
    message: Message,
    session: AsyncSession,
    bot: Bot,
    state: FSMContext,
) -> None:
    """
    PRO-режим: перехватывает текстовые сообщения клиента вне FSM
    и маршрутизирует их в активный диалог.
    """
    # Проверяем текущее состояние FSM — если есть активное, не перехватываем
    current_state = await state.get_state()
    if current_state is not None:
        return

    # Проверяем режим
    config_service = ConfigService(session)
    mode = await config_service.get_system_mode()
    if mode != SYSTEM_MODE_PRO:
        return

    user_id = message.from_user.id

    try:
        dialogue_service = DialogueService(session, bot)
        await dialogue_service.send_user_message(
            user_telegram_id=user_id,
            text=message.text,
        )
        await session.commit()
        # Не отправляем подтверждение клиенту — незаметная пересылка
    except ActiveLeadNotFoundError:
        # Нет активной заявки — игнорируем или возвращаем в меню
        await message.answer(
            text="У вас нет активной заявки. Воспользуйтесь меню:",
            reply_markup=get_main_menu_kb(),
        )
    except Exception as e:
        await logger.aerror(
            "Ошибка при обработке сообщения клиента в PRO режиме",
            user_id=user_id,
            error=str(e),
        )
```

> ⚠️ Добавить `from aiogram import F` и `from aiogram.fsm.context import FSMContext` если их нет в импортах файла. Добавить `Bot` в импорты aiogram.

---

## ШАГ 13 — Хендлеры оператора (callback-кнопки)

Создать `bot/handlers/admin/operator_callbacks.py`:

```python
"""Обработчики callback-кнопок оператора для управления заявками."""

import structlog
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.exceptions import LeadNotFoundError, AccessDeniedError, InvalidStatusTransitionError
from bot.services.lead_service import LeadService
from bot.services.dialogue_service import DialogueService
from bot.services.google_sheets_service import GoogleSheetsService
from bot.settings import settings

logger = structlog.get_logger()
router = Router(name="operator_callbacks")


class OperatorReplyState(StatesGroup):
    waiting_for_reply_text = State()


# --- Взять заявку в работу ---

@router.callback_query(F.data.startswith("lead:take:"))
async def handle_take_lead(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Оператор берёт заявку в работу."""
    lead_id = int(callback.data.split(":")[2])
    operator_telegram_id = callback.from_user.id

    try:
        from bot.database.repositories.operator_repo import OperatorRepository
        operator_repo = OperatorRepository(session)
        operator = await operator_repo.get_by_telegram_id(operator_telegram_id)

        if operator is None:
            await callback.answer("⛔ Вы не являетесь оператором", show_alert=True)
            return

        sheets_service = GoogleSheetsService(
            credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
            sheet_id=settings.GOOGLE_SHEET_ID,
        )
        lead_service = LeadService(session, sheets_service=sheets_service, bot=bot)
        lead = await lead_service.assign_operator(lead_id, operator.id, operator_telegram_id)
        await session.commit()

        await callback.answer("✅ Заявка взята в работу")
        await callback.message.edit_text(
            text=(
                f"{callback.message.text}\n\n"
                f"✅ <b>Взял в работу:</b> @{callback.from_user.username or operator_telegram_id}"
            ),
            parse_mode="HTML",
            reply_markup=None,
        )

    except (LeadNotFoundError, AccessDeniedError) as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        await logger.aerror("Ошибка при взятии заявки", lead_id=lead_id, error=str(e))
        await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)


# --- Отклонить заявку ---

@router.callback_query(F.data.startswith("lead:reject:"))
async def handle_reject_lead(
    callback: CallbackQuery,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Оператор отклоняет заявку."""
    lead_id = int(callback.data.split(":")[2])
    operator_telegram_id = callback.from_user.id

    try:
        sheets_service = GoogleSheetsService(
            credentials_path=settings.GOOGLE_CREDENTIALS_JSON,
            sheet_id=settings.GOOGLE_SHEET_ID,
        )
        lead_service = LeadService(session, sheets_service=sheets_service, bot=bot)

        # Для reject нужно сначала назначить оператора (если не назначен)
        from bot.database.repositories.operator_repo import OperatorRepository
        from bot.database.repositories.lead_repo import LeadRepository
        lead_repo = LeadRepository(session)
        operator_repo = OperatorRepository(session)
        lead = await lead_repo.get_by_id(lead_id)
        operator = await operator_repo.get_by_telegram_id(operator_telegram_id)

        if operator is None:
            await callback.answer("⛔ Вы не являетесь оператором", show_alert=True)
            return

        # Назначаем и сразу отклоняем
        if lead and lead.assigned_operator_id is None:
            lead.assigned_operator_id = operator.id
            await session.flush()

        await lead_service.change_status(lead_id, "rejected", operator_telegram_id)
        await session.commit()

        await callback.answer("Заявка отклонена")
        await callback.message.edit_text(
            text=f"{callback.message.text}\n\n❌ <b>Отклонено</b>",
            parse_mode="HTML",
            reply_markup=None,
        )

    except (LeadNotFoundError, AccessDeniedError, InvalidStatusTransitionError) as e:
        await callback.answer(str(e), show_alert=True)
    except Exception as e:
        await logger.aerror("Ошибка при отклонении заявки", lead_id=lead_id, error=str(e))
        await callback.answer("❌ Ошибка. Попробуйте позже.", show_alert=True)


# --- Ответить клиенту ---

@router.callback_query(F.data.startswith("lead:reply:"))
async def handle_reply_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    """Начало ввода ответа клиенту."""
    lead_id = int(callback.data.split(":")[2])
    await state.update_data(reply_lead_id=lead_id)
    await state.set_state(OperatorReplyState.waiting_for_reply_text)
    await callback.answer()
    await callback.message.answer(f"✍️ Введите ответ для заявки #{lead_id}:")


@router.message(OperatorReplyState.waiting_for_reply_text)
async def handle_reply_text(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
) -> None:
    """Обработка текста ответа оператора."""
    data = await state.get_data()
    lead_id = data.get("reply_lead_id")

    if not lead_id:
        await state.clear()
        await message.answer("❌ Ошибка: не найден ID заявки.")
        return

    await state.clear()
    operator_telegram_id = message.from_user.id

    try:
        dialogue_service = DialogueService(session, bot)
        await dialogue_service.send_operator_message(operator_telegram_id, lead_id, message.text)
        await session.commit()
        await message.answer(f"✅ Ответ отправлен клиенту по заявке #{lead_id}")
    except (LeadNotFoundError, AccessDeniedError) as e:
        await message.answer(f"❌ {e}")
    except Exception as e:
        await logger.aerror("Ошибка при отправке ответа", lead_id=lead_id, error=str(e))
        await message.answer("❌ Не удалось отправить ответ. Попробуйте позже.")
```

---

## ШАГ 14 — Хендлеры управления операторами (Owner)

Создать `bot/handlers/admin/operator_management.py`:

```python
"""Управление операторами — только для owner."""

import structlog
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.repositories.operator_repo import OperatorRepository
from bot.services.stats_service import StatsService
from bot.services.config_service import ConfigService, SYSTEM_MODE_LITE, SYSTEM_MODE_PRO
from bot.exceptions import OperatorNotFoundError

logger = structlog.get_logger()
router = Router(name="operator_management")


class OperatorManagementState(StatesGroup):
    waiting_for_operator_id_to_add = State()
    waiting_for_operator_id_to_remove = State()


# --- /stats ---

@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    """Показать дашборд статистики (только для owner/admin)."""
    stats_service = StatsService(session)
    data = await stats_service.get_owner_dashboard()

    avg_time = f"{data['avg_time_hours']} ч." if data['avg_time_hours'] is not None else "нет данных"

    text = (
        f"📊 <b>Дашборд LeadLock PRO</b>\n\n"
        f"📋 Всего заявок: <b>{data['total']}</b>\n"
        f"🆕 Новые: <b>{data['new']}</b>\n"
        f"🔄 В работе: <b>{data['in_progress']}</b>\n"
        f"✅ Закрыто: <b>{data['closed']}</b>\n"
        f"❌ Отклонено: <b>{data['rejected']}</b>\n\n"
        f"📅 Сегодня: <b>{data['today']}</b>\n"
        f"📅 За неделю: <b>{data['week']}</b>\n\n"
        f"💹 Конверсия: <b>{data['conversion_pct']}%</b>\n"
        f"⏱ Среднее время обработки: <b>{avg_time}</b>"
    )
    await message.answer(text, parse_mode="HTML")


# --- /mode ---

@router.message(Command("mode"))
async def cmd_mode(message: Message, session: AsyncSession) -> None:
    """Показать текущий режим и предложить переключение."""
    config_service = ConfigService(session)
    current_mode = await config_service.get_system_mode()

    builder = InlineKeyboardBuilder()
    if current_mode == SYSTEM_MODE_LITE:
        builder.button(text="🔄 Переключить на PRO", callback_data="mode:set:pro")
    else:
        builder.button(text="🔄 Переключить на LITE", callback_data="mode:set:lite")

    await message.answer(
        f"⚙️ Текущий режим: <b>{current_mode.upper()}</b>",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mode:set:"))
async def handle_mode_switch(callback: CallbackQuery, session: AsyncSession) -> None:
    """Переключить режим системы."""
    new_mode = callback.data.split(":")[2]
    config_service = ConfigService(session)

    try:
        await config_service.set_system_mode(new_mode)
        await session.commit()
        await callback.answer(f"✅ Режим переключён на {new_mode.upper()}")
        await callback.message.edit_text(
            f"⚙️ Режим изменён на: <b>{new_mode.upper()}</b>",
            parse_mode="HTML",
        )
    except ValueError as e:
        await callback.answer(str(e), show_alert=True)


# --- /list_operators ---

@router.message(Command("list_operators"))
async def cmd_list_operators(message: Message, session: AsyncSession) -> None:
    """Показать список всех операторов."""
    operator_repo = OperatorRepository(session)
    operators = await operator_repo.get_all_active()

    if not operators:
        await message.answer("👥 Операторов нет. Добавьте первого через /add_operator")
        return

    lines = ["👥 <b>Список операторов:</b>\n"]
    for op in operators:
        role_emoji = "👑" if op.role == "owner" else "👤"
        username = f"@{op.username}" if op.username else f"ID: {op.telegram_id}"
        lines.append(f"{role_emoji} {username} — {op.role}")

    await message.answer("\n".join(lines), parse_mode="HTML")


# --- /add_operator ---

@router.message(Command("add_operator"))
async def cmd_add_operator(message: Message, state: FSMContext) -> None:
    """Начать процесс добавления оператора."""
    await state.set_state(OperatorManagementState.waiting_for_operator_id_to_add)
    await message.answer(
        "👤 Введите Telegram ID нового оператора:\n\n"
        "<i>Пользователь может узнать свой ID через @userinfobot</i>",
        parse_mode="HTML",
    )


@router.message(OperatorManagementState.waiting_for_operator_id_to_add)
async def handle_add_operator_id(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Сохранить нового оператора."""
    await state.clear()

    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите числовой Telegram ID.")
        return

    operator_repo = OperatorRepository(session)
    existing = await operator_repo.get_by_telegram_id(telegram_id)
    if existing:
        await message.answer(f"ℹ️ Оператор с ID {telegram_id} уже существует.")
        return

    username = None  # username неизвестен при добавлении по ID
    await operator_repo.create(telegram_id=telegram_id, username=username)
    await session.commit()

    await message.answer(f"✅ Оператор {telegram_id} добавлен.")


# --- /remove_operator ---

@router.message(Command("remove_operator"))
async def cmd_remove_operator(message: Message, state: FSMContext) -> None:
    """Начать процесс удаления оператора."""
    await state.set_state(OperatorManagementState.waiting_for_operator_id_to_remove)
    await message.answer("🗑 Введите Telegram ID оператора для удаления:")


@router.message(OperatorManagementState.waiting_for_operator_id_to_remove)
async def handle_remove_operator_id(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    """Деактивировать оператора."""
    await state.clear()

    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID.")
        return

    operator_repo = OperatorRepository(session)
    operator = await operator_repo.deactivate(telegram_id)
    await session.commit()

    if operator:
        await message.answer(f"✅ Оператор {telegram_id} деактивирован.")
    else:
        await message.answer(f"❌ Оператор с ID {telegram_id} не найден.")
```

---

## ШАГ 15 — Обновить `bot/handlers/admin/__init__.py`

Добавить новые роутеры. **Не удалять существующие.**

```python
"""Админ-панель."""

from aiogram import Router

from .menu import router as menu_router
from .faq import router as faq_router
from .leads import router as leads_router
from .settings import router as settings_router
from .operator_callbacks import router as operator_callbacks_router
from .operator_management import router as operator_management_router

router = Router(name="admin")
router.include_router(menu_router)
router.include_router(faq_router)
router.include_router(leads_router)
router.include_router(settings_router)
router.include_router(operator_callbacks_router)
router.include_router(operator_management_router)

__all__ = ["router"]
```

> ⚠️ `operator_callbacks_router` и `operator_management_router` проходят через `AdminMiddleware` (применяется в `main.py` на весь `admin_router`). Если операторы НЕ должны проходить AdminMiddleware (они не в `settings.ADMIN_IDS`), то эти роутеры нужно регистрировать напрямую в `dp`, а не в `admin_router`. **Это критический момент — см. примечание ниже.**

---

## ШАГ 16 — Обновить `main.py`

Добавить отдельную регистрацию роутеров оператора, которые не требуют AdminMiddleware:

```python
# Добавить импорты:
from bot.handlers.admin.operator_callbacks import router as operator_callbacks_router
from bot.handlers.admin.operator_management import router as operator_management_router

# В функции main(), после регистрации admin_router:

# 4. Operator callbacks — без AdminMiddleware (операторы ≠ ADMIN_IDS)
dp.include_router(operator_callbacks_router)
await logger.ainfo("✅ Operator callbacks роутер зарегистрирован")

# 5. Operator management — без AdminMiddleware  
dp.include_router(operator_management_router)
await logger.ainfo("✅ Operator management роутер зарегистрирован")
```

> ⚠️ **Одновременно удалить** эти роутеры из `admin/__init__.py` если они там были добавлены на шаге 15. Роутер оператора регистрируется ЛИБО через admin_router (с AdminMiddleware), ЛИБО напрямую в dp (без). Решение принимается на основе бизнес-требований: если операторы = подмножество ADMIN_IDS, то через admin_router. Если операторы — отдельные пользователи, то напрямую в dp.

---

## ШАГ 17 — Обновить `requirements.txt`

Добавить Redis для FSM в PRO режиме:

```
aiogram-redis-storage==0.1.0
# или
redis==5.0.1
```

И обновить `main.py` для использования Redis если `VERSION == "PRO"`:

```python
from bot.settings import settings

if settings.VERSION == "PRO":
    from aiogram.fsm.storage.redis import RedisStorage
    storage = RedisStorage.from_url(settings.REDIS_URL)
else:
    from aiogram.fsm.storage.memory import MemoryStorage
    storage = MemoryStorage()
```

Добавить в `bot/settings.py`:
```python
REDIS_URL: str = "redis://localhost:6379/0"  # опционально, с default
```

---

## ШАГ 18 — Финальная проверка

После выполнения всех шагов проверить:

### Импорты
- [ ] `bot/database/models/__init__.py` экспортирует `LeadMessage`
- [ ] Нет циклических импортов (особенно между services)
- [ ] Все новые файлы корректно импортируются

### Миграция
- [ ] `alembic upgrade head` выполняется без ошибок
- [ ] Старые лиды сохранены (проверить `SELECT * FROM leads LIMIT 5`)
- [ ] Таблица `lead_messages` создана
- [ ] Поля `assigned_operator_id`, `closed_at`, `updated_at` добавлены в `leads`
- [ ] Поле `role` добавлено в `operators`

### Бизнес-логика
- [ ] LITE: создание заявки → уведомление ADMIN_IDS (как было)
- [ ] PRO: создание заявки → карточка в группу операторов
- [ ] PRO: оператор берёт заявку → статус `in_progress`
- [ ] PRO: переход `new` → `rejected` невозможен напрямую (только через `in_progress`)
- [ ] PRO: клиент пишет → сообщение доходит до оператора
- [ ] PRO: оператор отвечает → сообщение доходит до клиента
- [ ] Google Sheets: в LITE синхронизация сразу, в PRO — при `closed`

### Архитектура
- [ ] Нет прямых ORM-запросов в handlers
- [ ] Нет бизнес-логики (проверок прав, валидации статусов) в handlers
- [ ] `commit()` только в handlers
- [ ] Все новые исключения — из `bot/exceptions.py`

---

## ИЗВЕСТНЫЕ ПРОБЛЕМЫ ИСХОДНЫХ ТЗ (исправлены в этой версии)

1. **Отсутствовал `OperatorRepository`** — модель `Operator` была в БД но репозитория не было. Исправлено: добавлен ШАГ 6.

2. **AdminMiddleware конфликт** — исходные ТЗ предлагали добавить операторов в admin router, который защищён AdminMiddleware (проверяет `settings.ADMIN_IDS`). Операторы — отдельные пользователи. Исправлено: ШАГ 16 регистрирует операторские роутеры напрямую в `dp`.

3. **`onupdate` в SQLAlchemy** — в ТЗ был `onupdate=datetime.utcnow()` (с вызовом). Правильно: без скобок — `onupdate=datetime.utcnow`. Исправлено в ШАГ 1.1.

4. **`ConfigService` — async метод без сессии** — новые методы ConfigService требуют `session`, которая приходит из middleware. В ТЗ это не было явно указано. Исправлено: все методы — instance методы класса, сессия через `__init__`.

5. **`UserRepository.get_by_id`** — `DialogueService` требует `get_by_id(user_id)` (по внутреннему id), а в существующем коде есть только `get_by_tg_id`. Проверить и добавить при необходимости.

6. **MemoryStorage** — при рестарте теряются FSM-состояния. Критично для операторских диалогов. Исправлено: ШАГ 17 добавляет RedisStorage для PRO.

7. **`F.text` хендлер в menu.py** — обязан быть последним в роутере, иначе перехватит FSM. Явно указано в ШАГ 12.

8. **Google Sheets в LITE** — исходный `save_lead()` уже отправляет в Sheets сразу. В PRO это нельзя делать до `closed`. Исправлено: `change_status()` вызывает `_notify_sheets()` при переходе в `closed`.