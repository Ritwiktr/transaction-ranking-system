from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./local.db"
    cors_origins: str = "*"
    rate_limit_per_minute: int = 30
    min_amount: int = 1
    max_amount: int = 10_000


settings = Settings()
