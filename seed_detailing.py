"""Скрипт для заполнения базы данных начальными данными для детейлинга."""

import asyncio
import structlog
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from bot.settings import settings
from bot.database.repositories.config_repo import ConfigRepository
from bot.database.repositories.faq_repo import FAQRepository

logger = structlog.get_logger()


async def seed_config(session: AsyncSession) -> None:
    """
    Заполнить конфигурацию начальными данными.

    Args:
        session: Сессия БД
    """
    config_repo = ConfigRepository(session)

    # Приветственный текст
    welcome_text = (
        "Добро пожаловать в детейлинг студию! 🚗✨\n\n"
        "Профессиональный уход за вашим автомобилем.\n"
        "Выберите интересующий вас раздел:"
    )

    # Контакты
    contacts = (
        "📞 +7‒914‒958‒51‒88\n"
        "📞 +7‒904‒127‒23‒23\n\n"
        "📍 34-й микрорайон, ст41 этаж\n"
        "Въезд с ул. Енисейская\n"
        "Ангарск, Иркутская область\n\n"
        "🕐 Уточняйте время записи по телефону"
    )

    # Проверяем и добавляем welcome_text
    existing_welcome = await config_repo.get_by_key("welcome_text")
    if not existing_welcome:
        await config_repo.set_value("welcome_text", welcome_text)
        await logger.ainfo("Добавлен приветственный текст")
    else:
        await logger.ainfo("Приветственный текст уже существует")

    # Проверяем и добавляем contacts
    existing_contacts = await config_repo.get_by_key("contacts")
    if not existing_contacts:
        await config_repo.set_value("contacts", contacts)
        await logger.ainfo("Добавлены контакты")
    else:
        await logger.ainfo("Контакты уже существуют")


async def seed_faq(session: AsyncSession) -> None:
    """
    Заполнить FAQ начальными данными.

    Args:
        session: Сессия БД
    """
    faq_repo = FAQRepository(session)

    # Проверяем, есть ли уже FAQ
    existing_faq = await faq_repo.get_all()
    if existing_faq:
        await logger.ainfo("FAQ уже заполнен", count=len(existing_faq))
        return

    # Список FAQ для детейлинга
    faq_items = [
        {
            "question": "Какие услуги вы оказываете?",
            "answer": "Полировка кузова, керамическое покрытие, химчистка салона, бронирование плёнкой, детейлинг двигателя и многое другое 🔧",
        },
        {
            "question": "Сколько стоит полировка?",
            "answer": "Стоимость зависит от класса автомобиля и вида работ. Позвоните нам для расчёта: +7‒914‒958‒51‒88",
        },
        {
            "question": "Как долго ждать?",
            "answer": "Химчистка салона — от 4 часов. Полировка — от 8 часов. Керамика — от 2 дней. Точные сроки уточняйте при записи.",
        },
        {
            "question": "Есть ли гарантия?",
            "answer": "На керамическое покрытие — гарантия 2 года. На все виды работ даём письменную гарантию качества.",
        },
        {
            "question": "Как записаться?",
            "answer": "Позвоните по номеру +7‒914‒958‒51‒88 или оставьте заявку прямо здесь — мы перезвоним в течение часа!",
        },
    ]

    # Добавляем FAQ
    for item in faq_items:
        await faq_repo.create(
            question=item["question"],
            answer=item["answer"],
        )
        await logger.ainfo("Добавлен FAQ", question=item["question"])

    await logger.ainfo("Добавлено FAQ записей", count=len(faq_items))


async def main() -> None:
    """Главная функция для заполнения БД."""
    await logger.ainfo("Запуск скрипта заполнения БД")

    # Создаём движок и сессию
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )

    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        try:
            # Заполняем конфигурацию
            await seed_config(session)

            # Заполняем FAQ
            await seed_faq(session)

            # Коммитим изменения
            await session.commit()
            await logger.ainfo("Все изменения успешно сохранены")

        except Exception as e:
            await logger.aerror("Ошибка при заполнении БД", error=str(e))
            await session.rollback()
            raise

        finally:
            await engine.dispose()

    await logger.ainfo("Скрипт заполнения БД завершён")


if __name__ == "__main__":
    asyncio.run(main())
