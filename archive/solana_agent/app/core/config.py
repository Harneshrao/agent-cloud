from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/solana_agent"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Solana
    SOLANA_RPC_URL: str = "https://api.devnet.solana.com"
    SOLANA_PAYER_PRIVATE_KEY: str = ""
    SOLANA_RECIPIENT_ADDRESS: str = ""  # Public key of wallet that receives payment

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-me"


settings = Settings()
