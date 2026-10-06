"""Text -> vector conversion, used both when indexing documents and when searching.

IMPORTANT: the Vector Search index is created with 768 dimensions (see
.github/workflows/deploy.yml). The embedding model must produce 768-dimensional
vectors, and the SAME model must be used for indexing and for querying.
text-embedding-005 produces 768 dimensions.
"""
from functools import lru_cache

from langchain_google_vertexai import VertexAIEmbeddings

from config.settings import settings


@lru_cache(maxsize=1)
def get_embeddings() -> VertexAIEmbeddings:
    """Return the Vertex AI embeddings client, created on first use and reused afterwards.

    Only the model name comes from settings. The Google project and location are not
    passed here; how the library resolves them is not checked in this repo.
    """
    return VertexAIEmbeddings(model_name=settings.embedding_model_name)
