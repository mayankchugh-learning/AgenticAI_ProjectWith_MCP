"""Tests for the local/cloud toggle, the local RAG pipeline and the agent middleware.

Everything runs offline: embeddings and the chat model are replaced by fakes.
"""
import pytest
from fastapi.testclient import TestClient
from langchain.agents import create_agent
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from agent.middleware import build_agent_middleware
from api.main import app
from config.settings import Settings, settings
from exceptions import ConfigurationError
from rag import retrieval, vector_store
from rag.data_ingestion import ingest_pdf, ingest_stored_pdfs

client = TestClient(app)


class FakeToolModel(GenericFakeChatModel):
    """A scripted chat model that 'supports' tools, so create_agent accepts it."""

    def bind_tools(self, tools, **kwargs):
        return self


# ---------------------------------------------------------------------------
# The toggle
# ---------------------------------------------------------------------------

def test_default_mode_is_local(monkeypatch):
    monkeypatch.delenv("APP_MODE", raising=False)
    assert Settings(_env_file=None).app_mode == "local"


def test_invalid_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("APP_MODE", "hybrid")
    with pytest.raises(ValueError):
        Settings(_env_file=None)


def test_cloud_mode_lists_missing_settings(monkeypatch):
    monkeypatch.setattr(settings, "app_mode", "cloud")
    vector_store.get_vector_store.cache_clear()
    try:
        with pytest.raises(ConfigurationError, match="VECTOR_SEARCH_INDEX_ID"):
            vector_store.get_vector_store()
    finally:
        vector_store.get_vector_store.cache_clear()


def test_missing_api_key_gives_503_not_500(monkeypatch):
    from rag import llm

    monkeypatch.setattr(settings, "GOOGLE_API_KEY", "")
    llm.get_llm.cache_clear()
    try:
        res = client.post("/api/rag/ask", json={"query": "hi"})
        assert res.status_code == 503
        assert "GOOGLE_API_KEY" in res.json()["detail"]
    finally:
        llm.get_llm.cache_clear()


def test_health_and_status_report_local_mode():
    assert client.get("/api/health").json() == {"status": "ok", "mode": "local"}
    status = client.get("/api/status").json()
    assert status["mode"] == "local"
    assert status["vector_search"]["backend"].startswith("Chroma")
    assert status["models"]["embedding"] == settings.local_embedding_model_name


def test_cloud_mode_rag_call_gives_503_naming_variables_but_no_secrets(monkeypatch):
    """APP_MODE=cloud with empty cloud settings: a clear 503, never a 500 and never a secret."""
    from rag import embeddings

    monkeypatch.setattr(settings, "app_mode", "cloud")
    monkeypatch.setattr(settings, "GCP_PROJECT", "")
    monkeypatch.setattr(settings, "GCS_BUCKET_NAME", "")
    monkeypatch.setattr(settings, "vector_search_index_id", "")
    monkeypatch.setattr(settings, "vector_search_index_endpoint_id", "")
    for cached in (vector_store.get_vector_store, embeddings.get_embeddings):
        cached.cache_clear()
    try:
        res = client.post("/api/rag/ask", json={"query": "hi"})
        assert res.status_code == 503
        detail = res.json()["detail"]
        for name in ("GCP_PROJECT_ID", "GCS_BUCKET_NAME", "VECTOR_SEARCH_INDEX_ID", "VECTOR_SEARCH_INDEX_ENDPOINT_ID"):
            assert name in detail
        assert settings.GOOGLE_API_KEY not in detail  # names only, never values
    finally:
        for cached in (vector_store.get_vector_store, embeddings.get_embeddings):
            cached.cache_clear()


# ---------------------------------------------------------------------------
# Local RAG end to end: PDF -> Chroma -> retrieval -> answer
# ---------------------------------------------------------------------------

@pytest.fixture
def offline_local_store(monkeypatch):
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: DeterministicFakeEmbedding(size=768))
    vector_store.get_vector_store.cache_clear()
    yield vector_store.get_vector_store()
    vector_store.get_vector_store.cache_clear()


def test_local_ingest_and_ask(offline_local_store, monkeypatch, tmp_path):
    import glob
    import os
    import shutil

    pdf = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "sample_docs", "*.pdf")))[0]
    summary = ingest_pdf(pdf, "doc://sample.pdf")
    assert summary["chunks"] > 0

    # Re-ingesting the same file must not duplicate chunks (stable IDs)
    before = offline_local_store._collection.count()
    ingest_pdf(pdf, "doc://sample.pdf")
    assert offline_local_store._collection.count() == before

    # The "Index stored documents" button reads from the local upload folder
    os.makedirs(settings.local_upload_dir, exist_ok=True)
    shutil.copy(pdf, settings.local_upload_dir)
    assert ingest_stored_pdfs()["files"] == 1

    fake_llm = GenericFakeChatModel(messages=iter([AIMessage(content="EUR 2.84 billion")]))
    monkeypatch.setattr(retrieval, "get_llm", lambda: fake_llm)
    assert retrieval.ask_question("What is the revenue?") == "EUR 2.84 billion"


def test_upload_then_index_stored_documents_does_not_duplicate(monkeypatch, tmp_path):
    """Regression: uploading a PDF and then clicking "Index stored documents" indexed it twice.

    Upload used the source `upload://<file>`, the stored-file scan used `local://<file>`, and the
    chunk ID includes the source, so the same PDF got two sets of chunks. Both paths must now use
    the one key from document_store.source_key().
    """
    import glob
    import os

    # Isolated data dir and a fresh Chroma store, so other tests' files do not count
    monkeypatch.setattr(settings, "local_data_dir", str(tmp_path))
    monkeypatch.setattr(vector_store, "get_embeddings", lambda: DeterministicFakeEmbedding(size=768))
    vector_store.get_vector_store.cache_clear()
    try:
        pdf = sorted(glob.glob(os.path.join(os.path.dirname(__file__), "..", "..", "sample_docs", "*.pdf")))[0]
        with open(pdf, "rb") as f:
            res = client.post("/api/rag/upload", files={"files": (os.path.basename(pdf), f, "application/pdf")})
        assert res.status_code == 200
        assert res.json()["results"][0]["status"] == "ingested"

        store = vector_store.get_vector_store()
        after_upload = store._collection.count()
        assert after_upload > 0

        totals = ingest_stored_pdfs()
        assert totals["files"] == 1  # the copy kept by the upload
        assert store._collection.count() == after_upload

        sources = {m["source"] for m in store._collection.get(include=["metadatas"])["metadatas"]}
        assert len(sources) == 1
    finally:
        vector_store.get_vector_store.cache_clear()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def test_middleware_stack_has_the_expected_layers():
    names = [type(m).__name__ for m in build_agent_middleware()]
    for expected in ["PIIMiddleware", "ModelCallLimitMiddleware", "ToolCallLimitMiddleware",
                     "ModelRetryMiddleware", "ToolRetryMiddleware"]:
        assert expected in names


def test_agent_runs_tools_through_middleware_and_redacts_email():
    calls = []

    @tool
    def lookup_vendor(vendor_name: str) -> str:
        """Look a vendor up."""
        calls.append(vendor_name)
        return "CLEARED"

    model = FakeToolModel(messages=iter([
        AIMessage(content="", tool_calls=[{"name": "lookup_vendor", "args": {"vendor_name": "Takumi"}, "id": "1"}]),
        AIMessage(content="SANCTIONS CHECK: CLEARED"),
    ]))
    agent = create_agent(model=model, tools=[lookup_vendor], middleware=build_agent_middleware())
    result = agent.invoke({"messages": [HumanMessage("Screen Takumi, contact buyer@aldermoor.example")]})

    assert calls == ["Takumi"]
    assert result["messages"][-1].text == "SANCTIONS CHECK: CLEARED"
    assert "buyer@aldermoor.example" not in result["messages"][0].text


def test_supervisor_builds_three_agents_with_middleware():
    from agent.agents import ProcurementSupervisor

    supervisor = ProcurementSupervisor()  # no network call happens at build time
    assert supervisor.risk_agent and supervisor.tax_agent and supervisor.control_agent
