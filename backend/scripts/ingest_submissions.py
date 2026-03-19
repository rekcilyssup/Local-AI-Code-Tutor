import argparse
import json
from pathlib import Path

from app.db.chroma_client import get_persistent_client, get_submission_collection
from app.db.embedding import OllamaEmbeddingFunction


def load_submissions_from_json(file_path: str = "submissions.json"):
	"""Load submissions from a JSON file on disk."""
	path = Path(file_path)
	if not path.exists():
		raise FileNotFoundError(f"{file_path} not found. Create it before ingestion.")

	with path.open("r", encoding="utf-8") as file_handle:
		data = json.load(file_handle)

	if not isinstance(data, list):
		raise ValueError("submissions.json must contain a JSON array.")

	return data


def _extract_code_field(submission: dict):
	"""Return the first non-empty code field from a submission record."""
	for key in ["code", "submissionCode", "source", "content"]:
		value = submission.get(key)
		if isinstance(value, str) and value.strip():
			return value
	return None


def store_submission_code_in_chroma(
	json_file: str = "submissions.json",
	chroma_path: str | None = None,
	collection_name: str | None = None,
	embed_model: str | None = None,
):
	"""Read submission code from JSON, embed with Ollama, and persist in ChromaDB."""
	submissions = load_submissions_from_json(json_file)

	client = get_persistent_client(chroma_path=chroma_path)
	embedding_function = OllamaEmbeddingFunction(model=embed_model)
	collection = get_submission_collection(
		client=client,
		collection_name=collection_name,
		embedding_function=embedding_function,
	)

	ids = []
	documents = []
	metadatas = []

	for index, submission in enumerate(submissions):
		if not isinstance(submission, dict):
			continue

		code = _extract_code_field(submission)
		if not code:
			continue

		submission_id = str(submission.get("id") or f"submission-{index}")
		ids.append(submission_id)
		documents.append(code)
		metadatas.append(
			{
				"title": str(submission.get("title", "")),
				"titleSlug": str(submission.get("titleSlug", "")),
				"lang": str(submission.get("lang", "")),
				"statusDisplay": str(submission.get("statusDisplay", "")),
				"timestamp": str(submission.get("timestamp", "")),
			}
		)

	if not ids:
		print("No code entries found in submissions JSON. Expected keys like 'code' or 'submissionCode'.")
		return 0

	collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
	print(f"Stored {len(ids)} code submissions in Chroma collection '{collection.name}'.")
	return len(ids)


def main():
	parser = argparse.ArgumentParser(description="Ingest LeetCode submissions into ChromaDB.")
	parser.add_argument("--json-file", default="submissions.json", help="Path to scraped submissions JSON")
	parser.add_argument("--chroma-path", default=None, help="Override Chroma persistence path")
	parser.add_argument("--collection", default=None, help="Override Chroma collection name")
	parser.add_argument("--embed-model", default=None, help="Override embedding model name")
	args = parser.parse_args()

	store_submission_code_in_chroma(
		json_file=args.json_file,
		chroma_path=args.chroma_path,
		collection_name=args.collection,
		embed_model=args.embed_model,
	)


if __name__ == "__main__":
	main()
