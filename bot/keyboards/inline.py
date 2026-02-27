"""
Inline-клавиатуры для бота.

Содержит CallbackData-фабрики и функции для генерации динамических inline-клавиатур.
"""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.database.models.faq_item import FAQItem


# ============================================================================
# CallbackData Фабрики
# ============================================================================


class MainMenuCD(CallbackData, prefix="main_menu"):
    """Callback для кнопок главного меню."""

    action: str  # Действие: "faq", "lead", "contact"


class FAQItemCD(CallbackData, prefix="faq_item"):
    """Callback для выбора элемента FAQ."""

    faq_id: int  # ID выбранного элемента FAQ


class BackCD(CallbackData, prefix="back"):
    """Callback для кнопки «Назад»."""

    target: str  # Куда возвращаться: "main", "faq", и т.д.


# ============================================================================
# Функции для генерации клавиатур
# ============================================================================


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """
    Генерирует главную клавиатуру с основными опциями.

    Кнопки:
    - ❓ FAQ — просмотр часто задаваемых вопросов
    - 📋 Оставить заявку — создание новой заявки
    - 📞 Связаться — контактная информация

    Returns:
        InlineKeyboardMarkup: Inline-клавиатура с главным меню
    """
    buttons = [
        [
            InlineKeyboardButton(
                text="❓ FAQ",
                callback_data=MainMenuCD(action="faq").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📋 Оставить заявку",
                callback_data=MainMenuCD(action="lead").pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📞 Связаться",
                callback_data=MainMenuCD(action="contact").pack(),
            ),
        ],
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_faq_menu_kb(faq_items: list[FAQItem]) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру с выбором элементов FAQ.

    Для каждого элемента FAQ создаётся кнопка с текстом вопроса.
    Внизу добавляется кнопка «Назад» для возврата в главное меню.

    Args:
        faq_items: Список объектов FAQItem для отображения

    Returns:
        InlineKeyboardMarkup: Inline-клавиатура со списком FAQ
    """
    buttons = []

    # Добавляем кнопки для каждого элемента FAQ
    for faq_item in faq_items:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=faq_item.question,
                    callback_data=FAQItemCD(faq_id=faq_item.id).pack(),
                ),
            ]
        )

    # Добавляем кнопку «Назад»
    buttons.append(get_back_kb(back_to="main").inline_keyboard[0])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_kb(back_to: str = "main") -> InlineKeyboardMarkup:
    """
    Генерирует универсальную кнопку «Назад».

    Используется для навигации между экранами.
    По умолчанию возвращает в главное меню.

    Args:
        back_to: Целевой экран для возврата. По умолчанию "main".
                 Возможные значения: "main", "faq", и т.д.

    Returns:
        InlineKeyboardMarkup: Inline-клавиатура с кнопкой назад
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=BackCD(target=back_to).pack(),
                ),
            ],
        ]
    )
