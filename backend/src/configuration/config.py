from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] 
ENV_PATH = str(BASE_DIR / ".env") 

print(f"--- Alembic Debug: Looking for .env file at: {ENV_PATH} ---")

class Settings(BaseSettings):
    # Enforce case_sensitive=False so lower/uppercase fields both match your .env perfectly
    model_config = SettingsConfigDict(
        env_file=ENV_PATH, 
        env_file_encoding="utf-8",
        case_sensitive=False
    ) 
    
    DATABASE_HOSTNAME: str
    DATABASE_PORT: str
    POSTGRES_EXPOSE_PORT:str
    DATABASE_NAME: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str   
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    
    # Give gemini a default fallback or ensure its name matches your exact .env layout
    gemini_api_key: str = "placeholder_gemini_key"
    nvidia_api_key: str = "placeholder_nvidia_key"
    
settings = Settings()