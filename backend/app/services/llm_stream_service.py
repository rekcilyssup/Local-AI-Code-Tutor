import json
import logging
import time

from app.core.settings import get_settings
from app.services.local_llm_service import LocalLLMUnavailableError, stream_local_mentor_completion


logger = logging.getLogger(__name__)


def _format_sse(event: str, data: dict) -> str:
	payload = json.dumps(data, ensure_ascii=True)
	return f"event: {event}\ndata: {payload}\n\n"


def _build_sources_payload(matches):
	items = []
	for idx, match in enumerate(matches or [], start=1):
		meta = match.get("metadata") or {}
		items.append(
			{
				"index": idx,
				"title": meta.get("title", "Unknown"),
				"titleSlug": meta.get("titleSlug", "Unknown"),
				"lang": meta.get("lang", "Unknown"),
				"statusDisplay": meta.get("statusDisplay", "Unknown"),
				"timestamp": meta.get("timestamp", "Unknown"),
				"distance": match.get("distance"),
				"document": match.get("document", ""),
			}
		)
	return {"items": items}


def stream_mentor_tokens(prompt: str, mentor_model: str | None = None):
	"""Yield model tokens from local Ollama via OpenAI-compatible streaming API."""
	yield from stream_local_mentor_completion(prompt, mentor_model=mentor_model)


def stream_mentor_sse(prompt: str, matches=None, mentor_model: str | None = None):
	"""Yield Server-Sent Events for token streaming plus summary metrics."""
	settings = get_settings()
	active_model = mentor_model or settings.mentor_model
	request_started_at = time.perf_counter()
	first_token_at = None
	all_text_chunks = []

	try:
		if matches:
			yield _format_sse("sources", _build_sources_payload(matches))

		for token in stream_mentor_tokens(prompt, mentor_model=mentor_model):
			if first_token_at is None:
				first_token_at = time.perf_counter()
			all_text_chunks.append(token)
			yield _format_sse("token", {"text": token})

		finished_at = time.perf_counter()
		full_text = "".join(all_text_chunks)
		generated_chars = len(full_text)
		est_tokens = max(1, round(generated_chars / 4)) if generated_chars else 0
		total_time = max(0.0, finished_at - request_started_at)
		generation_time = max(0.0, finished_at - (first_token_at or finished_at))
		time_to_first_token = (first_token_at - request_started_at) if first_token_at else 0.0
		chars_per_sec = (generated_chars / generation_time) if generation_time > 0 else 0.0
		est_tokens_per_sec = (est_tokens / generation_time) if generation_time > 0 else 0.0

		yield _format_sse(
			"metrics",
			{
				"mentor_model": active_model,
				"time_to_first_token": round(time_to_first_token, 2),
				"generation_time": round(generation_time, 2),
				"total_request_time": round(total_time, 2),
				"generated_characters": generated_chars,
				"estimated_output_tokens": est_tokens,
				"characters_per_second": round(chars_per_sec, 2),
				"estimated_tokens_per_second": round(est_tokens_per_sec, 2),
			},
		)
		if settings.rag_debug:
			print(
				"[RAG] stream metrics "
				f"ttft={time_to_first_token:.2f}s "
				f"gen={generation_time:.2f}s "
				f"total={total_time:.2f}s "
				f"chars={generated_chars} "
				f"est_tps={est_tokens_per_sec:.2f}"
			)
		yield _format_sse("done", {"status": "completed"})
	except LocalLLMUnavailableError as exc:
		logger.exception("Local LLM unavailable")
		yield _format_sse("error", {"message": str(exc)})
	except Exception as exc:
		logger.exception("LLM streaming failed")
		yield _format_sse("error", {"message": str(exc)})
