import logging
from pathlib import Path

import numpy as np
from fastembed import TextEmbedding

logger = logging.getLogger("prepdesk.embeddings")

MODEL_NAME = "BAAI/bge-small-en-v1.5"
_CACHE_DIR = Path(__file__).resolve().parent / "data" / "models"

_model: TextEmbedding | None = None


def _get_model() -> TextEmbedding:
    """Lazily load and cache the fastembed TextEmbedding model once."""
    global _model
    if _model is None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("Loading embedding model %s (cache_dir=%s)", MODEL_NAME, _CACHE_DIR)
        _model = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(_CACHE_DIR))
    return _model


def _l2_normalize(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize a 1D or 2D float32 numpy array."""
    arr = np.asarray(vectors, dtype=np.float32)
    if arr.ndim == 1:
        norm = float(np.linalg.norm(arr))
        return (arr / norm).astype(np.float32) if norm > 0.0 else arr
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    safe_norms = np.where(norms > 0.0, norms, 1.0)
    return (arr / safe_norms).astype(np.float32)


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embed a list of passage strings into L2-normalized float32 vectors."""
    if not texts:
        return np.empty((0, 0), dtype=np.float32)
    vectors = list(_get_model().passage_embed(texts))
    return _l2_normalize(np.vstack(vectors))


def embed_query(text: str) -> np.ndarray:
    """Embed a single query string into an L2-normalized float32 vector."""
    vectors = list(_get_model().query_embed(text))
    return _l2_normalize(np.asarray(vectors[0], dtype=np.float32))
