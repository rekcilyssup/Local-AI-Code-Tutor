import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router_v1
from app.core.settings import get_settings
from app.services.local_llm_service import ensure_mentor_model_available, probe_local_llm_runtime


logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
	settings = get_settings()
	app = FastAPI(
		title="LeetCode AI Mentor API",
		version="0.1.0",
		description="RAG backend for LeetCode mentoring with local Ollama streaming.",
	)
	
	app.add_middleware(
		CORSMiddleware,
		allow_origins=["*"],
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	if settings.local_llm_startup_check:
		status = probe_local_llm_runtime()
		if not status["reachable"]:
			logger.warning(
				"Local LLM runtime is unreachable at %s. Error: %s",
				settings.ollama_base_url,
				status["error"],
			)
		elif not ensure_mentor_model_available(settings.mentor_model):
			logger.warning(
				"Configured mentor model '%s' not found locally. Installed models: %s",
				settings.mentor_model,
				", ".join(status["models"]) if status["models"] else "none",
			)

	app.include_router(api_router_v1, prefix="/api/v1")

	@app.get("/", tags=["meta"])
	def root():
		return {
			"message": "LeetCode AI Mentor API is running.",
			"env": settings.app_env,
			"mentor_model": settings.mentor_model,
			"version": "0.1.0",
		}

	return app


app = create_app()
