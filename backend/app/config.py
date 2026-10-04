from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_url: str
    mongodb_db: str = "resume_analyzer"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    admin_emails: str = ""
    cors_origins: str = "http://localhost:5173,https://ai-powered-resume-analyzer-job-matching-w4lw.onrender.com"

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    ai_api_key: str = ""
    ai_model_name: str = "gemini-3.5-flash-lite"

    # Upload limits (new)
    max_upload_mb: int = 5
    max_resumes_per_user: int = 10

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()