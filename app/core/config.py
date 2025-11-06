from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # OpenAI Configuration
    OPENAI_API_KEY: str

    # JWT Configuration
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 3

    # Admin Credentials
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str

    # API Configuration
    API_TITLE: str = "Audio Transcription Service"
    API_VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )


settings = Settings()
