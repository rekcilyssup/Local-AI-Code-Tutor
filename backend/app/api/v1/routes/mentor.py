from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.schemas.mentor import MentorResponse, MentorStreamRequest
from app.services.llm_stream_service import stream_mentor_sse, stream_mentor_tokens
from app.services.mentor_service import prepare_mentor_prompt


router = APIRouter(prefix="/mentor", tags=["mentor"])


@router.post("", response_model=MentorResponse)
def mentor_response(request: MentorStreamRequest):
	"""Non-streaming endpoint for simple clients and quick backend validation."""
	prompt, _matches = prepare_mentor_prompt(
		current_broken_code=request.current_broken_code,
		top_k=request.top_k,
		rag_source=request.rag_source,
	)
	text = "".join(stream_mentor_tokens(prompt, mentor_model=request.mentor_model))
	return MentorResponse(response=text)


@router.post("/stream")
def mentor_stream(request: MentorStreamRequest):
	"""SSE endpoint that streams mentor response tokens and completion metrics."""
	prompt, matches = prepare_mentor_prompt(
		current_broken_code=request.current_broken_code,
		top_k=request.top_k,
		rag_source=request.rag_source,
	)
	return StreamingResponse(
		stream_mentor_sse(prompt, matches=matches, mentor_model=request.mentor_model),
		media_type="text/event-stream",
	)
