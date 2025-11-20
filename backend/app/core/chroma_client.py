"""ChromaDB client initialization and management."""
import os
import logging
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Global Chroma client instance
_chroma_client: Optional[chromadb.ClientAPI] = None
_chroma_collection: Optional[chromadb.Collection] = None


def get_chroma_client() -> chromadb.ClientAPI:
    """
    Get or create ChromaDB client instance.

    Returns:
        ChromaDB client
    """
    global _chroma_client

    if _chroma_client is None:
        # Get persistence directory from environment or use default
        persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

        try:
            _chroma_client = chromadb.PersistentClient(
                path=persist_directory,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(f"ChromaDB client initialized with persistence directory: {persist_directory}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    return _chroma_client


def get_chroma_collection(collection_name: str = "documents") -> chromadb.Collection:
    """
    Get or create ChromaDB collection.

    Args:
        collection_name: Name of the collection

    Returns:
        ChromaDB collection
    """
    global _chroma_collection

    client = get_chroma_client()

    try:
        # Try to get existing collection
        _chroma_collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "Document embeddings for semantic search"},
        )
        logger.info(f"ChromaDB collection '{collection_name}' ready")
    except Exception as e:
        logger.error(f"Failed to get/create ChromaDB collection: {e}")
        raise

    return _chroma_collection


def add_embeddings_to_chroma(
    collection_name: str,
    embeddings: List[List[float]],
    texts: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
) -> None:
    """
    Add embeddings to ChromaDB collection.

    Args:
        collection_name: Collection name
        embeddings: List of embedding vectors
        texts: List of text contents
        metadatas: List of metadata dictionaries
        ids: List of unique IDs for each embedding
    """
    try:
        collection = get_chroma_collection(collection_name)

        collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Added {len(embeddings)} embeddings to ChromaDB collection '{collection_name}'")
    except Exception as e:
        logger.error(f"Failed to add embeddings to ChromaDB: {e}")
        raise


def delete_embeddings_from_chroma(
    collection_name: str,
    doc_id: str,
) -> None:
    """
    Delete all embeddings for a document from ChromaDB.

    Args:
        collection_name: Collection name
        doc_id: Document ID to delete
    """
    try:
        collection = get_chroma_collection(collection_name)

        # Delete by metadata filter
        collection.delete(
            where={"doc_id": doc_id},
        )
        logger.info(f"Deleted embeddings for document {doc_id} from ChromaDB")
    except Exception as e:
        logger.error(f"Failed to delete embeddings from ChromaDB: {e}")
        raise


def query_chroma(
    collection_name: str,
    query_embeddings: List[List[float]],
    n_results: int = 10,
    where: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Query ChromaDB collection.

    Args:
        collection_name: Collection name
        query_embeddings: Query embedding vectors
        n_results: Number of results to return
        where: Optional metadata filter

    Returns:
        Query results dictionary
    """
    try:
        collection = get_chroma_collection(collection_name)

        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=n_results,
            where=where,
        )
        return results
    except Exception as e:
        logger.error(f"Failed to query ChromaDB: {e}")
        raise

