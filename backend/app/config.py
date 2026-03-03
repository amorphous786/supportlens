from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SupportLens API"
    debug: bool = False
    database_url: str = "sqlite:///./supportlens.db"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3"
    # Comma-separated origins; parsed into a list by the property below.
    # Storing as str avoids pydantic_settings trying to JSON-decode the value.
    cors_origins: str = "http://localhost:3000"
    max_message_length: int = 2000
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"


settings = Settings()
