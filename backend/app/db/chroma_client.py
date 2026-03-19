from pathlib import Path

import chromadb

from app.core.settings import get_settings
from app.db.embedding import OllamaEmbeddingFunction


def get_persistent_client(chroma_path: str | Path | None = None):
	settings = get_settings()
	path = str(chroma_path or settings.chroma_path)
	return chromadb.PersistentClient(path=path)


def get_submission_collection(
	client=None,
	collection_name: str | None = None,
	embedding_function: OllamaEmbeddingFunction | None = None,
):
	settings = get_settings()
	active_client = client or get_persistent_client()
	active_collection_name = collection_name or settings.chroma_collection
	active_embedding_function = embedding_function or OllamaEmbeddingFunction(model=settings.embed_model)
	return active_client.get_or_create_collection(
		name=active_collection_name,
		embedding_function=active_embedding_function,
	)


def get_global_collection(
	client=None,
	collection_name: str | None = None,
	embedding_function: OllamaEmbeddingFunction | None = None,
):
	settings = get_settings()
	active_client = client or get_persistent_client()
	active_collection_name = collection_name or settings.chroma_global_collection
	active_embedding_function = embedding_function or OllamaEmbeddingFunction(model=settings.embed_model)
	return active_client.get_or_create_collection(
		name=active_collection_name,
		embedding_function=active_embedding_function,
	)
