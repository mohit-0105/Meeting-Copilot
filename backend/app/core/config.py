from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    STT_PROVIDER: str = "mock"
    DEEPGRAM_API_KEY: str = ""

    LLM_PROVIDER: str = "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
