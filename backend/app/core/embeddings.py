"""Embedding generation service using SentenceTransformers."""
import logging
from typing import List, Optional
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global model instance
_embedding_model: Optional[SentenceTransformer] = None


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2") -> SentenceTransformer:
    """
    Get or create SentenceTransformer model instance.

    Args:
        model_name: Name of the SentenceTransformer model

    Returns:
        SentenceTransformer model
    """
    global _embedding_model

    if _embedding_model is None:
        try:
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading embedding model '{model_name}' on device: {device}")

            _embedding_model = SentenceTransformer(model_name, device=device)
            logger.info(f"Embedding model '{model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    return _embedding_model


def generate_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 32,
    show_progress_bar: bool = False,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts: List of texts to embed
        model_name: Name of the SentenceTransformer model
        batch_size: Batch size for processing
        show_progress_bar: Whether to show progress bar

    Returns:
        List of embedding vectors
    """
    if not texts:
        return []

    try:
        model = get_embedding_model(model_name)

        # Generate embeddings in batches
        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress_bar,
            convert_to_numpy=True,
            normalize_embeddings=True,  # Normalize for cosine similarity
        )

        # Convert to list of lists
        embeddings_list = embeddings.tolist()

        logger.info(f"Generated {len(embeddings_list)} embeddings")
        return embeddings_list

    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
        raise

