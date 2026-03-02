"""Миграция: добавить поле category в таблицу faq_items."""

import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from bot.settings import settings


async def main() -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'faq_items' 
            AND column_name = 'category'
        """))
        exists = result.fetchone()

        if exists:
            print("✅ Колонка category уже существует")
        else:
            await conn.execute(text("""
                ALTER TABLE faq_items 
                ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT 'faq'
            """))
            print("✅ Колонка category добавлена")

    await engine.dispose()
    print("✅ Миграция завершена")


if __name__ == "__main__":
    asyncio.run(main())