from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./hackathon_radar.db"
    SECRET_KEY: str = "change-this-secret-key"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()
