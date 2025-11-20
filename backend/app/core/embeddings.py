"""Embedding generation service using SentenceTransformers."""
import logging
from typing import List, Optional, Tuple
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Global model cache: key is (model_name, device), value is model instance
_embedding_models: dict[Tuple[str, str], SentenceTransformer] = {}


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2", force_cpu: bool = True) -> SentenceTransformer:
    """
    Get or create SentenceTransformer model instance.
    
    Always uses CPU as per project requirements.

    Args:
        model_name: Name of the SentenceTransformer model
        force_cpu: Always True (CPU-only mode). Kept for API compatibility.

    Returns:
        SentenceTransformer model
    """
    global _embedding_models

    # Always use CPU
    device = "cpu"
    cache_key = (model_name, device)

    # Check if model is already cached
    if cache_key in _embedding_models:
        logger.debug(f"Using cached embedding model '{model_name}' on {device}")
        return _embedding_models[cache_key]

    try:
        logger.info(f"Loading embedding model '{model_name}' on device: {device}")
        model = SentenceTransformer(model_name, device=device)
        _embedding_models[cache_key] = model
        logger.info(f"Embedding model '{model_name}' loaded successfully on {device}")
        return model
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        raise


def generate_embeddings(
    texts: List[str],
    model_name: str = "all-MiniLM-L6-v2",
    batch_size: int = 8,
    show_progress_bar: bool = False,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    
    Default batch size is optimized for CPU (8). For GPU, use higher values.

    Args:
        texts: List of texts to embed
        model_name: Name of the SentenceTransformer model
        batch_size: Batch size for processing (default: 8 for CPU)
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

