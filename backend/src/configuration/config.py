from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[3] 
ENV_PATH = str(BASE_DIR / ".env") 

print(f"--- Alembic Debug: Looking for .env file at: {ENV_PATH} ---")

class Settings(BaseSettings):
    # specify the .env file to import all the environment variables and load them
    model_config = SettingsConfigDict(
    env_file=ENV_PATH, 
    env_file_encoding="utf-8",
    case_sensitive=False
    ) 

    # these are only access through .env but is secured and not hardcoded in our codebase, so we can keep them secret and not push them to github
    DATABASE_HOSTNAME: str
    DATABASE_PORT: str
    POSTGRES_EXPOSE_PORT:str
    DATABASE_NAME: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str
    PUBLIC_API_URL: str
    SECRET_KEY: str
    ALGORITHM: str   
    ACCESS_TOKEN_EXPIRE_MINUTES: int 
    
    # Give gemini a default fallback or ensure its name matches your exact .env layout
    gemini_api_key: str = "placeholder_gemini_key"
    nvidia_api_key: str = "placeholder_nvidia_key"

    # Comma-separated list of browser origins allowed to call this API.
    # Defaults cover local Vite dev servers, so development needs no .env entry.
    # A deployed frontend lives on a different origin (e.g. the Vercel domain)
    # and MUST be added here, or every browser request is blocked by CORS even
    # though the API itself is healthy and reachable.
    CORS_ORIGINS: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:3000, http://localhost:5173,[https://sushantsinghraut.com.np](https://sushantsinghraut.com.np),[https://www.sushantsinghraut.com.np](https://www.sushantsinghraut.com.np)"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS_ORIGINS split into the list form CORSMiddleware expects."""
        return [
            origin.strip()
            for origin in self.CORS_ORIGINS.split(",")
            if origin.strip()
        ]

settings = Settings()