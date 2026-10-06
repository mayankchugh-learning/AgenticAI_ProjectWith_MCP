"""Application settings, read from environment variables and an optional `.env` file.

Every other backend module imports the single `settings` object created at the bottom
of this file. Nothing here is validated at startup: unset values stay empty strings and
only fail later, when a feature that needs them is first used.
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
# from logger import GLOBAL_LOGGER as log
# (The import above stays commented out: logger/custom_logger.py imports `settings`, so enabling it would create a circular import.)

class Settings(BaseSettings):
    """All configuration values.

    `validation_alias` is the environment variable name, which is not always the same as
    the attribute name (for example GCP_PROJECT_ID is read into `GCP_PROJECT`).
    """

    # App
    app_name: str = "Meridian AI - Procurement Intelligence"
    # ENVIRONMENT is read here, but no backend code uses `app_env` or `debug`.
    app_env: str = Field("", validation_alias="ENVIRONMENT")
    app_version: str = "1.0.0"
    debug: bool = True

    # GCP (GOOGLE_API_KEY is the Gemini API key used by rag/llm.py, not a Google Cloud credential)
    GOOGLE_API_KEY: str = Field("", validation_alias="GOOGLE_API_KEY")
    GCP_PROJECT: str = Field("", validation_alias="GCP_PROJECT_ID")
    GCP_REGION: str = Field("", validation_alias="GCP_REGION")
    GCS_BUCKET_NAME: str = Field("", validation_alias="GCS_BUCKET_NAME")
    GCS_PREFIX: str = Field("", validation_alias="GCS_PREFIX")
    gcp_service_account_path: str = Field("", validation_alias="GCP_SERVICE_ACCOUNT_PATH")

    # Model / RAG
    llm_model_name: str = Field("gemini-3.8-flash", validation_alias="VERTEX_LLM_MODEL_NAME")
    # 0 = most repeatable answers. If the model loops or repeats itself, try 1.0 (Gemini 3 default)
    llm_temperature: float = Field(0.0, validation_alias="LLM_TEMPERATURE")
    # Must output 768 dimensions to match the Vector Search index (see rag/embeddings.py)
    embedding_model_name: str = Field("text-embedding-005", validation_alias="VERTEX_EMBEDDING_MODEL_NAME")
    # VERTEX AI VECTOR SEARCH
    vector_search_index_id: str = Field("", validation_alias="VECTOR_SEARCH_INDEX_ID")
    vector_search_index_endpoint_id: str = Field("", validation_alias="VECTOR_SEARCH_INDEX_ENDPOINT_ID")

    # `.env` is a relative path, so it is looked up in the directory the app is started from.
    # Unknown variables in the file are ignored (extra="ignore").
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Shared instance imported by the rest of the backend (created once, when this module is first imported).
settings = Settings()



# Post-initialization: Set GOOGLE_APPLICATION_CREDENTIALS if path is provided
# (Google client libraries read that variable. A path that does not exist is silently ignored.)
if settings.gcp_service_account_path:
    # Try to resolve relative to project root (where .env usually is)
    # This is rough but helpful for local dev
    abs_path = os.path.abspath(settings.gcp_service_account_path)
    if os.path.exists(abs_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_path
        # log.info("Google Application Credentials set", path=abs_path)
    else:
        # Try relative to the current working directory if absolute didn't exist
        # log.warning("Service account file not found", path=abs_path)
        pass
