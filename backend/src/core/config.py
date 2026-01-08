from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int

    OPENAI_API_KEY: str
    OPENAI_API_BASE: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o"

    @property
    def database_url(self) -> str:
        # Construct the connection string
        # Note: When running in Docker, POSTGRES_HOST should be 'host.docker.internal' to check local machine
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
