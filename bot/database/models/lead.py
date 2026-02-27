"""Модель конфигурации лидов."""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from bot.database.models.base import Base


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="new")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    user = relationship("User", back_populates="leads")

    def __repr__(self):
        return f"<Lead(id={self.id}, user_id={self.user_id}, name='{self.name}', status='{self.status}')>"
