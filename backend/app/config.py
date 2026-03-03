from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "SupportLens API"
    debug: bool = False
    database_url: str = "sqlite:///./supportlens.db"
    ollama_base_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "llama3"

    class Config:
        env_file = ".env"


settings = Settings()
