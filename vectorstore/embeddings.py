"""
HuggingFace embedding model setup.
Uses sentence-transformers for local, free embeddings (no API key required).
"""

from langchain_huggingface import HuggingFaceEmbeddings
from config.settings import get_settings
from utils.logger import logger

_embeddings = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Get or create the singleton embedding model instance."""
    global _embeddings
    if _embeddings is None:
        settings = get_settings()
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        _embeddings = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding model loaded successfully")
    return _embeddings
