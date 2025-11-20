"""Embedding indexing module for chunk-based semantic search.

This module provides a robust pipeline for generating and persisting embeddings
for chunks already stored in the database, with batch processing, OOM handling,
and comprehensive metrics tracking.
"""
import uuid
import logging
import time
import hashlib
import os
import psutil
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session

from app.db.models import Document, Chunk, DocumentStatus
from app.core.embeddings import generate_embeddings, get_embedding_model
from app.core.chroma_client import get_chroma_collection, add_embeddings_to_chroma

logger = logging.getLogger(__name__)


@dataclass
class IndexingMetrics:
    """Metrics for embedding indexing process."""
    total_chunks: int = 0
    chunks_indexed: int = 0
    batches_processed: int = 0
    total_time_seconds: float = 0.0
    embedding_time_seconds: float = 0.0
    persistence_time_seconds: float = 0.0
    peak_memory_mb: float = 0.0
    errors: List[str] = None
    batch_times: List[float] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.batch_times is None:
            self.batch_times = []


class EmbeddingIndexer:
    """Handles embedding generation and persistence for chunks."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        collection_name: str = "documents",
        initial_batch_size: int = 6,
        min_batch_size: int = 2,
        max_batch_size: int = 8,
    ):
        """
        Initialize the embedding indexer.
        
        Args:
            model_name: SentenceTransformer model name
            collection_name: ChromaDB collection name
            initial_batch_size: Starting batch size (will adapt if OOM)
            min_batch_size: Minimum batch size before failing
            max_batch_size: Maximum batch size for CPU processing
        """
        self.model_name = model_name
        self.collection_name = collection_name
        self.initial_batch_size = initial_batch_size
        self.min_batch_size = min_batch_size
        self.max_batch_size = max_batch_size
        self.current_batch_size = initial_batch_size
        
        # Ensure model is loaded (will be reused) - CPU is default
        logger.info(f"Initializing EmbeddingIndexer with model: {model_name}")
        get_embedding_model(model_name, force_cpu=True)
    
    def _compute_chunk_hash(self, text: str) -> str:
        """Compute SHA256 hash for a chunk text."""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()[:16]
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    def _generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int,
    ) -> Tuple[List[List[float]], float]:
        """
        Generate embeddings for a batch of texts with error handling.
        
        Returns:
            Tuple of (embeddings, time_taken)
        """
        start_time = time.time()
        try:
            embeddings = generate_embeddings(
                texts=texts,
                model_name=self.model_name,
                batch_size=batch_size,
                show_progress_bar=False,
            )
            elapsed = time.time() - start_time
            return embeddings, elapsed
        except RuntimeError as e:
            if "out of memory" in str(e).lower() or "oom" in str(e).lower():
                raise MemoryError(f"OOM during embedding generation: {e}")
            raise
    
    def index_document_chunks(
        self,
        db: Session,
        doc_id: uuid.UUID,
        skip_existing: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate and persist embeddings for all chunks of a document.
        
        Args:
            db: Database session
            doc_id: Document UUID
            skip_existing: If True, skip chunks already indexed in ChromaDB
            
        Returns:
            Dictionary with indexing results and metrics
        """
        start_time = time.time()
        metrics = IndexingMetrics()
        
        # Verify document exists
        document = db.query(Document).filter(Document.doc_id == doc_id).first()
        if not document:
            raise ValueError(f"Document {doc_id} not found")
        
        # Get all chunks for the document, ordered by chunk_id
        chunks = (
            db.query(Chunk)
            .filter(Chunk.doc_id == doc_id)
            .order_by(Chunk.chunk_id)
            .all()
        )
        
        if not chunks:
            logger.warning(f"No chunks found for document {doc_id}")
            return {
                "doc_id": str(doc_id),
                "chunks_indexed": 0,
                "total_chunks": 0,
                "metrics": metrics.__dict__,
                "collection_size": self._get_collection_size(),
            }
        
        metrics.total_chunks = len(chunks)
        logger.info(f"Indexing {len(chunks)} chunks for document {doc_id}")
        
        # Check existing embeddings if skip_existing is True
        chunks_to_index = chunks
        if skip_existing:
            collection = get_chroma_collection(self.collection_name)
            existing_ids = set()
            
            # Query existing embeddings for this document
            try:
                existing_results = collection.get(
                    where={"doc_id": str(doc_id)},
                )
                if existing_results and existing_results.get("ids"):
                    existing_ids = set(existing_results["ids"])
                    logger.info(f"Found {len(existing_ids)} existing embeddings for document {doc_id}")
            except Exception as e:
                logger.warning(f"Could not check existing embeddings: {e}")
            
            # Filter out chunks that already have embeddings
            chunks_to_index = [
                chunk for chunk in chunks
                if f"{doc_id}_{chunk.chunk_id}" not in existing_ids
            ]
            
            if len(chunks_to_index) < len(chunks):
                logger.info(f"Skipping {len(chunks) - len(chunks_to_index)} already indexed chunks")
        
        if not chunks_to_index:
            logger.info(f"All chunks for document {doc_id} are already indexed")
            return {
                "doc_id": str(doc_id),
                "chunks_indexed": 0,
                "total_chunks": len(chunks),
                "metrics": metrics.__dict__,
                "collection_size": self._get_collection_size(),
            }
        
        # Reset batch size for this document
        self.current_batch_size = self.initial_batch_size
        
        # Process chunks in batches
        chunk_texts = [chunk.text for chunk in chunks_to_index]
        total_batches = (len(chunk_texts) + self.current_batch_size - 1) // self.current_batch_size
        
        logger.info(f"Processing {len(chunk_texts)} chunks in batches of {self.current_batch_size}")
        
        all_embeddings = []
        all_metadatas = []
        all_ids = []
        all_texts = []
        
        for batch_idx in range(0, len(chunk_texts), self.current_batch_size):
            batch_texts = chunk_texts[batch_idx:batch_idx + self.current_batch_size]
            batch_chunks = chunks_to_index[batch_idx:batch_idx + self.current_batch_size]
            
            batch_start_time = time.time()
            batch_num = (batch_idx // self.current_batch_size) + 1
            
            try:
                # Generate embeddings with adaptive batch size
                memory_before = self._get_memory_usage_mb()
                
                try:
                    embeddings, embedding_time = self._generate_embeddings_batch(
                        batch_texts,
                        self.current_batch_size,
                    )
                    metrics.embedding_time_seconds += embedding_time
                    
                    # Track peak memory
                    memory_after = self._get_memory_usage_mb()
                    peak_memory = max(memory_before, memory_after)
                    metrics.peak_memory_mb = max(metrics.peak_memory_mb, peak_memory)
                    
                except MemoryError as e:
                    # Reduce batch size and retry
                    if self.current_batch_size > self.min_batch_size:
                        new_batch_size = max(self.min_batch_size, self.current_batch_size // 2)
                        logger.warning(
                            f"OOM at batch size {self.current_batch_size}, "
                            f"reducing to {new_batch_size}"
                        )
                        self.current_batch_size = new_batch_size
                        
                        # Retry with smaller batch
                        embeddings, embedding_time = self._generate_embeddings_batch(
                            batch_texts,
                            self.current_batch_size,
                        )
                        metrics.embedding_time_seconds += embedding_time
                    else:
                        error_msg = f"OOM at minimum batch size {self.min_batch_size}"
                        logger.error(error_msg)
                        metrics.errors.append(error_msg)
                        raise
                
                # Prepare metadata and IDs
                for i, chunk in enumerate(batch_chunks):
                    chunk_hash = self._compute_chunk_hash(chunk.text)
                    metadata = {
                        "doc_id": str(doc_id),
                        "chunk_id": chunk.chunk_id,
                        "chunk_uuid": str(chunk.id),
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                        "hash": chunk_hash,
                    }
                    if chunk.page_number is not None:
                        metadata["page_number"] = chunk.page_number
                    
                    all_metadatas.append(metadata)
                    all_ids.append(f"{doc_id}_{chunk.chunk_id}")
                    all_texts.append(chunk.text)
                
                all_embeddings.extend(embeddings)
                
                batch_time = time.time() - batch_start_time
                metrics.batch_times.append(batch_time)
                metrics.batches_processed += 1
                
                logger.info(
                    f"Batch {batch_num}/{total_batches} processed: "
                    f"{len(batch_texts)} chunks in {batch_time:.2f}s "
                    f"(embedding: {embedding_time:.2f}s, memory: {memory_after:.1f}MB)"
                )
                
            except Exception as e:
                error_msg = f"Error processing batch {batch_num}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                metrics.errors.append(error_msg)
                # Continue with next batch instead of failing completely
                continue
        
        # Persist all embeddings to ChromaDB
        if all_embeddings:
            persistence_start = time.time()
            try:
                add_embeddings_to_chroma(
                    collection_name=self.collection_name,
                    embeddings=all_embeddings,
                    texts=all_texts,
                    metadatas=all_metadatas,
                    ids=all_ids,
                )
                metrics.persistence_time_seconds = time.time() - persistence_start
                metrics.chunks_indexed = len(all_embeddings)
                
                logger.info(
                    f"Persisted {len(all_embeddings)} embeddings to ChromaDB "
                    f"in {metrics.persistence_time_seconds:.2f}s"
                )
            except Exception as e:
                error_msg = f"Failed to persist embeddings: {str(e)}"
                logger.error(error_msg, exc_info=True)
                metrics.errors.append(error_msg)
                raise
        
        metrics.total_time_seconds = time.time() - start_time
        
        # Get final collection size
        collection_size = self._get_collection_size()
        
        logger.info(
            f"Indexing completed for document {doc_id}: "
            f"{metrics.chunks_indexed}/{metrics.total_chunks} chunks indexed "
            f"in {metrics.total_time_seconds:.2f}s "
            f"(peak memory: {metrics.peak_memory_mb:.1f}MB)"
        )
        
        return {
            "doc_id": str(doc_id),
            "chunks_indexed": metrics.chunks_indexed,
            "total_chunks": metrics.total_chunks,
            "total_time_seconds": metrics.total_time_seconds,
            "collection_size": collection_size,
            "metrics": {
                "batches_processed": metrics.batches_processed,
                "embedding_time_seconds": metrics.embedding_time_seconds,
                "persistence_time_seconds": metrics.persistence_time_seconds,
                "peak_memory_mb": metrics.peak_memory_mb,
                "errors": metrics.errors,
                "avg_batch_time_seconds": (
                    sum(metrics.batch_times) / len(metrics.batch_times)
                    if metrics.batch_times else 0.0
                ),
            },
        }
    
    def _get_collection_size(self) -> int:
        """Get the current size of the ChromaDB collection."""
        try:
            collection = get_chroma_collection(self.collection_name)
            count = collection.count()
            return count
        except Exception as e:
            logger.warning(f"Could not get collection size: {e}")
            return 0

