import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database configuration
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    SECRET_KEY: str
    SQLALCHEMY_DATABASE_URI: str
    GEMINI_API_KEY: str
    class Config:
        env_file = os.path.join(os.path.dirname(__file__), '../.env')
        env_file_encoding = 'utf-8'

settings = Settings()
