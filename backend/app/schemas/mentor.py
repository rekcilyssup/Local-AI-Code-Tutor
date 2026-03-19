from pydantic import BaseModel, Field


class MentorStreamRequest(BaseModel):
	current_broken_code: str = Field(..., min_length=1, description="User's current broken code.")
	top_k: int = Field(default=2, ge=1, le=10, description="Number of retrieval matches to include.")
	mentor_model: str | None = Field(default=None, description="Optional Ollama model override for this request.")
	rag_source: str = Field(default="personal", description="Source of RAG context: personal or global.")


class MentorResponse(BaseModel):
	response: str
