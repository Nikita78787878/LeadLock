"""Миграция: добавить поле synced_to_sheets в таблицу leads."""

import asyncio
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from bot.settings import settings

logger = structlog.get_logger()


async def main() -> None:
    """Добавить колонку synced_to_sheets в таблицу leads если не существует."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        # Проверяем существует ли колонка
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'leads' 
            AND column_name = 'synced_to_sheets'
        """))
        exists = result.fetchone()

        if exists:
            print("✅ Колонка synced_to_sheets уже существует")
        else:
            await conn.execute(text("""
                ALTER TABLE leads 
                ADD COLUMN synced_to_sheets BOOLEAN NOT NULL DEFAULT FALSE
            """))
            print("✅ Колонка synced_to_sheets успешно добавлена")

    await engine.dispose()
    print("✅ Миграция завершена")


if __name__ == "__main__":
    asyncio.run(main())