import logging

from app.core.settings import get_settings
from app.db.chroma_client import get_submission_collection, get_global_collection


logger = logging.getLogger(__name__)


def _normalize_query_results(results):
	docs = (results.get("documents") or [[]])[0]
	metas = (results.get("metadatas") or [[]])[0]
	dists = (results.get("distances") or [[]])[0]

	matches = []
	for doc, meta, dist in zip(docs, metas, dists):
		matches.append(
			{
				"document": doc,
				"metadata": meta or {},
				"distance": dist,
			}
		)
	return matches


def retrieve_similar_submissions(current_broken_code: str, top_k: int = 2, rag_source: str = "personal"):
	"""Retrieve nearest neighbors for grounded mentoring from the specified source."""
	if rag_source == "global":
		collection = get_global_collection()
	else:
		collection = get_submission_collection()

	failed_results = collection.query(
		query_texts=[current_broken_code],
		n_results=1,
		where={"statusDisplay": {"$ne": "Accepted"}},
		include=["documents", "metadatas", "distances"],
	)

	accepted_results = collection.query(
		query_texts=[current_broken_code],
		n_results=1,
		where={"statusDisplay": "Accepted"},
		include=["documents", "metadatas", "distances"],
	)

	matches = []
	matches.extend(_normalize_query_results(failed_results))
	matches.extend(_normalize_query_results(accepted_results))
	return matches[:top_k]


def build_mentor_prompt(current_broken_code: str, matches):
	"""Build a mentor prompt grounded in retrieved historical submissions."""
	context_blocks = []
	for idx, match in enumerate(matches, start=1):
		metadata = match["metadata"]
		context_blocks.append(
			(
				f"Example {idx}\n"
				f"Title: {metadata.get('title', 'Unknown')}\n"
				f"Title Slug: {metadata.get('titleSlug', 'Unknown')}\n"
				f"Language: {metadata.get('lang', 'Unknown')}\n"
				f"Submission Status: {metadata.get('statusDisplay', 'Unknown')}\n"
				f"Timestamp: {metadata.get('timestamp', 'Unknown')}\n"
				f"Distance: {match['distance']}\n"
				f"Code:\n{match['document']}"
			)
		)

	retrieved_context = "\n\n".join(context_blocks) if context_blocks else "No similar submissions found."

	return (
		"You are a strict, elite Senior Java Engineer mentoring a junior developer. "
		"I am providing you with their current broken code, along with similar past submissions from a database. "
		"You are STRICTLY FORBIDDEN from writing the corrected Java code. "
		"\n\n"
		"### VALIDATION GATE\n"
		"First, look at the 'Current Broken Code'. If it is a greeting (like 'hello'), conversational text, "
		"or clearly not a programming logic attempt, you MUST abort and output EXACTLY this single sentence: "
		"' Please paste a valid code snippet for me to analyze.' Do not output anything else.\n\n"
		"### MENTORING FORMAT\n"
		"If the input IS valid code, you must output your response in EXACTLY this format:\n\n"
		"###  The Core Bug\n"
		"(Explain exactly which line or logic block in the 'Current Broken Code' is failing in 2 sentences max. Be direct.)\n\n"
		"###  The Conceptual Hint\n"
		"(Give a specific hint on how to fix it without writing the code.)\n\n"
		"###  History Context\n"
		"(Briefly mention how their current attempt compares to the 'Accepted' example provided in the context, if applicable.)\n\n"
		f"Context:\n{retrieved_context}\n\n"
		f"Current Broken Code:\n{current_broken_code}"
	)


def prepare_mentor_prompt(current_broken_code: str, top_k: int = 2, rag_source: str = "personal"):
	settings = get_settings()
	matches = retrieve_similar_submissions(current_broken_code=current_broken_code, top_k=top_k, rag_source=rag_source)
	if settings.rag_debug:
		code_preview = current_broken_code.strip().replace("\n", " ")[: settings.rag_log_code_preview_chars]
		print(f"[RAG] request top_k={top_k} code_preview={code_preview}")
		for index, match in enumerate(matches, start=1):
			meta = match.get("metadata", {})
			print(
				"[RAG] match "
				f"{index}: status={meta.get('statusDisplay', 'Unknown')} "
				f"title={meta.get('title', 'Unknown')} "
				f"lang={meta.get('lang', 'Unknown')} "
				f"distance={match.get('distance', 'Unknown')}"
			)

		if matches and not any((m.get("metadata") or {}).get("statusDisplay") == "Accepted" for m in matches):
			logger.warning("RAG grounding warning: no Accepted submission found in retrieved context")
		if not matches:
			logger.warning("RAG grounding warning: no retrieval matches returned")

	prompt = build_mentor_prompt(current_broken_code=current_broken_code, matches=matches)
	return prompt, matches
