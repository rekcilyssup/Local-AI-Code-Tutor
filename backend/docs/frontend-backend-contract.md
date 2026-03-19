# Frontend-Backend Contract (Do Not Break)

This document defines the stable API interface for UI work.
Any external AI agent improving the frontend must follow this contract and must not change backend endpoint paths, payload shape, or SSE event format.

## Scope

- Backend: FastAPI app under `app/`
- Frontend: Streamlit app under `frontend/`
- API version: `v1`
- Base URL (local default): `http://127.0.0.1:8000`

## Stable Endpoints

### 1) Health Check

- Method: `GET`
- Path: `/api/v1/health`
- Response JSON:

```json
{
  "status": "ok"
}
```

### 2) Mentor Non-Streaming

- Method: `POST`
- Path: `/api/v1/mentor`
- Content-Type: `application/json`
- Request JSON schema:

```json
{
  "current_broken_code": "string, required, min length 1",
  "top_k": "integer, optional, default 2, allowed 1..10"
}
```

- Response JSON schema:

```json
{
  "response": "string"
}
```

### 3) Mentor Streaming (SSE)

- Method: `POST`
- Path: `/api/v1/mentor/stream`
- Content-Type (request): `application/json`
- Content-Type (response): `text/event-stream`
- Request JSON schema:

```json
{
  "current_broken_code": "string, required, min length 1",
  "top_k": "integer, optional, default 2, allowed 1..10"
}
```

## SSE Event Contract

The stream emits these events in order:

1. Repeating `token` events
2. One `metrics` event
3. One `done` event

If failure occurs, an `error` event may be emitted.

### token

```text
event: token
data: {"text":"..."}
```

### metrics

```text
event: metrics
data: {
  "time_to_first_token": 0.0,
  "generation_time": 0.0,
  "total_request_time": 0.0,
  "generated_characters": 0,
  "estimated_output_tokens": 0,
  "characters_per_second": 0.0,
  "estimated_tokens_per_second": 0.0
}
```

### done

```text
event: done
data: {"status":"completed"}
```

### error

```text
event: error
data: {"message":"..."}
```

## Non-Negotiable Compatibility Rules

External UI improvements must NOT:

- Rename or remove `/api/v1/mentor/stream`
- Rename or remove `/api/v1/mentor`
- Rename or remove `/api/v1/health`
- Change request field names: `current_broken_code`, `top_k`
- Change SSE event names: `token`, `metrics`, `done`, `error`
- Change SSE token field name `text`
- Change metrics key names

External UI improvements MAY:

- Change layout, styling, component architecture
- Add local frontend-only features (themes, saved prompts, rendering options)
- Add additional frontend telemetry, as long as request/response contract is unchanged

## Frontend Integration Notes

- For streaming UX, parse SSE frames by:
  - splitting by blank line
  - reading `event:` and `data:` lines
- `data:` payload is JSON text and should be parsed safely
- Append all `token.text` chunks in order to build final assistant output
- Handle `error` event gracefully in the UI

## Example Request Payload

```json
{
  "current_broken_code": "class Solution { ... }",
  "top_k": 2
}
```

## Quick Validation Commands

Run backend:

```bash
uvicorn app.main:app --reload
```

Sanity check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Source of Truth in Code

- API app wiring: `app/main.py`
- API router registration: `app/api/v1/api.py`
- Mentor endpoints: `app/api/v1/routes/mentor.py`
- Mentor request/response schema: `app/schemas/mentor.py`
- SSE event generation: `app/services/llm_stream_service.py`

If there is ever a mismatch between this doc and code, update this document immediately after code changes.
