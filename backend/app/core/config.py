from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "change-this-secret-key"
    DEBUG: bool = True

    model_config = ConfigDict(env_file=".env")


settings = Settings()
