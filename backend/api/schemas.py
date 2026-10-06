from pydantic import BaseModel


# ============================================================
# AGENT  Schemas
# ============================================================



# Models use comments instead of docstrings on purpose: a docstring on a Pydantic model
# becomes part of the generated API schema (/docs, /openapi.json).

# Body of POST /api/agent/audit. `request_text` is free text with no length limit.
class AuditRequest(BaseModel):
    request_text: str

# Reply of POST /api/agent/audit. The four fields match the keys returned by
# ProcurementSupervisor.run_audit() in agent/agents.py.
class AuditResponse(BaseModel):
    risk_result: str
    tax_result: str
    control_result: str
    cfo_memo: str


# ============================================================
# RAG  Schemas
# ============================================================


# Body of POST /api/rag/ask. `retriever_type` is plain text: "similarity" (default),
# "multiquery" or "contextual". Any other value falls back to "similarity" (rag/retrieval.py).
class QueryRequest(BaseModel):
    query: str
    retriever_type: str = "similarity"

# Reply of POST /api/rag/ask: the model's answer text only. The source passages are not returned.
class QueryResponse(BaseModel):
    answer: str