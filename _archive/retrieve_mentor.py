import requests
import chromadb
import time
import os
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from openai import OpenAI


CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "leetcode_submission_code"
OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/api/embeddings"
OLLAMA_EMBED_FALLBACK_URL = "http://localhost:11434/api/embed"
OLLAMA_OPENAI_BASE_URL = "http://localhost:11434/v1"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
MENTOR_MODEL = os.getenv("MENTOR_MODEL", "llama3.1:8b")


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """Chroma embedding function that calls local Ollama embeddings API."""

    def __init__(self, model: str = OLLAMA_EMBED_MODEL, timeout: int = 60):
        self.model = model
        self.timeout = timeout
        self.openai_client = OpenAI(base_url=OLLAMA_OPENAI_BASE_URL, api_key="ollama")

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []

        for text in input:
            vector = self._embed_with_ollama(text)
            embeddings.append(vector)

        return embeddings

    def _embed_with_ollama(self, text: str):
        response = requests.post(
            OLLAMA_EMBEDDINGS_URL,
            json={"model": self.model, "prompt": text},
            timeout=self.timeout,
        )

        if response.status_code == 404:
            fallback_response = requests.post(
                OLLAMA_EMBED_FALLBACK_URL,
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
        response = self.openai_client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding


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


def retrieve_similar_submissions(current_broken_code: str, top_k: int = 2):
    """Query ChromaDB for both failed and accepted examples to anchor mentor comparisons."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=OllamaEmbeddingFunction(),
    )

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

    top_matches = []
    top_matches.extend(_normalize_query_results(failed_results))
    top_matches.extend(_normalize_query_results(accepted_results))

    return top_matches[:top_k]


def build_mentor_prompt(current_broken_code: str, matches):
    """Build prompt for the AI mentor using retrieved similar submissions."""
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
        "You are a strict technical interviewer. Point out bottlenecks and likely bug patterns. "
        "Use the Submission Status field to contrast failed attempts (e.g., TLE/Wrong Answer) against Accepted ones. "
        "You are STRICTLY FORBIDDEN from writing any Python code. Provide only a conceptual hint.\n\n"
        f"Current broken code:\n{current_broken_code}\n\n"
        f"Retrieved similar past submissions:\n{retrieved_context}\n"
    )


def stream_mentor_response(prompt: str):
    """Stream mentor response from local Ollama via OpenAI-compatible API."""
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
    print(f"--- Mentor Model: {MENTOR_MODEL} ---")

    request_started_at = time.perf_counter()
    stream = client.chat.completions.create(
        model=MENTOR_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful AI coding mentor."},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )

    print("--- AI Mentor Response ---")
    first_token_at = None
    all_text_chunks = []

    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            if first_token_at is None:
                first_token_at = time.perf_counter()
            all_text_chunks.append(delta)
            print(delta, end="", flush=True)

    finished_at = time.perf_counter()
    full_text = "".join(all_text_chunks)
    generated_chars = len(full_text)
    # Rough token estimate for local dev metrics (LLM tokenizers vary by model).
    est_tokens = max(1, round(generated_chars / 4)) if generated_chars else 0
    total_time = max(0.0, finished_at - request_started_at)
    generation_time = max(0.0, finished_at - (first_token_at or finished_at))
    time_to_first_token = (first_token_at - request_started_at) if first_token_at else 0.0
    chars_per_sec = (generated_chars / generation_time) if generation_time > 0 else 0.0
    est_tokens_per_sec = (est_tokens / generation_time) if generation_time > 0 else 0.0

    print("\n")
    print("--- Streaming Metrics (Dev Estimate) ---")
    print(f"Time to first token: {time_to_first_token:.2f}s")
    print(f"Generation time: {generation_time:.2f}s")
    print(f"Total request time: {total_time:.2f}s")
    print(f"Generated characters: {generated_chars}")
    print(f"Estimated output tokens: {est_tokens}")
    print(f"Characters/sec: {chars_per_sec:.2f}")
    print(f"Estimated tokens/sec: {est_tokens_per_sec:.2f}")


def main():
    # Hardcoded input per requirement.
    current_broken_code = """class Solution {
    public boolean uniqueOccurrences(int[] arr) {
        HashMap<Integer, Integer> map = new HashMap<>();
        for (int i : arr) {
            if (map.containsKey(i)) {
                map.put(i, map.get(i) + 1);
            } else {
                map.put(i, 1);
            }
        }

        HashSet<Integer> set = new HashSet<>();
        for (int i : map.keySet()) {
            if (set.contains(map.get(i))) {
                return false;
            }
            set.add(map.get(i));
        }

        // Deliberate bug: should return true when all counts are unique.
        return false;
    }
}"""

    matches = retrieve_similar_submissions(current_broken_code=current_broken_code, top_k=2)

    print("--- Retrieved Similar Submissions ---")
    if not matches:
        print("No similar submissions were found in ChromaDB.")
    else:
        for i, match in enumerate(matches, start=1):
            metadata = match["metadata"]
            title = metadata.get("title", "Unknown")
            lang = metadata.get("lang", "Unknown")
            status = metadata.get("statusDisplay", "Unknown")
            print(f"{i}. {title} [{lang}] status={status} (distance={match['distance']})")

    prompt = build_mentor_prompt(current_broken_code=current_broken_code, matches=matches)
    stream_mentor_response(prompt)


if __name__ == "__main__":
    main()