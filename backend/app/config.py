from functools import lru_cache
import json
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongodb_url: str
    mongodb_db: str = "resume_analyzer"

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    admin_emails: str = ""
    initial_admin_email: str = "admin@gmail.com"
    initial_admin_password: str = "admin123"
    cors_origins: str = "http://localhost:5173,https://ai-powered-resume-analyzer-job-matching-w4lw.onrender.com,https://data-science-project-nine.vercel.app"

    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    ai_api_key: str = ""
    ai_model_name: str = "gemini-3.5-flash-lite"
    ai_pricing_version: str = "unconfigured"
    ai_model_rates_json: str = "{}"
    max_ai_parse_chars: int = 40_000

    # Upload limits (new)
    max_upload_mb: int = 5
    max_resumes_per_user: int = 10

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_email_set(self) -> set[str]:
        configured = {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}
        if self.initial_admin_email.strip():
            configured.add(self.initial_admin_email.strip().lower())
        return configured

    @property
    def ai_model_rates(self) -> dict[str, dict[str, float]]:
        """Rates in USD per one million tokens, keyed by exact model name."""
        try:
            rates = json.loads(self.ai_model_rates_json)
        except json.JSONDecodeError as exc:
            raise ValueError("AI_MODEL_RATES_JSON must be valid JSON.") from exc
        if not isinstance(rates, dict):
            raise ValueError("AI_MODEL_RATES_JSON must be a JSON object.")

        normalized = {}
        for model, rate in rates.items():
            if not isinstance(model, str) or not isinstance(rate, dict):
                raise ValueError("Each AI model rate must be an object keyed by model name.")
            try:
                input_rate = float(rate["input_usd_per_million_tokens"])
                output_rate = float(rate["output_usd_per_million_tokens"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "Each AI model rate needs input_usd_per_million_tokens and output_usd_per_million_tokens."
                ) from exc
            if input_rate < 0 or output_rate < 0:
                raise ValueError("AI model rates cannot be negative.")
            normalized[model] = {
                "input_usd_per_million_tokens": input_rate,
                "output_usd_per_million_tokens": output_rate,
            }
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
