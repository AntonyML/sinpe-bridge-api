from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Conectar con supabase
    DATABASE_URL: str
    DEBUG: bool = False

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
