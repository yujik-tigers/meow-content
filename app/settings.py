from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    CLOUDFLARE_API_KEY: str
    CLOUDFLARE_ACCOUNT_ID: str
    CLOUDFLARE_IMAGE_GEN_MODEL: str

    model_config = SettingsConfigDict(env_file=".env")


app_config = Settings()  # type: ignore
