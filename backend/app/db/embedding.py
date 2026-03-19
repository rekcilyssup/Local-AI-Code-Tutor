from urllib.parse import urlparse

import requests
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI

from app.core.settings import get_settings


def _get_ollama_api_base_url(openai_base_url: str) -> str:
	"""Convert an OpenAI-compatible base URL to the native Ollama API base URL."""
	parsed = urlparse(openai_base_url)
	if not parsed.scheme or not parsed.netloc:
		raise ValueError("Invalid OLLAMA_BASE_URL. Expected format like http://localhost:11434/v1")
	return f"{parsed.scheme}://{parsed.netloc}"


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
	"""Custom Chroma embedding function backed by local Ollama embeddings APIs."""

	def __init__(self, model: str | None = None, timeout: int = 60, openai_base_url: str | None = None):
		settings = get_settings()
		self.model = model or settings.embed_model
		self.timeout = timeout
		self.openai_base_url = openai_base_url or settings.ollama_base_url
		self.ollama_api_base = _get_ollama_api_base_url(self.openai_base_url)
		self.openai_client = OpenAI(base_url=self.openai_base_url, api_key="ollama")

	def __call__(self, input: Documents) -> Embeddings:
		embeddings: Embeddings = []
		for text in input:
			embeddings.append(self._embed_with_ollama(text))
		return embeddings

	def _embed_with_ollama(self, text: str):
		response = requests.post(
			f"{self.ollama_api_base}/api/embeddings",
			json={"model": self.model, "prompt": text},
			timeout=self.timeout,
		)

		if response.status_code == 404:
			fallback_response = requests.post(
				f"{self.ollama_api_base}/api/embed",
				json={"model": self.model, "input": text},
				timeout=self.timeout,
			)
			if fallback_response.status_code == 404:
				return self._embed_with_openai_compatible(text)

			fallback_response.raise_for_status()
			fallback_data = fallback_response.json()
			fallback_vectors = fallback_data.get("embeddings") or []
			if not fallback_vectors:
				raise ValueError("Ollama /api/embed response missing 'embeddings'.")
			return fallback_vectors[0]

		response.raise_for_status()
		data = response.json()
		vector = data.get("embedding")
		if not vector:
			raise ValueError("Ollama /api/embeddings response missing 'embedding'.")
		return vector

	def _embed_with_openai_compatible(self, text: str):
		response = self.openai_client.embeddings.create(model=self.model, input=text)
		return response.data[0].embedding
