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
    config_repo = ConfigRepository(session)

    welcome_text = (
        "Добро пожаловать в детейлинг студию! 🚗✨\n\n"
        "Профессиональный уход за вашим автомобилем.\n"
        "Выберите интересующий вас раздел:"
    )

    contacts = (
        "📞 +7‒914‒958‒51‒88\n"
        "📞 +7‒904‒127‒23‒23\n\n"
        "🕐 Уточняйте время записи по телефону"
    )

    location = (
        "34-й микрорайон, ст41 этаж\n"
        "Въезд с ул. Енисейская\n"
        "Ангарск, Иркутская область"
    )

    maps_url = "https://go.2gis.com/rqQ8Z"

    await config_repo.set_value("welcome_text", welcome_text)
    await config_repo.set_value("contacts", contacts)
    await config_repo.set_value("location", location)
    await config_repo.set_value("maps_url", maps_url)

    await logger.ainfo("Конфигурация обновлена")


async def seed_faq(session: AsyncSession) -> None:
    """
    Перезаписывает FAQ и услуги без проверки существующих записей.
    """

    faq_repo = FAQRepository(session)

    # Услуги
    service_items = [
        {
            "question": "Полировка кузова",
            "answer": "Восстанавливаем блеск и убираем царапины. От 3 000 руб. Время: от 8 часов.",
            "category": "services",
        },
        {
            "question": "Керамическое покрытие",
            "answer": "Защита на 2-3 года. Цена от 15 000 руб. Гарантия 2 года.",
            "category": "services",
        },
        {
            "question": "Химчистка салона",
            "answer": "Полная чистка салона, удаление запахов. От 4 000 руб. Время: от 4 часов.",
            "category": "services",
        },
        {
            "question": "Бронирование плёнкой",
            "answer": "Защита кузова от царапин и сколов. От 5 000 руб. за элемент.",
            "category": "services",
        },
        {
            "question": "Детейлинг двигателя",
            "answer": "Профессиональная мойка и чистка двигателя. От 2 000 руб.",
            "category": "services",
        },
    ]

    # FAQ
    faq_items = [
        {
            "question": "Как долго ждать?",
            "answer": "Химчистка — от 4 часов. Полировка — от 8 часов. Керамика — от 2 дней. Уточняйте при записи.",
            "category": "faq",
        },
        {
            "question": "Есть ли гарантия?",
            "answer": "На керамику — 2 года. На все работы — письменная гарантия качества.",
            "category": "faq",
        },
        {
            "question": "Как записаться?",
            "answer": "Позвоните +7‒914‒958‒51‒88 или оставьте заявку — перезвоним в течение часа!",
            "category": "faq",
        },
        {
            "question": "Можно ли приехать без записи?",
            "answer": "Лучше записаться заранее — мастера могут быть заняты. Запись по телефону или через бота.",
            "category": "faq",
        },
    ]

    all_items = service_items + faq_items

    for item in all_items:
        await faq_repo.create(
            question=item["question"],
            answer=item["answer"],
            category=item["category"],
        )

        await logger.ainfo(
            "Добавлена запись",
            question=item["question"],
            category=item["category"],
        )

    await logger.ainfo("Заполнение FAQ завершено", count=len(all_items))


async def main() -> None:
    await logger.ainfo("Запуск скрипта заполнения БД")

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
            await seed_config(session)
            await seed_faq(session)

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