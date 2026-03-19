from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	"""Application settings loaded from environment variables."""

	model_config = SettingsConfigDict(
		env_file=".env",
		env_file_encoding="utf-8",
		case_sensitive=False,
		extra="forbid",
	)

	app_env: str = Field(default="dev", alias="APP_ENV")
	api_host: str = Field(default="127.0.0.1", alias="API_HOST")
	api_port: int = Field(default=8000, alias="API_PORT")

	ollama_base_url: str = Field(default="http://localhost:11434/v1", alias="OLLAMA_BASE_URL")
	mentor_model: str = Field(default="llama3.1:8b", alias="MENTOR_MODEL")
	embed_model: str = Field(default="nomic-embed-text", alias="EMBED_MODEL")
	local_llm_timeout_seconds: int = Field(default=120, alias="LOCAL_LLM_TIMEOUT_SECONDS")
	local_llm_startup_check: bool = Field(default=True, alias="LOCAL_LLM_STARTUP_CHECK")

	chroma_path: Path = Field(default=Path("./data/chroma_db"), alias="CHROMA_PATH")
	chroma_collection: str = Field(default="leetcode_submission_code", alias="CHROMA_COLLECTION")
	chroma_global_collection: str = Field(default="global_leetcode_solutions", alias="CHROMA_GLOBAL_COLLECTION")
	rag_debug: bool = Field(default=True, alias="RAG_DEBUG")
	rag_log_code_preview_chars: int = Field(default=160, alias="RAG_LOG_CODE_PREVIEW_CHARS")

	streamlit_port: int = Field(default=8501, alias="STREAMLIT_PORT")

	@property
	def ollama_native_base_url(self) -> str:
		"""Return Ollama base URL without the OpenAI compatibility suffix."""
		parsed = urlparse(self.ollama_base_url)
		if not parsed.scheme or not parsed.netloc:
			raise ValueError("Invalid OLLAMA_BASE_URL. Expected format like http://localhost:11434/v1")
		return f"{parsed.scheme}://{parsed.netloc}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
	"""Return a cached settings instance for dependency injection."""
	return Settings()
