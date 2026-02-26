from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    DATABASE_URL: str
    VERSION: Literal["LITE", "PRO", "AI"]
    GOOGLE_SHEET_ID: str
    GOOGLE_CREDENTIALS_JSON: str
    OPENAI_API_KEY: str
    ADMIN_IDS: list[int]
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
