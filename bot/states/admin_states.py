from aiogram.fsm.state import State, StatesGroup


class FAQEdit(StatesGroup):
    """Состояния для редактирования существующего FAQ."""
    
    selecting_item = State()  # выбор пункта (храним faq_id)
    waiting_for_question = State()  # ввод нового вопроса
    waiting_for_answer = State()  # ввод нового ответа


class FAQAdd(StatesGroup):
    """Состояния для добавления нового FAQ."""
    
    waiting_for_question = State()  # ввод нового вопроса
    waiting_for_answer = State()  # ввод нового ответа


class ConfigEdit(StatesGroup):
    """Состояния для редактирования настроек."""

    waiting_for_welcome = State()  # ввод нового приветственного текста
    waiting_for_contacts = State()  # ввод новых контактов
