"""Хендлеры управления FAQ."""

import structlog
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.faq_service import FAQService
from bot.states.admin_states import FAQEdit, FAQAdd
from bot.keyboards.reply import get_cancel_kb
from .menu import show_admin_menu

logger = structlog.get_logger()

router = Router(name="admin_faq")


async def show_faq_list(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user_id = callback.from_user.id

    faq_service = FAQService(session)
    faq_items = await faq_service.get_all_faq_items()

    builder = InlineKeyboardBuilder()

    if not faq_items:
        text = "📝 FAQ пуст. Добавьте первый вопрос."

        builder.button(text="➕ Добавить FAQ", callback_data="admin:faq:add")
        builder.button(text="⬅️ Назад", callback_data="admin:main")
        builder.adjust(1)

        await logger.ainfo(
            "Отображена пустая панель FAQ",
            user_id=user_id,
        )
    else:
        text = "📝 Управление FAQ:\n\n"

        for i, item in enumerate(faq_items, start=1):
            question_short = item.question
            if len(question_short) > 25:
                question_short = question_short[:25] + "..."

            text += f"{i}. {question_short}\n"

            builder.button(
                text=f"{i}. {question_short}",
                callback_data=f"admin:faq:view:{item.id}",
            )

        builder.adjust(1)

        builder.button(text="➕ Добавить FAQ", callback_data="admin:faq:add")
        builder.button(text="⬅️ Назад", callback_data="admin:main")
        builder.adjust(1)

        await logger.ainfo(
            "Отображен список FAQ",
            user_id=user_id,
            count=len(faq_items),
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data == "admin:faq")
async def handle_admin_faq(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user_id = callback.from_user.id

    await logger.ainfo(
        "Администратор открыл управление FAQ",
        user_id=user_id,
    )

    try:
        await show_faq_list(callback, session)
        await callback.answer()
    except Exception as e:
        await logger.aerror(
            "Ошибка при отображении списка FAQ",
            user_id=user_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


@router.callback_query(F.data.startswith("admin:faq:view:"))
async def handle_faq_view(
    callback: CallbackQuery,
    session: AsyncSession,
) -> None:
    user_id = callback.from_user.id
    faq_id = int(callback.data.split(":")[-1])

    await logger.ainfo(
        "Администратор просматривает FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    try:
        faq_service = FAQService(session)
        faq_item = await faq_service.get_faq_item_by_id(faq_id)

        if not faq_item:
            await callback.answer(
                text="Элемент FAQ не найден",
                show_alert=True,
            )
            return

        text = f"📝 <b>Вопрос:</b>\n{faq_item.question}\n\n<b>Ответ:</b>\n{faq_item.answer}"

        builder = InlineKeyboardBuilder()
        builder.button(text="✏️ Редактировать", callback_data=f"admin:faq:edit:{faq_id}")
        builder.button(text="🗑️ Удалить", callback_data=f"admin:faq:del:{faq_id}")
        builder.button(text="⬅️ К списку", callback_data="admin:faq")
        builder.adjust(2, 1)

        await callback.message.edit_text(
            text=text,
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
        await callback.answer()

    except Exception as e:
        await logger.aerror(
            "Ошибка при просмотре FAQ",
            user_id=user_id,
            faq_id=faq_id,
            error=str(e),
        )
        await callback.answer(
            text="Произошла ошибка. Попробуйте позже.",
            show_alert=True,
        )


# ========================= EDIT FAQ =========================


@router.callback_query(F.data.startswith("admin:faq:edit:"))
async def handle_faq_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    user_id = callback.from_user.id
    faq_id = int(callback.data.split(":")[-1])

    await logger.ainfo(
        "Администратор начал редактирование FAQ",
        user_id=user_id,
        faq_id=faq_id,
    )

    faq_service = FAQService(session)
    faq_item = await faq_service.get_faq_item_by_id(faq_id)

    await state.update_data(
        editing_faq_id=faq_id,
        current_question=faq_item.question,
        current_answer=faq_item.answer,
    )

    await state.set_state(FAQEdit.waiting_for_question)

    await callback.message.edit_text(
        text=(
            f"✏️ <b>Текущий вопрос</b> (нажмите чтобы скопировать):\n\n"
            f"<code>{faq_item.question}</code>\n\n"
            f"Введите новый текст вопроса или нажмите Отмена:"
        ),
        parse_mode="HTML",
    )
    await callback.message.answer("👇", reply_markup=get_cancel_kb())
    await callback.answer()


@router.message(FAQEdit.waiting_for_question)
async def handle_faq_edit_question(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Редактирование отменено", reply_markup=ReplyKeyboardRemove())
        await show_admin_menu(message)
        return

    user_id = message.from_user.id
    new_question = message.text

    await logger.ainfo(
        "Администратор ввёл новый вопрос",
        user_id=user_id,
        question_length=len(new_question),
    )

    data = await state.get_data()
    current_answer = data.get("current_answer", "")

    await state.update_data(new_question=new_question)
    await state.set_state(FAQEdit.waiting_for_answer)

    await message.answer(
        text=(
            f"✏️ <b>Текущий ответ</b> (нажмите чтобы скопировать):\n\n"
            f"<code>{current_answer}</code>\n\n"
            f"Введите новый текст ответа или нажмите Отмена:"
        ),
        parse_mode="HTML",
        reply_markup=get_cancel_kb(),
    )


@router.message(FAQEdit.waiting_for_answer)
async def handle_faq_edit_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Редактирование отменено", reply_markup=ReplyKeyboardRemove())
        await show_admin_menu(message)
        return

    user_id = message.from_user.id
    new_answer = message.text

    await logger.ainfo(
        "Администратор ввёл новый ответ",
        user_id=user_id,
        answer_length=len(new_answer),
    )

    try:
        data = await state.get_data()
        faq_id = data["editing_faq_id"]
        new_question = data["new_question"]

        faq_service = FAQService(session)
        await faq_service.repository.update(
            faq_id=faq_id,
            question=new_question,
            answer=new_answer,
        )

        await session.commit()

        await message.answer("✅ FAQ обновлён!", reply_markup=ReplyKeyboardRemove())

        await state.clear()

        await logger.ainfo(
            "FAQ успешно обновлён",
            user_id=user_id,
            faq_id=faq_id,
        )

        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при обновлении FAQ",
            user_id=user_id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()


# ========================= ADD FAQ =========================


@router.callback_query(F.data == "admin:faq:add")
async def handle_faq_add_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    builder = InlineKeyboardBuilder()
    builder.button(text="✨ Услуга/Цена", callback_data="admin:faq:category:services")
    builder.button(text="❓ Вопрос/Ответ", callback_data="admin:faq:category:faq")
    builder.button(text="⬅️ Назад", callback_data="admin:faq")
    builder.adjust(2, 1)

    await callback.message.edit_text(
        text="➕ Выберите категорию для нового FAQ:",
        reply_markup=builder.as_markup(),
    )

    await state.set_state(FAQAdd.waiting_for_category)
    await callback.answer()


@router.callback_query(F.data.startswith("admin:faq:category:"))
async def handle_faq_add_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[-1]

    await state.update_data(category=category)
    await state.set_state(FAQAdd.waiting_for_question)

    await callback.message.edit_text(
        text="➕ Введите текст ВОПРОСА или названия услуги:"
    )
    await callback.message.answer("👇", reply_markup=get_cancel_kb())
    await callback.answer()


@router.message(FAQAdd.waiting_for_question)
async def handle_faq_add_question(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=ReplyKeyboardRemove())
        await show_admin_menu(message)
        return

    new_question = message.text
    await state.update_data(new_question=new_question)
    await state.set_state(FAQAdd.waiting_for_answer)

    await message.answer("➕ Теперь введите текст ОТВЕТА:", reply_markup=get_cancel_kb())


@router.message(FAQAdd.waiting_for_answer)
async def handle_faq_add_answer(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
) -> None:
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено", reply_markup=ReplyKeyboardRemove())
        await show_admin_menu(message)
        return

    new_answer = message.text

    try:
        data = await state.get_data()
        new_question = data["new_question"]
        category = data.get("category", "faq")

        faq_service = FAQService(session)
        faq_item = await faq_service.repository.create(
            question=new_question,
            answer=new_answer,
            category=category,
        )

        await session.commit()

        await message.answer("✅ Новый FAQ добавлен!", reply_markup=ReplyKeyboardRemove())

        await state.clear()

        await show_admin_menu(message)

    except Exception as e:
        await logger.aerror(
            "Ошибка при добавлении FAQ",
            user_id=message.from_user.id,
            error=str(e),
        )
        await message.answer(
            text="❌ Произошла ошибка при сохранении. Попробуйте позже.",
        )
        await state.clear()