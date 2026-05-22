"""
ChromaDB vector store setup and operations.
Local persistence with no external database required.
"""

from typing import List, Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from vectorstore.embeddings import get_embeddings
from config.settings import get_settings
from utils.logger import logger

_stores = {}


def get_vectorstore(collection_name: str = "code_patterns") -> Chroma:
    """
    Get or create a ChromaDB vector store collection.
    
    Args:
        collection_name: Name of the collection (code_patterns, test_templates, etc.)
    
    Returns:
        Chroma vector store instance.
    """
    global _stores
    if collection_name not in _stores:
        settings = get_settings()
        logger.info(f"Initializing ChromaDB collection: {collection_name}")
        _stores[collection_name] = Chroma(
            collection_name=collection_name,
            embedding_function=get_embeddings(),
            persist_directory=settings.chroma_persist_dir,
        )
    return _stores[collection_name]


def add_documents(
    documents: List[Document],
    collection_name: str = "code_patterns",
) -> None:
    """Add documents to a vector store collection."""
    store = get_vectorstore(collection_name)
    store.add_documents(documents)
    logger.info(f"Added {len(documents)} documents to '{collection_name}'")


def similarity_search(
    query: str,
    collection_name: str = "code_patterns",
    k: int = 5,
) -> List[Document]:
    """Search for similar documents in a collection."""
    store = get_vectorstore(collection_name)
    results = store.similarity_search(query, k=k)
    return results


def get_retriever(collection_name: str = "code_patterns", k: int = 5):
    """Get a LangChain retriever for a collection."""
    store = get_vectorstore(collection_name)
    return store.as_retriever(search_kwargs={"k": k})
