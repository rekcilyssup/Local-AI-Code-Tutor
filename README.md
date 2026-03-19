# LeetMentor (Local AI RAG)

LeetMentor is a privacy-first, local AI coding assistant that uses Retrieval-Augmented Generation (RAG) to provide grounded hints and mentorship based on actual successful and failed LeetCode submissions. 

It completely decouples from cloud APIs by running **Ollama** locally for both text generation (e.g., `llama3.1:8b`) and text embeddings (`nomic-embed-text`), utilizing **ChromaDB** for blazing-fast vector storage.

## ✨ Features
- **Dual-RAG Memory**: Instantly toggle your AI's brain between your own personal LeetCode submission history and a massive Global Dataset of thousands of highly-upvoted Python solutions.
- **Sleek React Frontend**: A premium, dark-mode (Vercel/Linear-inspired) UI built with React, TypeScript, and Vite.
- **Real-Time Streaming**: Tokens stream directly from the local LLM to the UI without blocking, utilizing Server-Sent Events (SSE).
- **Context Inspection**: A polished sliding right-panel allows you to natively inspect the exact retrieved vectors (the "sources") and telemetry metrics that the LLM used to formulate your hint.

## 🏗 Architecture
- **Backend (`/backend`)**: FastAPI, Python 3.12, Uvicorn, ChromaDB, Ollama.
- **Frontend (`/frontend`)**: React 18, TypeScript, Vite, `lucide-react`, `react-markdown`.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- Node.js & npm
- [Ollama](https://ollama.ai/) installed and running locally with the following models pulled:
  ```bash
  ollama pull llama3.1:8b
  ollama pull nomic-embed-text
  ```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Optional: tune any environment variables
```

### 3. Populating the Vector Database
You can evaluate your code against your own submissions or use a massive global parquet dataset.
```bash
# In the /backend directory (with venv activated)
python -m scripts.ingest_submissions  # Ingests your personal submissions.json
python -m scripts.ingest_global       # Ingests the global HuggingFace/Kaggle dataset
```

### 4. Running the Development Servers
**Terminal 1 (Backend):**
```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm install
npm run dev
```

The React interactive UI will be immediately available at `http://localhost:5173`.

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
