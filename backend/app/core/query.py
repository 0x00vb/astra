"""RAG query module for retrieving and assembling context from vector database.

This module provides deterministic, compact, properly tagged context assembly
that maximizes grounding and minimizes token waste.
"""
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from collections import OrderedDict

from app.core.embeddings import generate_embeddings
from app.core.chroma_client import query_chroma, get_chroma_collection
from app.db.models import Chunk

logger = logging.getLogger(__name__)


class LRUCache:
    """Lightweight LRU cache for query results."""
    
    def __init__(self, maxsize: int = 128):
        self.cache: OrderedDict[str, Any] = OrderedDict()
        self.maxsize = maxsize
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, moving it to end (most recently used)."""
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Put value in cache, evicting oldest if at capacity."""
        if key in self.cache:
            self.cache.move_to_end(key)
        elif len(self.cache) >= self.maxsize:
            self.cache.popitem(last=False)  # Remove oldest
        self.cache[key] = value
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()


def extract_top_sentences(text: str, max_chars: int) -> str:
    """
    Extract top sentences from text to fit within max_chars.
    
    Uses simple sentence splitting and prioritizes earlier sentences.
    This is a fallback when chunk truncation is needed.
    
    Args:
        text: Text to summarize
        max_chars: Maximum characters to return
        
    Returns:
        Truncated text with complete sentences
    """
    if len(text) <= max_chars:
        return text
    
    # Simple sentence splitting (basic approach)
    sentences = []
    current_sentence = ""
    
    for char in text:
        current_sentence += char
        if char in '.!?':
            sentences.append(current_sentence.strip())
            current_sentence = ""
    
    if current_sentence.strip():
        sentences.append(current_sentence.strip())
    
    # Take sentences until we exceed max_chars
    result = ""
    for sentence in sentences:
        if len(result) + len(sentence) + 1 <= max_chars:
            result += sentence + " "
        else:
            break
    
    return result.strip() if result else text[:max_chars]


class QueryRetriever:
    """Handles query embedding, retrieval, and context assembly."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        collection_name: str = "documents",
        cache_size: int = 128,
    ):
        """
        Initialize query retriever.
        
        Args:
            model_name: Embedding model name (must match ingestion model)
            collection_name: ChromaDB collection name
            cache_size: LRU cache size for query results
        """
        self.model_name = model_name
        self.collection_name = collection_name
        self.chunks_cache = LRUCache(maxsize=cache_size)
        self.context_cache = LRUCache(maxsize=cache_size)
        
        logger.info(
            f"Initialized QueryRetriever with model={model_name}, "
            f"collection={collection_name}, cache_size={cache_size}"
        )
    
    def _compute_query_hash(self, query: str, top_k: int, max_context_chars: int) -> str:
        """Compute hash for query caching."""
        cache_key = f"{query}|{top_k}|{max_context_chars}"
        return hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:16]
    
    def retrieve_chunks(
        self,
        query: str,
        top_k: int = 6,
        db_session=None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve top_k most relevant chunks for a query.
        
        Args:
            query: User query string
            top_k: Number of chunks to retrieve
            db_session: Optional database session for validation
            
        Returns:
            List of chunk dictionaries with metadata, sorted by similarity (desc)
        """
        cache_key = f"chunks_{self._compute_query_hash(query, top_k, 0)}"
        cached = self.chunks_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Cache hit for query: {query[:50]}...")
            return cached
        
        start_time = time.time()
        
        # Generate query embedding
        try:
            query_embeddings = generate_embeddings(
                texts=[query],
                model_name=self.model_name,
                batch_size=1,
                show_progress_bar=False,
            )
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise
        
        # Query vector database
        try:
            results = query_chroma(
                collection_name=self.collection_name,
                query_embeddings=query_embeddings,
                n_results=top_k,
            )
        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {e}")
            raise
        
        # Process results
        retrieved_chunks = []
        
        if results.get("ids") and len(results["ids"]) > 0:
            ids = results["ids"][0]  # First (and only) query
            distances = results.get("distances", [[]])[0] if results.get("distances") else []
            metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            documents = results.get("documents", [[]])[0] if results.get("documents") else []
            
            for i, chunk_id in enumerate(ids):
                if i < len(documents):
                    metadata = metadatas[i] if i < len(metadatas) else {}
                    distance = distances[i] if i < len(distances) else 1.0
                    similarity = 1.0 - distance  # Convert distance to similarity
                    
                    chunk_data = {
                        "chunk_id": chunk_id,
                        "doc_id": metadata.get("doc_id", ""),
                        "chunk_id_num": metadata.get("chunk_id", 0),
                        "page_number": metadata.get("page_number"),
                        "text": documents[i],
                        "similarity": similarity,
                        "distance": distance,
                        "metadata": metadata,
                    }
                    retrieved_chunks.append(chunk_data)
        
        # Sort by similarity (descending)
        retrieved_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Retrieved {len(retrieved_chunks)} chunks for query in {elapsed:.3f}s"
        )
        
        # Cache results
        self.chunks_cache.put(cache_key, retrieved_chunks)
        
        return retrieved_chunks
    
    def assemble_context(
        self,
        query: str,
        top_k: int = 6,
        max_context_chars: int = 4000,
        db_session=None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Assemble deterministic, compact, properly tagged context.
        
        Args:
            query: User query string
            top_k: Number of chunks to retrieve
            max_context_chars: Maximum characters in context
            db_session: Optional database session
            
        Returns:
            Tuple of (assembled_context_string, list_of_source_citations)
        """
        cache_key = f"context_{self._compute_query_hash(query, top_k, max_context_chars)}"
        cached = self.context_cache.get(cache_key)
        if cached is not None:
            logger.debug(f"Context cache hit for query: {query[:50]}...")
            return cached
        
        start_time = time.time()
        
        # Retrieve chunks
        chunks = self.retrieve_chunks(query, top_k=top_k, db_session=db_session)
        
        if not chunks:
            context = self._format_empty_context(query)
            citations = []
            self.context_cache.put(cache_key, (context, citations))
            return context, citations
        
        # Assemble context with character limit
        context_parts = []
        citations = []
        current_length = 0
        
        # Header
        header = "[SYSTEM CONTEXT RULES]\nUse only the information provided below.\nCite evidence using [DOC:doc_id | CHUNK:chunk_id].\n\n[CONTEXT SOURCES]\n"
        current_length += len(header)
        context_parts.append(header)
        
        # Add chunks until limit
        for idx, chunk in enumerate(chunks):
            doc_id = chunk["doc_id"]
            chunk_id_num = chunk["chunk_id_num"]
            page = chunk.get("page_number")
            text = chunk["text"]
            
            # Format source header
            page_str = f" | PAGE: {page}" if page is not None else ""
            source_header = f"--- SOURCE {idx + 1} ---\n[DOC: {doc_id} | CHUNK: {chunk_id_num}{page_str}]\n\n"
            source_footer = "\n\n"
            
            # Calculate available space
            header_len = len(source_header) + len(source_footer)
            available_chars = max_context_chars - current_length - header_len
            
            if available_chars <= 0:
                # No space for more chunks
                break
            
            # Truncate text if needed
            if len(text) > available_chars:
                # Try extractive summarization
                truncated_text = extract_top_sentences(text, available_chars)
                if len(truncated_text) > available_chars:
                    # Fallback: hard truncate
                    truncated_text = text[:available_chars].rsplit(' ', 1)[0] + "..."
                text = truncated_text
            
            # Add source
            source_block = source_header + text + source_footer
            context_parts.append(source_block)
            current_length += len(source_block)
            
            # Track citation
            citation = {
                "doc_id": doc_id,
                "chunk_id": chunk_id_num,
                "page": page,
                "similarity": chunk["similarity"],
            }
            citations.append(citation)
            
            # Check if we've reached the limit
            if current_length >= max_context_chars:
                break
        
        # Add user question
        user_question = f"\n[USER QUESTION]\n{query}\n"
        context_parts.append(user_question)
        
        context = "".join(context_parts)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Assembled context ({len(context)} chars, {len(citations)} sources) "
            f"in {elapsed:.3f}s"
        )
        
        result = (context, citations)
        self.context_cache.put(cache_key, result)
        
        return result
    
    def _format_empty_context(self, query: str) -> str:
        """Format context when no chunks are retrieved."""
        return (
            "[SYSTEM CONTEXT RULES]\n"
            "Use only the information provided below.\n"
            "Cite evidence using [DOC:doc_id | CHUNK:chunk_id].\n\n"
            "[CONTEXT SOURCES]\n"
            "No relevant sources found.\n\n"
            f"[USER QUESTION]\n{query}\n"
        )
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self.chunks_cache.clear()
        self.context_cache.clear()
        logger.info("Query caches cleared")

