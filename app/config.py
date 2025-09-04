from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    app_env: str = "production"
    agent_url: str
    agent_api_key: str
    x_api_key: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
