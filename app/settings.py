from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    CLOUDFLARE_API_KEY: str
    CLOUDFLARE_ACCOUNT_ID: str
    CLOUDFLARE_IMAGE_GEN_MODEL: str

    GEMINI_API_KEY: str

    OPENAI_API_KEY: str

    MEME_FONT_PATH: str
    MEME_FONT_PATH_KOR: str

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "meme_keywords"

    MYSQL_URL: str

    SCHEDULER_HOUR: int
    SCHEDULER_MINUTE: int

    LANGSMITH_TRACING: bool
    LANGSMITH_ENDPOINT: str
    LANGSMITH_API_KEY: str
    LANGSMITH_PROJECT: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    AWS_S3_BUCKET_NAME: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


app_config = Settings()  # type: ignore
