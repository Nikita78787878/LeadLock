from aiogram.fsm.state import State, StatesGroup


class LeadForm(StatesGroup):
    """Состояния FSM для формы сбора заявки."""
    # Ожидание ввода имени
    waiting_for_name = State()
    # Ожидание ввода телефона
    waiting_for_phone = State()
    # Ожидание ввода описания проблемы
    waiting_for_description = State()
