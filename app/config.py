# app/config.py
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file before BaseSettings reads environment
# You can specify the path if it's not in the root relative to where you run python
# load_dotenv(dotenv_path=Path('.') / '.env')
# Or let BaseSettings find it automatically if it's in the right place
# by adding model_config below

class Settings(BaseSettings):
    # Define your environment variables here with types
    # BaseSettings will automatically read them from the environment or .env file
    GOOGLE_CLIENT_ID: str
    BACKEND_JWT_SECRET_KEY: str
    BACKEND_JWT_ALGORITHM: str = "HS256" # Default algorithm
    BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 # Default expiry
    FRONTEND_ORIGIN_URL: str = "http://localhost:5173" # Default origin

    # DB Settings
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str = "postgres"
    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    
    # If your .env file is in the project root where you run uvicorn:
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    # Use extra='ignore' to avoid errors if extra variables exist in .env

# Create a single instance of the settings to be imported elsewhere
settings = Settings()

_DB_DRIVER = "postgresql+asyncpg"
_encoded_user = quote_plus(settings.DB_USER)
_encoded_password = quote_plus(str(settings.DB_PASSWORD))
DATABASE_URL = (
    f"{_DB_DRIVER}://"
    f"{_encoded_user}:{_encoded_password}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}"
    f"/{settings.DB_NAME}"
)

# You can add a check here if needed, although BaseSettings validates types
# if not all([settings.GOOGLE_CLIENT_ID, settings.BACKEND_JWT_SECRET_KEY]):
#     raise ValueError("Missing required environment variables...")
