"""Модель конфигурации бота."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from bot.database.models.base import Base


class Config(Base):
    """Модель для хранения конфигурации бота."""

    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    def __repr__(self) -> str:
        return f"<Config(key={self.key}, value={self.value[:50]}...)>"
