# 📱 LITE Edition - User & Admin Interface Guide

> Comprehensive guide describing the user interface and admin panel in LITE version of the Telegram Bot

**Версия:** LITE  
**Язык интерфейса:** Русский  
**Целевая аудитория:** Конечные пользователи и администраторы LITE версии

---

## 📋 Table of Contents

- [Overview](#overview)
- [User Interface](#user-interface)
  - [User Flows & Commands](#user-flows--commands)
  - [Main Menu](#main-menu)
  - [FAQ Section](#faq-section)
  - [Lead Generation Form](#lead-generation-form)
  - [Help & Support](#help--support)
- [Admin Interface](#admin-interface)
  - [Admin Commands](#admin-commands)
  - [FAQ Management](#faq-management)
  - [Lead Management](#lead-management)
  - [Bot Settings](#bot-settings)
- [Message Examples](#message-examples)
- [FSM States Flow](#fsm-states-flow)
- [User Roles & Permissions](#user-roles--permissions)

---

## 🎯 Overview

LITE Edition provides a minimal but fully functional Telegram bot interface with two main user roles:

| Role | Permissions | Features |
|------|-------------|----------|
| **User** | Read-only | Browse FAQ, Submit leads, View help |
| **Admin** | Full control | Create/Edit FAQ, View leads, Configure bot, Manage users |

---

## 👥 User Interface

### User Flows & Commands

#### Available Commands for Users

| Command | Description | Access |
|---------|-------------|--------|
| `/start` | Initialize bot, show main menu | Everyone |
| `/admin` | Access admin panel (admin only) | Admin users only |

---

### Main Menu

**Trigger:** `/start` or `/menu` command

**Bot Response:**
```
Добро пожаловать! 👋

Я ваш персональный помощник. Выберите, что вас интересует:
Услуги и цены
[FAQ] Частые вопросы
[contscts] Позвонить нам
[maps_url]Как нас найти
[Оставить заявку] Записаться 

**Buttons:**
- `📚 Часто задаваемые вопросы` → FAQ Section
- `📝 Оставить заявку` → Lead Generation Form

**Keyboard Type:** Reply keyboard (persistent)

---

### FAQ Section

#### Step 1: View FAQ Categories/Questions

**Trigger:** User clicks `📚 Часто задаваемые вопросы`

**Bot Response:**
```
Часто задаваемые вопросы:

[1] Как это работает?
[2] Какая цена?
[3] Есть ли у вас поддержка?
[4] Как начать работу?

Выберите интересующий вас вопрос ☝️

Навигация: /start - вернуться в главное меню
```

**Buttons:** Inline keyboard with FAQ items
- Each button shows question number and short question text
- `callback_data`: `faq_{faq_id}`


--

### Lead Generation Form

#### FSM State: `LeadFormStates`

**Trigger:** User clicks `📝 Оставить заявку`

---

#### Step 1: Enter Full Name

**FSM State:** `LeadFormStates.WAITING_FOR_NAME`

**Bot Response:**
```
📝 Оставить заявку

Шаг 1/3: Укажите ваше имя

Пожалуйста, введите ваше полное имя:
```

**Buttons:** Reply keyboard
- `/отмена` - Cancel the form

**Validation:**
- Min length: 2 characters
- Max length: 100 characters
- No special characters

**Error Response (if invalid):**
```
❌ Имя должно содержать от 2 до 100 символов.

Попробуйте еще раз:
```

---

#### Step 2: Enter Phone Number

**FSM State:** `LeadFormStates.WAITING_FOR_PHONE`

**Bot Response:**
```
📝 Оставить заявку

Шаг 2/3: Укажите ваш номер телефона

Введите номер телефона (формат: +7(XXX)XXX-XX-XX или 89XX-XXX-XX-XX):
```

**Buttons:** Reply keyboard with quick options
- `📱 Поделиться контактом` - Share contact via Telegram

**Validation:**
- Russian phone numbers only
- Patterns: `+7(***)***, 8(***)***, +*` etc.
- Min 10 digits

**Error Response (if invalid):**
```
❌ Пожалуйста, введите корректный номер телефона.

Примеры:
• +7(999)123-45-67
• 89991234567

Или нажмите "Поделиться контактом" для быстрой передачи:
```

---

#### Step 3: Enter Description/Message

**FSM State:** `LeadFormStates.WAITING_FOR_DESCRIPTION`

**Bot Response:**
```
📝 Оставить заявку

Шаг 3/3: Расскажите о вашем вопросе (необязательно)

Введите текст вашего сообщения или нажмите /пропустить для пропуска:
```

**Buttons:** Reply keyboard
- `/отмена` - Cancel form

**Validation:**
- Max length: 1000 characters
- Optional field (can skip)


#### Step 4: Success Confirmation

**Bot Response:**
```
🎉 Спасибо за вашу заявку!

Ваша заявка успешно отправлена.
Мы свяжемся с вами в ближайшее время.

───────────────────────────

[← Главное меню]
```

**Data Saved to Database:**
```python
lead = {
    "id": "uuid",
    "user_id": "uuid",
    "name": "Иван Петров",
    "phone": "+7(999)123-45-67",
    "description": "Интересует информация о ценах",
    "status": "new",  # enum: new, contacted, converted, rejected
    "created_at": "2024-01-15T14:30:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
}
```

**Google Sheets Export:**
- Automatically added to Google Sheet
- Columns: `ID | Name | Phone | Message | Date | Status`

---


## 🔐 Admin Interface

### Admin Commands

**Requirement:** `is_admin = TRUE` in `users` table

#### Available Commands

| Command | Description | Access |
|---------|-------------|--------|
| `/admin` | Open admin panel | Admin only |

**Access Denied Response (if user is not admin):**
```
🚫 Доступ запрещен

У вас нет прав администратора.
Если это ошибка, свяжитесь с владельцем бота.
```

---

### Admin Panel Main Menu

**Trigger:** `/admin`

**Bot Response:**
```
🔧 Панель администратора

Добро пожаловать в панель администратора!

Выберите нужный вам раздел:

[FAQ] 📚 Управление FAQ
[Заявки] 📋 Просмотр заявок
[Настройки] ⚙️ Параметры бота
[Назад] 🏠 Главное меню
```

**Buttons:** Reply keyboard
- `📚 Управление FAQ` → FAQ Management
- `📋 Просмотр заявок` → Lead Management
- `⚙️ Параметры бота` → Bot Settings
- `🏠 Главное меню` → Return to user main menu

---

### FAQ Management

#### Admin Submenu: FAQ Management

**Trigger:** Admin clicks `📚 Управление FAQ`

**Bot Response:**
```
📚 Управление FAQ

Выберите действие:

[Добавить] ➕ Добавить новый вопрос
[Редактировать] ✏️ Редактировать вопрос
[Удалить] 🗑️ Удалить вопрос
[Назад] ◀️ Вернуться
```

**Buttons:** Reply keyboard
- `➕ Добавить новый вопрос` → Create FAQ
- `✏️ Редактировать вопрос` → Edit FAQ
- `🗑️ Удалить вопрос` → Delete FAQ
- `📋 Просмотреть все вопросы` → List FAQ

---

#### Create FAQ Item

**FSM State:** `AdminFAQStates.WAITING_FOR_QUESTION`

**Step 1: Enter Question**

**Bot Response:**
```
➕ Добавление нового вопроса

Шаг 1/2: Введите вопрос

Напишите вопрос, на который будет ответ:
```
**Error Response:**
---

**FSM State:** `AdminFAQStates.WAITING_FOR_ANSWER`

**Step 2: Enter Answer**

**Bot Response:**
```
➕ Добавление нового вопроса

Шаг 2/2: Введите ответ


---

───────────────────────────


**Buttons:** Inline keyboard
- `❌ Отмена` → Cancel and return

---

**Success Response:**
```
✅ Вопрос добавлен успешно!


───────────────────────────

```

**Database Record:**
```python
faq_item = {
    "id": "uuid",
    "question": "Как это работает?",
    "answer": "Ответ...",
    "category": None,  # nullable for LITE
    "order": 5,  # auto-increment
    "is_active": True,
    "created_at": "2024-01-15T14:45:00Z",
    "updated_at": "2024-01-15T14:45:00Z"
}

#### Edit FAQ Item

**Trigger:** Admin clicks `✏️ Редактировать вопрос`

**Bot Response (Step 1: List FAQ):**
```
✏️ Редактирование вопроса

Выберите вопрос для редактирования:

[1] Как это работает?
[2] Какая цена?
[3] Есть ли у вас поддержка?

Нажмите на номер вопроса ☝️
```

**Buttons:** Inline keyboard
- Each FAQ item as a button with `callback_data: edit_faq_{id}`

---

**FSM State:** `AdminFAQStates.EDITING_QUESTION`

**Step 2: Edit Question or Answer**

**Bot Response:**
```
✏️ Редактирование вопроса

Текущий вопрос: Как это работает?

```

**Buttons:** Reply keyboard with options

---

**Update Success Response:**
```
✅ Вопрос обновлен успешно!

Изменения вступили в силу немедленно.
Пользователи увидят обновленную информацию.

───────────────────────────

[← Назад]
```

---

#### Delete FAQ Item

**Trigger:** Admin clicks `🗑️ Удалить вопрос`

**Bot Response (Step 1):**
```
🗑️ Удаление вопроса
```

**Buttons:** Inline keyboard with FAQ items

---


───────────────────────────
 [❌ Отмена]
```
**Buttons:** Inline keyboard
- `❌ Отмена` → Cancel

---

**Deletion Success Response:**
```
✅ Вопрос удален!

───────────────────────────
 [← Назад]
```

---


### Lead Management

#### View All Leads

**Trigger:** Admin clicks `📋 Последние заявки`

**Bot Response (Page 1):**
```
📋 Все заявки

[#2024-047] Новая ❌
  📝 Иван Петров
  📱 +7(999)123-45-67
  📅 15.01.2024 14:30

[#2024-046] Обработана ✅
  📝 Мария Сидорова
  📱 +7(999)987-65-43
  📅 15.01.2024 13:15

[#2024-045] Отклонена ❌
  📝 Петр Козлов
  📱 +7(999)555-55-55
  📅 14.01.2024 16:40
```


---

#### View Single Lead Details

**Trigger:** Admin clicks on a lead

**Bot Response:**
```
📋 Детали заявки #2024-047

────────────────────────────

📝 ИМЯ:
Иван Петров

📱 ТЕЛЕФОН:
+7(999)123-45-67

💬 СООБЩЕНИЕ:
Интересует информация о ценах и сроках доставки.
Нужна срочная консультация.
────────────────────────────
📅 ДАТА СОЗДАНИЯ: 15.01.2024 14:30

────────────────────────────
```


### Bot Settings

#### Settings Menu

**Trigger:** Admin clicks `⚙️ Параметры бота`

**Bot Response:**
```
⚙️ Параметры бота

Текущие настройки:

Версия бота: LITE v1.0.0

────────────────────────────

[Информация] 📝 Текст приветствия
[Контакты] 📞 Контактная информация

[Назад] 
```

**Buttons:** Reply keyboard with settings sections

---

#### Edit Welcome Message

**Trigger:** Admin clicks `📝 Текст приветствия`

**Bot Response:**
```
📝 Текст приветствия

Текущий текст:

"Добро пожаловать! 👋

Я ваш персональный помощник. Выберите, что вас интересует:
..."

────────────────────────────

```

---

#### Edit Contact Information

**Trigger:** Admin clicks `📞 Контактная информация`

**Bot Response:**
```
📞 Контактная информация

Текущие контакты:

Телефон: +7(999)555-55-55

────────────────────────────

[Назад] ◀️
```

**Buttons:** Inline keyboard

---

**Edit Single Field:**

**Bot Response:**
```
☎️ Редактирование телефона

Текущий: +7(999)555-55-55

Введите новый номер телефона:
```

**Validation:**
- Format: Russian phone numbers or standard formats

---

---

## 📝 Message Examples

### Success Messages

```python
# Lead submitted successfully
"🎉 Спасибо за вашу заявку!\n\n"
"Ваша заявка успешно отправлена.\n"
"Мы свяжемся с вами в ближайшее время.\n\n"

# FAQ item created
"✅ Вопрос добавлен успешно!\n\n"

```

### Error Messages

```python
# Invalid phone number
"❌ Пожалуйста, введите корректный номер телефона.\n\n"
"Примеры:\n"
"• +7(999)123-45-67\n"
"• 89991234567"

# Input too short
"❌ Имя должно содержать от 2 до 100 символов.\n\n"
"Попробуйте еще раз:"

# Form cancelled
"❌ Оформление заявки отменено.\n\n"
"Возвращаемся в главное меню..."

# Unauthorized access
"🚫 Доступ запрещен\n\n"
"У вас нет прав администратора."
```

### Info Messages

```python
# Form step indicator
"📝 Оставить заявку\n\n"
"Шаг 2/3: Укажите ваш номер телефона"


# Pagination info
"📋 Последние заявки\n\n"
```

---

## 🔄 FSM States Flow

### User Lead Form FSM

```
START
  ↓
/start or menu button
  ↓
MAIN_MENU
  ↓
User clicks "📝 Оставить заявку"
  ↓
LeadFormStates.WAITING_FOR_NAME
  ├─ Valid input → Next step
  └─ Invalid → Error message → Retry
  ↓
LeadFormStates.WAITING_FOR_PHONE
  ├─ Valid input → Next step
  └─ Invalid → Error message → Retry
  ↓
LeadFormStates.WAITING_FOR_DESCRIPTION
  ├─ Input (or skip) → Next step
  └─ /отмена → Cancel to main menu
  ↓
LeadFormStates.CONFIRM
  ├─ ✅ Confirm → Save to DB
  └─ ❌ Cancel → Discard
  ↓
SUCCESS_MESSAGE
  ↓
MAIN_MENU
```

---

### Admin FAQ Management FSM

```
/admin
  ↓
ADMIN_MENU
  ↓
User clicks "📚 Управление FAQ"
  ↓
FAQ_MENU
  ├─ "Добавить"
  │   ├─ AdminFAQStates.WAITING_FOR_QUESTION
  │   ├─ AdminFAQStates.WAITING_FOR_ANSWER
  │   ├─ AdminFAQStates.CONFIRM
  │   └─ → Save to DB → SUCCESS
  ├─ "Редактировать"
  │   ├─ Show FAQ list
  │   ├─ AdminFAQStates.EDITING_QUESTION
  │   ├─ AdminFAQStates.CONFIRM_EDIT
  │   └─ → Update DB → SUCCESS
  └─ "Удалить"
      ├─ Show FAQ list
      ├─ AdminFAQStates.CONFIRM_DELETE
      └─ → Delete from DB → SUCCESS
  ↓
ADMIN_MENU
```

---

## 👤 User Roles & Permissions

### User Role

**Telegram Field:** `users.is_admin = FALSE`

**Permissions:**
```python
{
    "read_faq": True,           # Can view FAQ
    "submit_leads": True,       # Can create leads
    "access_admin": False,      # Cannot access admin panel
    "edit_faq": False,          # Cannot edit FAQ
    "manage_leads": False,      # Cannot view other leads
    "configure_bot": False,     # Cannot change settings
}
```

**Available Commands:**
- `/start` - Show main menu

---

### Admin Role

**Telegram Field:** `users.is_admin = TRUE`

**Permissions:**
```python
{
    "read_faq": True,           # Can view FAQ
    "submit_leads": True,       # Can create leads (optional)
    "view_help": True,          # Can view help page
    "access_admin": True,       # Can access admin panel
    "edit_faq": True,           # Can create/edit/delete FAQ
    "manage_leads": True,       # Can view all leads & update status
    "configure_bot": True,      # Can change bot settings
    "export_leads": True,       # Auto-export to Google Sheets
}
```

**Available Commands:**
- `/start` - Show main menu
- `/admin` - Open admin panel

---

### Permission Check Middleware

**Location:** `bot/middlewares/admin_middleware.py`

```python
async def check_admin_access(user_id: int) -> bool:
    """Check if user has admin permissions"""
    user = await user_repo.get_by_telegram_id(user_id)
    if not user or not user.is_admin:
        return False
    return True
```

**Applied to:**
- `/admin` command
- Admin handlers
- Admin callbacks
- Settings modification

---

## 📊 Database Schema for LITE

### users table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255) NULLABLE,
    first_name VARCHAR(255) NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### faq_items table

```sql
CREATE TABLE faq_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question VARCHAR(500) NOT NULL,
    answer TEXT NOT NULL,
    category VARCHAR(100) NULLABLE,  -- Not used in LITE (for future)
    "order" INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### leads table

```sql
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    description TEXT NULLABLE,
    status VARCHAR(50) DEFAULT 'new',  -- new, contacted, converted, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### config table (for settings)

```sql
CREATE TABLE config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    data_type VARCHAR(50) DEFAULT 'string',  -- string, json, bool
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sample data
INSERT INTO config (key, value, data_type) VALUES
    ('welcome_text', '...', 'string'),
    ('contacts', '+7(999)555-55-55', 'string'),
    ('email', 'support@company.com', 'string'),
    ('location', 'Ангарск улица рябикова 32', 'string'),
    ('maps_url', 'https://go.2gis.com/rqQ8Z', 'string');
```

---


---

## 📞 Support & Maintenance

### Common Admin Tasks

**Adding a new FAQ:**
1. Open admin panel: `/admin`
2. Click `📚 Управление FAQ`
3. Click `➕ Добавить новый вопрос`
4. Enter question and answer
5. Confirm

**Changing bot settings:**
1. Open admin panel: `/admin`
2. Click `⚙️ Параметры бота`
3. Select what to change
4. Enter new values
5. Confirm

---

