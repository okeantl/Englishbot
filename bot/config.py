from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    bot_token: str
    database_url: str = "sqlite+aiosqlite:///./english_bot.db"

    llm_api_key: str | None = None
    llm_base_url: str | None = "https://openrouter.ai/api/v1"
    llm_model: str = "google/gemma-4-31b-it:free"
    llm_fallback_models: list[str] = ["google/gemma-4-26b-a4b-it:free", "nvidia/nemotron-3.5-lightning:free"]

    admin_ids: list[int] = []
    timezone: str = "Europe/Moscow"


settings = Settings()
