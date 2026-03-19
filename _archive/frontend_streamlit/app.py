import json
import time

import requests
import streamlit as st


BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TOP_K = 2

st.set_page_config(
    page_title="AI Code Mentor",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="expanded",
)


def check_health():
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health", timeout=2)
        return response.status_code == 200 and response.json().get("status") == "ok"
    except requests.exceptions.RequestException:
        return False


def get_backend_info():
    try:
        response = requests.get(f"{BASE_URL}/", timeout=2)
        if response.status_code == 200:
            return response.json()
    except requests.exceptions.RequestException:
        pass
    return {}


def get_mentor_non_streaming(code: str):
    url = f"{BASE_URL}/api/v1/mentor"
    payload = {
        "current_broken_code": code,
        "top_k": DEFAULT_TOP_K,
    }
    response = requests.post(url, json=payload, timeout=120)
    response.raise_for_status()
    return response.json().get("response", "")


def stream_mentor_response(code: str):
    url = f"{BASE_URL}/api/v1/mentor/stream"
    payload = {
        "current_broken_code": code,
        "top_k": DEFAULT_TOP_K,
    }

    with requests.post(url, json=payload, stream=True, timeout=(10, 600)) as response:
        response.raise_for_status()
        event_type = None
        for line in response.iter_lines():
            if not line:
                continue
            decoded_line = line.decode("utf-8")
            if decoded_line.startswith("event:"):
                event_type = decoded_line.replace("event:", "").strip()
            elif decoded_line.startswith("data:"):
                data_str = decoded_line.replace("data:", "").strip()
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                if event_type == "token":
                    yield {"type": "token", "content": data.get("text", "")}
                elif event_type == "sources":
                    yield {"type": "sources", "content": data.get("items", [])}
                elif event_type == "metrics":
                    yield {"type": "metrics", "content": data}
                elif event_type == "error":
                    yield {"type": "error", "content": data.get("message", "Unknown error")}
                elif event_type == "done":
                    yield {"type": "done", "content": data.get("status")}
                    break


@st.dialog("🔍 RAG Database Context", width="large")
def show_context_modal(sources, metrics):
    if sources:
        st.subheader("Retrieved Code History")
        tabs = st.tabs([f"Source {i + 1} ({s.get('statusDisplay')})" for i, s in enumerate(sources)])

        for i, source in enumerate(sources):
            with tabs[i]:
                st.markdown(
                    f"**Title:** {source.get('title')} | "
                    f"**Distance:** `{float(source.get('distance', 0)):.2f}`"
                )
                st.code(source.get("document", ""), language=source.get("lang", "java"))

    if metrics:
        st.divider()
        st.subheader("⚡ Telemetry Metrics")
        st.json(metrics)


if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []


with st.sidebar:
    st.title("⚙️ Settings")
    is_online = check_health()
    backend_info = get_backend_info() if is_online else {}
    active_model = backend_info.get("mentor_model", "unknown")
    if is_online:
        st.success("Backend: Online", icon="🟢")
        st.caption(f"Active Model: {active_model}")
    else:
        st.error("Backend: Offline", icon="🔴")
        st.caption("Ensure backend is running on port 8000.")

    st.divider()
    st.caption("Model selection is controlled by backend config/terminal (MENTOR_MODEL).")
    use_streaming = st.toggle("Use Streaming (SSE)", value=True)

    if st.button("Clear Chat History", use_container_width=True, type="secondary"):
        st.session_state.chat_messages = []
        st.rerun()


st.title("🧠 AI Code Mentor")
st.caption("Model is controlled by backend runtime. Paste your code below.")

for idx, message in enumerate(st.session_state.chat_messages):
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            with st.expander("📄 View submitted code", expanded=False):
                st.code(message["code"], language="java")
        else:
            st.markdown(message["content"])
            if message.get("sources") or message.get("metrics"):
                if st.button("📊 View Sources & Metrics", key=f"btn_sources_{idx}"):
                    show_context_modal(message.get("sources"), message.get("metrics"))

if not is_online:
    st.chat_input("Backend offline. Start the FastAPI server first.", disabled=True)
elif user_code := st.chat_input("Paste your Java code here... (Shift+Enter for new line)"):
    st.session_state.chat_messages.append({"role": "user", "code": user_code})
    with st.chat_message("user"):
        with st.expander("📄 View submitted code", expanded=False):
            st.code(user_code, language="java")

    full_text = ""
    source_items = []
    metrics_data = None

    with st.chat_message("assistant"):
        if not use_streaming:
            with st.spinner("Analyzing your history..."):
                started = time.time()
                full_text = get_mentor_non_streaming(user_code)
                elapsed = round(time.time() - started, 2)
                metrics_data = {"total_request_time": elapsed, "mentor_model": active_model}
                st.markdown(full_text)
        else:
            response_placeholder = st.empty()
            try:
                for chunk in stream_mentor_response(user_code):
                    chunk_type = chunk["type"]
                    if chunk_type == "token":
                        full_text += chunk["content"]
                        response_placeholder.markdown(full_text + " ▌")
                    elif chunk_type == "sources":
                        source_items = chunk["content"] or []
                    elif chunk_type == "metrics":
                        metrics_data = chunk["content"]
                    elif chunk_type == "error":
                        st.error(f"Mentor Error: {chunk['content']}")
                    elif chunk_type == "done":
                        response_placeholder.markdown(full_text)
            except Exception as exc:
                st.error(f"Streaming failed: {exc}")

    st.session_state.chat_messages.append(
        {
            "role": "assistant",
            "content": full_text,
            "sources": source_items,
            "metrics": metrics_data,
            "mentor_model": active_model,
        }
    )
    st.rerun()
