from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vulture"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8787
    timezone: str = "America/New_York"
    log_level: str = "INFO"
    secret_key: str = "change-me"

    database_url: str = "sqlite:///./data/vulture.db"
    data_dir: Path = Path("./data")
    upload_dir: Path = Path("./data/uploads")
    resume_dir: Path = Path("./data/resumes")
    cover_letter_dir: Path = Path("./data/cover_letters")
    run_artifact_dir: Path = Path("./data/runs")

    browser_use_headless: bool = False
    browser_use_keep_browser_open: bool = False
    browser_use_max_steps: int = 200
    browser_use_nav_timeout_sec: int = 30
    browser_use_action_timeout_sec: int = 20
    browser_use_allowed_domains: str = ""
    browser_use_blocked_domains: str = ""
    browser_use_user_data_dir: Path = Path("./data/browser_profile")
    browser_use_channel: str = ""
    browser_use_executable_path: str = ""
    browser_use_profile_directory: str = ""

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model_planner: str = "gpt-5"
    openai_model_extractor: str = "gpt-5-mini"
    openai_model_writer: str = "gpt-5-mini"
    openai_timeout_sec: int = 60

    local_llm_enabled: bool = True
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_api_key: str = "local"
    local_llm_model: str = "qwen2.5:14b-instruct"
    local_llm_timeout_sec: int = 90

    llm_router_default: str = "hybrid"
    llm_router_plan_provider: str = "openai"
    llm_router_extract_provider: str = "openai"
    llm_router_db_patch_provider: str = "local"
    llm_router_writer_provider: str = "openai"

    default_run_mode: str = "medium"
    strict_approval_policy: str = "action"
    medium_approval_policy: str = "stage"
    yolo_approval_policy: str = "captcha_only"
    require_captcha_handoff: bool = True
    auto_submit_enabled: bool = True

    max_retries_per_field: int = 2
    max_retries_per_page: int = 2
    save_screenshots: bool = True
    save_dom_snapshots: bool = False

    pii_encryption_key: str = ""
    redact_log_pii: bool = True
    audit_retention_days: int = 365

    web_ui_enabled: bool = True
    api_auth_mode: str = "local_session"
    session_ttl_min: int = 720
    cors_origins: str = "http://127.0.0.1:8787"

    @field_validator("app_env")
    @classmethod
    def validate_env(cls, value: str) -> str:
        allowed = {"development", "staging", "production", "test"}
        if value not in allowed:
            raise ValueError(f"app_env must be one of {sorted(allowed)}")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
