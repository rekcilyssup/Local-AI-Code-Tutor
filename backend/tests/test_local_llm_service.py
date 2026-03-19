from app.services import local_llm_service


def test_probe_local_llm_runtime_unreachable(monkeypatch):
	def fake_get(*args, **kwargs):
		raise RuntimeError("connection refused")

	monkeypatch.setattr(local_llm_service.requests, "get", fake_get)
	status = local_llm_service.probe_local_llm_runtime()

	assert status["reachable"] is False
	assert status["models"] == []
	assert "connection refused" in status["error"]


def test_ensure_mentor_model_available_true(monkeypatch):
	def fake_probe():
		return {"reachable": True, "models": ["llama3.1:8b"], "error": None}

	monkeypatch.setattr(local_llm_service, "probe_local_llm_runtime", fake_probe)
	assert local_llm_service.ensure_mentor_model_available("llama3.1:8b") is True


def test_ensure_mentor_model_available_false_when_missing(monkeypatch):
	def fake_probe():
		return {"reachable": True, "models": ["mistral:7b"], "error": None}

	monkeypatch.setattr(local_llm_service, "probe_local_llm_runtime", fake_probe)
	assert local_llm_service.ensure_mentor_model_available("llama3.1:8b") is False


def test_ensure_mentor_model_available_false_when_unreachable(monkeypatch):
	def fake_probe():
		return {"reachable": False, "models": [], "error": "offline"}

	monkeypatch.setattr(local_llm_service, "probe_local_llm_runtime", fake_probe)
	assert local_llm_service.ensure_mentor_model_available("llama3.1:8b") is False
