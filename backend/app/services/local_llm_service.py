import logging
from typing import Any

import requests
from openai import OpenAI

from app.core.settings import get_settings


logger = logging.getLogger(__name__)


class LocalLLMUnavailableError(RuntimeError):
	"""Raised when the local LLM backend cannot be reached or queried."""


def get_local_llm_client() -> OpenAI:
	"""Return an OpenAI-compatible client pointed at the local Ollama runtime."""
	settings = get_settings()
	return OpenAI(base_url=settings.ollama_base_url, api_key="ollama", timeout=settings.local_llm_timeout_seconds)


def probe_local_llm_runtime() -> dict[str, Any]:
	"""Check if local Ollama runtime is reachable and list installed model tags."""
	settings = get_settings()
	try:
		response = requests.get(
			f"{settings.ollama_native_base_url}/api/tags",
			timeout=min(settings.local_llm_timeout_seconds, 10),
		)
		response.raise_for_status()
		payload = response.json()
		models = [model.get("name") for model in payload.get("models", []) if model.get("name")]
		return {
			"reachable": True,
			"models": models,
			"error": None,
		}
	except Exception as exc:
		return {
			"reachable": False,
			"models": [],
			"error": str(exc),
		}


def ensure_mentor_model_available(model_name: str | None = None) -> bool:
	"""Return True when the configured mentor model is available locally."""
	settings = get_settings()
	active_model = model_name or settings.mentor_model
	status = probe_local_llm_runtime()
	if not status["reachable"]:
		return False
	return active_model in status["models"]


def stream_local_mentor_completion(prompt: str, mentor_model: str | None = None):
	"""Yield text deltas for a local chat completion request."""
	settings = get_settings()
	client = get_local_llm_client()
	active_model = mentor_model or settings.mentor_model

	try:
		stream = client.chat.completions.create(
			model=active_model,
			messages=[
				{"role": "system", "content": "You are a helpful AI coding mentor."},
				{"role": "user", "content": prompt},
			],
			stream=True,
		)
	except Exception as exc:
		raise LocalLLMUnavailableError(
			"Could not connect to local LLM runtime. Ensure Ollama is running and the model is pulled."
		) from exc

	for chunk in stream:
		delta = chunk.choices[0].delta.content if chunk.choices else None
		if delta:
			yield delta
