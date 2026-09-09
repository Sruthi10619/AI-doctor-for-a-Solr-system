import os
from typing import Literal
from pydantic import BaseModel, Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class ConfigBase(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore"
        )
except ImportError:
    class ConfigBase(BaseModel):
        pass


class Settings(ConfigBase):
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./solr_doctor.db")

    # LLM Settings
    llm_mode: str = os.getenv("LLM_MODE", "EXPLICIT_MOCK")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "15"))

    # Anomaly Detection Thresholds
    solr_qtime_warn_ms: float = float(os.getenv("SOLR_QTIME_WARN_MS", "1000.0"))
    solr_qtime_crit_ms: float = float(os.getenv("SOLR_QTIME_CRIT_MS", "5000.0"))
    solr_error_burst_count: int = int(os.getenv("SOLR_ERROR_BURST_COUNT", "3"))
    gc_pause_warn_ms: float = float(os.getenv("GC_PAUSE_WARN_MS", "1000.0"))
    gc_pause_crit_ms: float = float(os.getenv("GC_PAUSE_CRIT_MS", "3000.0"))
    heap_usage_warn_pct: float = float(os.getenv("HEAP_USAGE_WARN_PCT", "80.0"))
    heap_usage_crit_pct: float = float(os.getenv("HEAP_USAGE_CRIT_PCT", "92.0"))

    # Correlation Engine Settings
    correlation_window_seconds: int = int(os.getenv("CORRELATION_WINDOW_SECONDS", "90"))
    same_node_boost: bool = os.getenv("SAME_NODE_BOOST", "true").lower() in ("true", "1")
    topology_shard_correlation: bool = os.getenv("TOPOLOGY_SHARD_CORRELATION", "true").lower() in ("true", "1")


settings = Settings()
