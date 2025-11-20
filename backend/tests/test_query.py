"""Comprehensive tests for RAG query module.

These tests validate:
- Retrieval correctness
- Grounding ratio (citations in answers)
- Performance metrics
- Safety and determinism (no fabricated citations)
- Context assembly formatting
- Caching behavior
"""
import sys
import os
from pathlib import Path

# Add backend directory to Python path for imports
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import uuid
import tempfile
import shutil
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, Base, engine
from app.db.models import Document, Chunk, DocumentStatus
from app.core.indexing import EmbeddingIndexer
from app.core.query import QueryRetriever, extract_top_sentences
from app.core.llm import get_llm_provider, PlaceholderLLM


# Test configuration
TEST_COLLECTION_NAME = "test_documents_query"
TEST_MODEL_NAME = "all-MiniLM-L6-v2"


@pytest.fixture(scope="function")
def temp_chroma_dir():
    """Create a temporary ChromaDB directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_query_test_")
    os.environ["CHROMA_PERSIST_DIR"] = temp_dir
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    if "CHROMA_PERSIST_DIR" in os.environ:
        del os.environ["CHROMA_PERSIST_DIR"]


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing."""
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(scope="function")
def indexed_document(temp_chroma_dir, db_session):
    """Create and index a test document with chunks."""
    doc_id = uuid.uuid4()
    document = Document(
        doc_id=doc_id,
        filename="test_qa_document.txt",
        file_type="txt",
        file_size=2000,
        status=DocumentStatus.INDEXED,
        total_chunks=5,
        total_characters=2000,
        total_pages=3,
    )
    db_session.add(document)
    
    # Create test chunks with known QA pairs
    chunks_data = [
        {
            "text": "Python is a high-level programming language known for its simplicity and readability. It was created by Guido van Rossum and first released in 1991.",
            "chunk_id": 0,
            "start_char": 0,
            "end_char": 150,
            "page_number": 1,
        },
        {
            "text": "FastAPI is a modern web framework for building APIs with Python. It is based on standard Python type hints and provides automatic API documentation.",
            "chunk_id": 1,
            "start_char": 150,
            "end_char": 300,
            "page_number": 1,
        },
        {
            "text": "Vector databases store embeddings in a way that enables efficient similarity search. ChromaDB is an open-source vector database.",
            "chunk_id": 2,
            "start_char": 300,
            "end_char": 450,
            "page_number": 2,
        },
        {
            "text": "RAG (Retrieval-Augmented Generation) combines information retrieval with language models to provide grounded answers.",
            "chunk_id": 3,
            "start_char": 450,
            "end_char": 600,
            "page_number": 2,
        },
        {
            "text": "Embeddings are dense vector representations of text that capture semantic meaning. They enable semantic search.",
            "chunk_id": 4,
            "start_char": 600,
            "end_char": 750,
            "page_number": 3,
        },
    ]
    
    chunks = []
    for chunk_data in chunks_data:
        chunk = Chunk(
            id=uuid.uuid4(),
            doc_id=doc_id,
            chunk_id=chunk_data["chunk_id"],
            start_char=chunk_data["start_char"],
            end_char=chunk_data["end_char"],
            page_number=chunk_data.get("page_number"),
            text=chunk_data["text"],
            token_count=len(chunk_data["text"].split()),
        )
        chunks.append(chunk)
        db_session.add(chunk)
    
    db_session.commit()
    db_session.refresh(document)
    
    # Index the document
    indexer = EmbeddingIndexer(
        model_name=TEST_MODEL_NAME,
        collection_name=TEST_COLLECTION_NAME,
    )
    indexer.index_document_chunks(
        db=db_session,
        doc_id=doc_id,
        skip_existing=False,
    )
    
    return document, chunks


class TestQueryRetrieval:
    """Test query retrieval correctness."""
    
    def test_retrieve_chunks_returns_relevant_results(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that retrieval returns semantically relevant chunks."""
        document, chunks = indexed_document
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        # Query about Python
        query = "What is Python programming language?"
        results = retriever.retrieve_chunks(query, top_k=3, db_session=db_session)
        
        assert len(results) > 0
        assert results[0]["doc_id"] == str(document.doc_id)
        # Should retrieve chunk 0 (about Python)
        assert results[0]["chunk_id_num"] == 0
        assert "Python" in results[0]["text"].lower()
    
    def test_retrieve_chunks_sorted_by_similarity(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that chunks are sorted by similarity (descending)."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is FastAPI?"
        results = retriever.retrieve_chunks(query, top_k=5, db_session=db_session)
        
        # Check sorting
        similarities = [r["similarity"] for r in results]
        assert similarities == sorted(similarities, reverse=True)
        assert all(0 <= s <= 1 for s in similarities)
    
    def test_retrieve_chunks_includes_metadata(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that retrieved chunks include all required metadata."""
        document, chunks = indexed_document
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "Tell me about vector databases"
        results = retriever.retrieve_chunks(query, top_k=2, db_session=db_session)
        
        assert len(results) > 0
        for result in results:
            assert "doc_id" in result
            assert "chunk_id_num" in result
            assert "text" in result
            assert "similarity" in result
            assert "metadata" in result
            assert result["doc_id"] == str(document.doc_id)


class TestContextAssembly:
    """Test context assembly formatting."""
    
    def test_assemble_context_format(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that context is assembled in correct format."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is RAG?"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # Check format
        assert "[SYSTEM CONTEXT RULES]" in context
        assert "[CONTEXT SOURCES]" in context
        assert "[USER QUESTION]" in context
        assert query in context
        
        # Check citations
        assert len(citations) > 0
        assert len(citations) <= 3  # top_k limit
    
    def test_assemble_context_respects_max_chars(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that context respects max_context_chars limit."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "Tell me about programming"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=10,
            max_context_chars=500,  # Small limit
            db_session=db_session,
        )
        
        # Context should be within limit (with some tolerance for formatting)
        assert len(context) <= 500 + 200  # Allow some overhead for formatting
    
    def test_assemble_context_includes_citations(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that context includes proper citation tags."""
        document, chunks = indexed_document
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is Python?"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=2,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # Check citation format in context
        assert f"[DOC: {str(document.doc_id)}" in context
        assert "CHUNK:" in context
        
        # Check citations list
        assert len(citations) > 0
        for citation in citations:
            assert citation["doc_id"] == str(document.doc_id)
            assert "chunk_id" in citation
    
    def test_assemble_context_empty_when_no_chunks(
        self, temp_chroma_dir, db_session
    ):
        """Test context assembly when no chunks are retrieved."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "Completely unrelated query that won't match anything"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=5,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        assert "[SYSTEM CONTEXT RULES]" in context
        assert query in context
        assert len(citations) == 0


class TestCaching:
    """Test caching behavior."""
    
    def test_query_cache_hit(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that repeated queries use cache."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is FastAPI?"
        
        # First call
        context1, citations1 = retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # Second call (should use cache)
        context2, citations2 = retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # Results should be identical
        assert context1 == context2
        assert citations1 == citations2
    
    def test_cache_clear(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that cache can be cleared."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is Python?"
        
        # Populate cache
        retriever.assemble_context(query=query, top_k=3, max_context_chars=2000, db_session=db_session)
        
        # Clear cache
        retriever.clear_cache()
        
        # Cache should be empty (results will be recomputed)
        # We can't directly test cache state, but we can verify it works after clear
        context, citations = retriever.assemble_context(
            query=query, top_k=3, max_context_chars=2000, db_session=db_session
        )
        assert len(context) > 0


class TestExtractiveSummarization:
    """Test extractive summarization fallback."""
    
    def test_extract_top_sentences(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test extractive summarization for long chunks."""
        long_text = (
            "This is the first sentence. "
            "This is the second sentence. "
            "This is the third sentence. "
            "This is the fourth sentence. "
            "This is the fifth sentence."
        )
        
        # Extract to fit 50 chars
        result = extract_top_sentences(long_text, max_chars=50)
        
        assert len(result) <= 50
        assert "first sentence" in result
        # Should include complete sentences
    
    def test_extract_top_sentences_no_truncation_needed(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that short text is not truncated."""
        short_text = "This is a short text."
        result = extract_top_sentences(short_text, max_chars=100)
        
        assert result == short_text


class TestGroundingAndSafety:
    """Test grounding ratio and safety (no fabricated citations)."""
    
    def test_citations_match_retrieved_chunks(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that citations match actual retrieved chunks."""
        document, chunks = indexed_document
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is Python?"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # Verify citations reference actual chunks
        chunk_ids = {c["chunk_id"] for c in citations}
        actual_chunk_ids = {chunk.chunk_id for chunk in chunks}
        
        # All cited chunks should exist
        assert chunk_ids.issubset(actual_chunk_ids)
    
    def test_no_fabricated_citations(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that citations are not fabricated."""
        document, chunks = indexed_document
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is Python?"
        context, citations = retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        
        # All citations should reference the correct document
        for citation in citations:
            assert citation["doc_id"] == str(document.doc_id)
            # Chunk ID should be valid
            assert 0 <= citation["chunk_id"] < len(chunks)
    
    def test_deterministic_formatting(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that formatting is stable across calls."""
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is RAG?"
        
        # Multiple calls should produce identical formatting
        contexts = []
        for _ in range(3):
            context, _ = retriever.assemble_context(
                query=query,
                top_k=3,
                max_context_chars=2000,
                db_session=db_session,
            )
            contexts.append(context)
        
        # All contexts should be identical (after first call uses cache)
        assert contexts[0] == contexts[1] == contexts[2]


class TestPerformanceMetrics:
    """Test performance metrics tracking."""
    
    def test_retrieval_latency_tracked(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that retrieval latency is reasonable."""
        import time
        
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is Python?"
        start = time.time()
        retriever.retrieve_chunks(query, top_k=3, db_session=db_session)
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 5 seconds for test)
        assert elapsed < 5.0
    
    def test_context_assembly_time_tracked(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that context assembly completes in reasonable time."""
        import time
        
        retriever = QueryRetriever(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        query = "What is FastAPI?"
        start = time.time()
        retriever.assemble_context(
            query=query,
            top_k=3,
            max_context_chars=2000,
            db_session=db_session,
        )
        elapsed = time.time() - start
        
        # Should complete quickly (< 5 seconds)
        assert elapsed < 5.0


class TestLLMIntegration:
    """Test LLM integration."""
    
    def test_llm_provider_generates_response(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that LLM provider generates structured response."""
        llm = get_llm_provider()
        
        system_prompt = "You are a helpful assistant."
        context = "[CONTEXT SOURCES]\n--- SOURCE 1 ---\n[DOC: test | CHUNK: 0]\nPython is a language.\n\n[USER QUESTION]\nWhat is Python?"
        user_question = "What is Python?"
        
        result = llm.generate(
            system_prompt=system_prompt,
            context=context,
            user_question=user_question,
        )
        
        assert "answer" in result
        assert "citations" in result
        assert "tokens_used" in result
        assert "model" in result
        assert len(result["answer"]) > 0
    
    def test_llm_extracts_citations(
        self, temp_chroma_dir, db_session, indexed_document
    ):
        """Test that LLM extracts citations from context."""
        llm = PlaceholderLLM()
        
        context = (
            "[CONTEXT SOURCES]\n"
            "--- SOURCE 1 ---\n"
            "[DOC: doc123 | CHUNK: 0]\n"
            "Python is a language.\n\n"
            "[USER QUESTION]\n"
            "What is Python?"
        )
        
        result = llm.generate(
            system_prompt="Test",
            context=context,
            user_question="What is Python?",
        )
        
        # Placeholder should extract citations
        assert len(result["citations"]) > 0

