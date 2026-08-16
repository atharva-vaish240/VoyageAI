from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    
    # Frontend callback used by Google Calendar OAuth & Google Sign-In redirect
    GOOGLE_REDIRECT_URI: str = (
        "https://voyageai-1zzx.onrender.com/auth/google/callback"
    )
    
    # Backend callback used by Google Login OAuth
    GOOGLE_BACKEND_CALLBACK: str = (
        "https://voyageai-backend-kovu.onrender.com/api/v1/oauth/google/callback"
    )
    # Gemini
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # Google Cloud API
    GOOGLE_API_KEY: str = ""

    # Pexels
    PEXELS_API_KEY: str = ""

    # OpenStreetMap / Nominatim
    NOMINATIM_BASE_URL: str = "https://nominatim.openstreetmap.org"
    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"

    # Redis Caching
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 345600  # Default 4 days in seconds (345600s) for itineraries / suggestions
    REDIS_RECOMMENDATION_CACHE_TTL: int = 345600  # Default 4 days in seconds (345600s) for recommendations

    # SMTP
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = "VoyageAI"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
