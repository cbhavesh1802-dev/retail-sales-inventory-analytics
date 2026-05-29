from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    github_token: str
    github_webhook_secret: str
    snyk_token: str

    class Config:
        env_file = ".env"

settings = Settings()
