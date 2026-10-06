"""Connection to Vertex AI Vector Search (the database that stores our embeddings)."""
from functools import lru_cache

from google.cloud import aiplatform
from langchain_google_vertexai import VectorSearchVectorStore

from config.settings import settings
from rag.embeddings import get_embeddings


@lru_cache(maxsize=1)
def get_vector_store() -> VectorSearchVectorStore:
    """Connect on first use, so the API can start (e.g. /api/health) before GCP is configured."""
    # Sets the project and region for Google's Vertex AI client library, for the whole process.
    aiplatform.init(project=settings.GCP_PROJECT, location=settings.GCP_REGION)

    return VectorSearchVectorStore.from_components(
        project_id=settings.GCP_PROJECT,
        region=settings.GCP_REGION,
        embedding=get_embeddings(),  # NOTE: singular "embedding", not "embeddings"
        index_id=settings.vector_search_index_id,
        endpoint_id=settings.vector_search_index_endpoint_id,
        # The same bucket (GCS_BUCKET_NAME) also holds uploads and logs; what the library itself
        # stores in it is not checked in this repo.
        gcs_bucket_name=settings.GCS_BUCKET_NAME,
        # Matches the index, which deploy.yml creates with the STREAM_UPDATE update method.
        stream_update=True,
    )
