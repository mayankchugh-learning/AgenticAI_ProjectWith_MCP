"""Where the ORIGINAL PDF files are kept. Which place depends on APP_MODE.

    local  -> a folder on your disk:      .meridian/uploads/
    cloud  -> a Cloud Storage bucket:     gs://<GCS_BUCKET_NAME>/<GCS_PREFIX>

Three operations are all the app needs:
    save(local_path, filename)  keep a copy of an uploaded PDF
    pdfs()                      yield (local_path, source) for every stored PDF
    source_key(filename)        the ONE source name a file is indexed under (see below)
"""
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager

from config.settings import settings
from exceptions import ConfigurationError
from logger import GLOBAL_LOGGER as log


def source_key(filename: str) -> str:
    """The single source name stored in every chunk's metadata for this file.

    Uploading a PDF and indexing the stored copy are two ways to index the same file, and the
    chunk ID is built from the source (rag/data_ingestion.py). Both paths must therefore use this
    one key; otherwise the same PDF is indexed twice under different names. The key depends only
    on the file name, not on the mode or the storage location.
    """
    return f"doc://{os.path.basename(filename)}"


def location() -> str:
    """Human-readable location, shown on the System Status tab."""
    if settings.is_cloud:
        return f"gs://{settings.GCS_BUCKET_NAME}/{settings.GCS_PREFIX}"
    return settings.local_upload_dir


def _bucket():
    """Cloud only: the GCS bucket client. Imported lazily so local mode never loads google-cloud-storage."""
    if not settings.GCS_BUCKET_NAME:
        raise ConfigurationError("APP_MODE=cloud needs GCS_BUCKET_NAME.")
    from google.cloud import storage

    return storage.Client(project=settings.GCP_PROJECT or None).bucket(settings.GCS_BUCKET_NAME)


def save(local_path: str, filename: str) -> str:
    """Keep a copy of the uploaded PDF. Returns where it was stored."""
    filename = os.path.basename(filename)
    if settings.is_cloud:
        blob_name = f"{settings.GCS_PREFIX}{filename}"
        _bucket().blob(blob_name).upload_from_filename(local_path, content_type="application/pdf")
        stored_at = f"gs://{settings.GCS_BUCKET_NAME}/{blob_name}"
    else:
        os.makedirs(settings.local_upload_dir, exist_ok=True)
        stored_at = os.path.join(settings.local_upload_dir, filename)
        shutil.copyfile(local_path, stored_at)
    log.info("Original file stored", filename=filename, stored_at=stored_at)
    return stored_at


@contextmanager
def pdfs() -> Iterator[Iterator[tuple[str, str]]]:
    """Yield (local_path, source) for every stored PDF; `source` comes from source_key().

    Used as a context manager because cloud files are downloaded to a temp folder
    that must be cleaned up afterwards.
    """
    if not settings.is_cloud:
        folder = settings.local_upload_dir
        os.makedirs(folder, exist_ok=True)
        yield (
            (os.path.join(folder, name), source_key(name))
            for name in sorted(os.listdir(folder))
            if name.lower().endswith(".pdf")
        )
        return

    tmp_dir = tempfile.mkdtemp()
    try:
        def _download() -> Iterator[tuple[str, str]]:
            for blob in _bucket().list_blobs(prefix=settings.GCS_PREFIX):
                if not blob.name.lower().endswith(".pdf"):
                    continue
                path = os.path.join(tmp_dir, os.path.basename(blob.name))
                blob.download_to_filename(path)
                yield path, source_key(blob.name)

        yield _download()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
