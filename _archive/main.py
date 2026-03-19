import os  # Provides access to environment variables.
import json  # Handles JSON serialization/deserialization.
import requests  # Sends HTTP requests to the LeetCode API.
from pathlib import Path  # Provides filesystem path utilities.

import chromadb  # Official ChromaDB Python client.
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings  # Typing helpers for custom embedding functions.
from dotenv import load_dotenv  # Loads variables from a .env file.
from openai import OpenAI  # OpenAI-compatible client used with local Ollama /v1 endpoint.

# Load environment variables
load_dotenv()  # Read .env and add its values to process environment.

LEETCODE_SESSION = os.getenv("LEETCODE_SESSION")  # Auth cookie required by LeetCode.
LEETCODE_URL = "https://leetcode.com/graphql"  # LeetCode GraphQL endpoint.
OLLAMA_EMBEDDINGS_URL = "http://localhost:11434/api/embeddings"  # Primary Ollama embeddings endpoint.
OLLAMA_EMBED_FALLBACK_URL = "http://localhost:11434/api/embed"  # Fallback endpoint used by newer Ollama versions.
OLLAMA_OPENAI_BASE_URL = "http://localhost:11434/v1"  # OpenAI-compatible Ollama endpoint.


class OllamaEmbeddingFunction(EmbeddingFunction[Documents]):
    """Custom Chroma embedding function backed by a local Ollama model."""

    def __init__(self, model: str = "nomic-embed-text", timeout: int = 60):
        self.model = model  # Ollama embedding model name.
        self.timeout = timeout  # Request timeout for each embedding call.
        self.openai_client = OpenAI(base_url=OLLAMA_OPENAI_BASE_URL, api_key="ollama")  # Reusable OpenAI-compatible client.

    def __call__(self, input: Documents) -> Embeddings:
        embeddings: Embeddings = []  # Output list aligned with input text order.

        for text in input:
            # Try legacy endpoint first, then fallback to newer /api/embed endpoint.
            vector = self._embed_with_ollama(text)
            embeddings.append(vector)

        return embeddings

    def _embed_with_ollama(self, text: str):
        # Legacy Ollama endpoint: /api/embeddings with {prompt: text}.
        response = requests.post(
            OLLAMA_EMBEDDINGS_URL,
            json={"model": self.model, "prompt": text},
            timeout=self.timeout,
        )

        if response.status_code == 404:
            # Newer Ollama endpoint: /api/embed with {input: text}.
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
        # Final fallback for Ollama instances exposing only OpenAI-compatible /v1 APIs.
        response = self.openai_client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding


def load_submissions_from_json(file_path: str = "submissions.json"):
    """Load submissions from a JSON file on disk."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"{file_path} not found. Create it before ingestion.")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("submissions.json must contain a JSON array.")

    return data


def _extract_code_field(submission: dict):
    """Return the first non-empty code field from a submission record."""
    candidate_keys = ["code", "submissionCode", "source", "content"]

    for key in candidate_keys:
        value = submission.get(key)
        if isinstance(value, str) and value.strip():
            return value

    return None


def store_submission_code_in_chroma(
    json_file: str = "submissions.json",
    chroma_path: str = "./chroma_db",
    collection_name: str = "leetcode_submission_code",
):
    """Read submission code from JSON, embed with Ollama, and persist in ChromaDB."""
    submissions = load_submissions_from_json(json_file)

    client = chromadb.PersistentClient(path=chroma_path)  # Persistent local Chroma client.
    embedding_function = OllamaEmbeddingFunction(model="nomic-embed-text")  # Custom Ollama embeddings.
    collection = client.get_or_create_collection(
        name=collection_name,
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
        print("No code entries found in submissions.json. Expected keys like 'code' or 'submissionCode'.")
        return

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"Stored {len(ids)} code submissions in Chroma collection '{collection_name}'.")

def fetch_submissions():  # Fetch recent accepted submissions and save them locally.
    """Fetch recent accepted and failed submissions from LeetCode GraphQL API."""
    
    query = """  # GraphQL query requesting the submission fields we care about.
    query getSubmissions($offset: Int!, $limit: Int!, $filters: SubmissionFilterInput) {
        submissionList(offset: $offset, limit: $limit, filters: $filters) {
            submissions {
                id
                title
                titleSlug
                timestamp
                statusDisplay
                lang
                runtime
                memory
            }
        }
    }
    """
    
    variables = {  # Variables passed into the GraphQL query.
        "offset": 0,  # Start at the latest submission.
        "limit": 50,  # Maximum number of submissions to fetch.
        "filters": {  # Filter object for submissionList.
            "status": "ACCEPTED"  # Only include accepted submissions.
        }
    }
    
    headers = {  # HTTP headers required by LeetCode GraphQL API.
        "Content-Type": "application/json",  # Body is sent as JSON.
        "Cookie": f"LEETCODE_SESSION={LEETCODE_SESSION}"  # Session cookie for auth.
    }
    
    try:  # Handle networking/API errors cleanly.
        response = requests.post(  # Make a POST request to GraphQL endpoint.
            LEETCODE_URL,  # Target URL.
            json={"query": query, "variables": variables},  # GraphQL payload.
            headers=headers,  # Request headers with content type and auth cookie.
            timeout=10  # Stop waiting if no response within 10 seconds.
        )
        response.raise_for_status()  # Raise an error for non-2xx HTTP responses.
        
        data = response.json()  # Parse response body into a Python dictionary.
        
        if "errors" in data:  # Check if GraphQL returned application-level errors.
            print(f"GraphQL Error: {data['errors']}")  # Print API error details.
            return None  # Exit early when API reports errors.
        
        submissions = data.get("data", {}).get("submissionList", {}).get("submissions", [])  # Safely extract submissions list.
        
        # Save to file
        with open("submissions.json", "w") as f:  # Open output file in write mode.
            json.dump(submissions, f, indent=2)  # Write submissions as pretty JSON.
        
        print(f"Successfully saved {len(submissions)} submissions to submissions.json")  # Confirm save count.
        return submissions  # Return data so callers can reuse it.
        
    except requests.exceptions.RequestException as e:  # Catch request/network-related failures.
        print(f"Request failed: {e}")  # Print error message for debugging.
        return None  # Return None to signal failure.

if __name__ == "__main__":  # Run only when executed directly, not when imported.
    store_submission_code_in_chroma()  # Read submissions JSON, embed code, and store in persistent Chroma.