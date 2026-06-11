from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[3] #this gets the path to the root folder (Handy_Man). This moves up 3 levels from config.py to hit .env
# config.py -> configuration -> src -> backend-> root

ENV_PATH = str(BASE_DIR / ".env") # this stores the path to the .env file in a variable so we can use it in our Settings class

print(f"--- Alembic Debug: Looking for .env file at: {ENV_PATH} ---")
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH) # specify the .env file to import all the environment variables and load them
    
    # these are only access through .env but is secured and not hardcoded in our codebase, so we can keep them secret and not push them to github
    DATABASE_HOSTNAME: str
    DATABASE_PORT: str
    DATABASE_NAME: str
    DATABASE_USERNAME: str
    DATABASE_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str   # this is the algorithm used to sign our JWT tokens, HS256 is a common choice for symmetric signing
    ACCESS_TOKEN_EXPIRE_MINUTES: int # this is the number of minutes that our access tokens will be valid for, after that they will expire and the user will need to log in again to get a new token
    gemini_api_key: str
    
    
settings = Settings() # creates an instance of the Settings class, which will read the environment variables from the .env file and make them available when ever needed 

