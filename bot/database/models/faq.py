from sqlalchemy import Column, Integer, String, Text
from bot.database.base import Base


class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True)
    key = Column(String(100), nullable=False, unique=True, index=True)
    question = Column(String(500), nullable=False)
    answer = Column(Text, nullable=False)

    def __repr__(self):
        return f"<FAQ(id={self.id}, key='{self.key}')>"
