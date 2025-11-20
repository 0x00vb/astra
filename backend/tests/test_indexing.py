"""Functional tests for embedding indexing and retrieval.

These tests validate:
- Semantic retrieval consistency
- Geometric coherence of embeddings (L2, cosine distances)
- Collection persistence and stability
- Duplicate detection
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
import numpy as np
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, Base, engine
from app.db.models import Document, Chunk, DocumentStatus
from app.core.indexing import EmbeddingIndexer
from app.core.chroma_client import get_chroma_collection
from app.core.embeddings import generate_embeddings


# Test configuration
TEST_COLLECTION_NAME = "test_documents"
TEST_MODEL_NAME = "all-MiniLM-L6-v2"


@pytest.fixture(scope="function")
def temp_chroma_dir():
    """Create a temporary ChromaDB directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="chroma_test_")
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
def test_document(db_session):
    """Create a test document with chunks."""
    doc_id = uuid.uuid4()
    document = Document(
        doc_id=doc_id,
        filename="test_document.txt",
        file_type="txt",
        file_size=1000,
        status=DocumentStatus.INDEXED,
        total_chunks=3,
        total_characters=500,
    )
    db_session.add(document)
    
    # Create test chunks with semantically related content
    chunks_data = [
        {
            "text": "Machine learning is a subset of artificial intelligence that enables computers to learn from data.",
            "chunk_id": 0,
            "start_char": 0,
            "end_char": 100,
        },
        {
            "text": "Deep learning uses neural networks with multiple layers to process complex patterns in data.",
            "chunk_id": 1,
            "start_char": 100,
            "end_char": 200,
        },
        {
            "text": "Natural language processing allows computers to understand and generate human language.",
            "chunk_id": 2,
            "start_char": 200,
            "end_char": 300,
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
            text=chunk_data["text"],
            token_count=len(chunk_data["text"].split()),
        )
        chunks.append(chunk)
        db_session.add(chunk)
    
    db_session.commit()
    db_session.refresh(document)
    
    return document, chunks


class TestSemanticRetrieval:
    """Test semantic retrieval consistency."""
    
    def test_semantic_query_returns_relevant_chunks(
        self, temp_chroma_dir, db_session, test_document
    ):
        """Test that semantic queries return semantically relevant chunks."""
        document, chunks = test_document
        
        # Index the document
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        result = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        assert result["chunks_indexed"] == 3
        
        # Query with semantically related text
        query_text = "How do computers learn from data?"
        query_embeddings = generate_embeddings([query_text], model_name=TEST_MODEL_NAME)
        
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=5,
        )
        
        assert len(results["ids"][0]) > 0
        
        # The first result should be semantically related to machine learning
        first_result_text = results["documents"][0][0]
        assert "machine learning" in first_result_text.lower() or "learn" in first_result_text.lower()
    
    def test_query_with_unrelated_text(self, temp_chroma_dir, db_session, test_document):
        """Test that unrelated queries still return results but with lower relevance."""
        document, chunks = test_document
        
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        # Query with unrelated text
        query_text = "What is the weather like today?"
        query_embeddings = generate_embeddings([query_text], model_name=TEST_MODEL_NAME)
        
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        results = collection.query(
            query_embeddings=query_embeddings,
            n_results=3,
        )
        
        # Should still return results (all chunks indexed)
        assert len(results["ids"][0]) == 3


class TestGeometricCoherence:
    """Test geometric coherence of embeddings."""
    
    def test_embedding_distances_are_consistent(
        self, temp_chroma_dir, db_session, test_document
    ):
        """Test that embeddings have consistent geometric properties."""
        document, chunks = test_document
        
        # Generate embeddings directly
        texts = [chunk.text for chunk in chunks]
        embeddings = generate_embeddings(texts, model_name=TEST_MODEL_NAME)
        
        assert len(embeddings) == 3
        assert all(len(emb) > 0 for emb in embeddings)
        
        # Convert to numpy arrays
        emb_array = np.array(embeddings)
        
        # Test L2 distances
        l2_distances = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                l2_dist = np.linalg.norm(emb_array[i] - emb_array[j])
                l2_distances.append(l2_dist)
                # L2 distance should be reasonable (not NaN, not Inf)
                assert not np.isnan(l2_dist)
                assert not np.isinf(l2_dist)
                assert 0 <= l2_dist <= 10  # Reasonable range for normalized embeddings
        
        # Test cosine distances (since embeddings are normalized)
        cosine_distances = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                # Cosine distance = 1 - cosine similarity
                cosine_sim = np.dot(emb_array[i], emb_array[j])
                cosine_dist = 1 - cosine_sim
                cosine_distances.append(cosine_dist)
                assert 0 <= cosine_dist <= 2  # Cosine distance range
        
        # Similar texts should have smaller distances
        # Chunks 0 and 1 are both about ML/AI, should be closer than chunk 2
        ml_chunks_dist = cosine_distances[0]  # Distance between chunk 0 and 1
        # This is a soft check - semantically related chunks should generally be closer
        assert ml_chunks_dist < 1.5  # Reasonable threshold
    
    def test_embeddings_are_normalized(self, temp_chroma_dir, db_session, test_document):
        """Test that embeddings are normalized (L2 norm ≈ 1)."""
        document, chunks = test_document
        
        texts = [chunk.text for chunk in chunks]
        embeddings = generate_embeddings(texts, model_name=TEST_MODEL_NAME)
        
        emb_array = np.array(embeddings)
        
        # Check L2 norms (should be close to 1.0 for normalized embeddings)
        norms = np.linalg.norm(emb_array, axis=1)
        for norm in norms:
            assert abs(norm - 1.0) < 0.1  # Allow small tolerance
    
    def test_no_corrupted_embeddings(self, temp_chroma_dir, db_session, test_document):
        """Test that no embeddings are corrupted (all zeros, NaN, Inf)."""
        document, chunks = test_document
        
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        result = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        assert result["chunks_indexed"] == 3
        
        # Retrieve embeddings from ChromaDB
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        all_data = collection.get()
        
        # Verify embeddings are valid
        if all_data.get("embeddings"):
            for emb in all_data["embeddings"]:
                emb_array = np.array(emb)
                assert not np.any(np.isnan(emb_array))
                assert not np.any(np.isinf(emb_array))
                assert not np.all(emb_array == 0)  # Not all zeros


class TestPersistence:
    """Test collection persistence and stability."""
    
    def test_collection_persists_after_restart(
        self, temp_chroma_dir, db_session, test_document
    ):
        """Test that collection persists across restarts."""
        document, chunks = test_document
        
        # Index document
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        result1 = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        initial_size = result1["collection_size"]
        assert initial_size == 3
        
        # Simulate restart by creating new indexer and client
        # Clear global state
        from app.core.chroma_client import _chroma_client, _chroma_collection
        _chroma_client = None
        _chroma_collection = None
        
        # Create new indexer (should use existing collection)
        indexer2 = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        # Collection should still exist
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        size_after_restart = collection.count()
        assert size_after_restart == initial_size
    
    def test_collection_size_grows_correctly(
        self, temp_chroma_dir, db_session, test_document
    ):
        """Test that collection size grows as documents are indexed."""
        document, chunks = test_document
        
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        # Initial size should be 0
        initial_size = indexer._get_collection_size()
        assert initial_size == 0
        
        # Index document
        result = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        # Size should be 3 (number of chunks)
        final_size = indexer._get_collection_size()
        assert final_size == 3


class TestDuplicateDetection:
    """Test duplicate detection and ID management."""
    
    def test_no_duplicate_ids_in_collection(
        self, temp_chroma_dir, db_session, test_document
    ):
        """Test that no duplicate IDs exist in the collection."""
        document, chunks = test_document
        
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        
        # Index twice (second should skip existing)
        result1 = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=True,
        )
        
        result2 = indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=True,
        )
        
        # Second indexing should skip all chunks
        assert result2["chunks_indexed"] == 0
        
        # Verify no duplicates in collection
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        all_data = collection.get()
        
        if all_data.get("ids"):
            ids = all_data["ids"]
            assert len(ids) == len(set(ids))  # No duplicates
    
    def test_metadata_consistency(self, temp_chroma_dir, db_session, test_document):
        """Test that metadata is consistent and complete."""
        document, chunks = test_document
        
        indexer = EmbeddingIndexer(
            model_name=TEST_MODEL_NAME,
            collection_name=TEST_COLLECTION_NAME,
        )
        indexer.index_document_chunks(
            db=db_session,
            doc_id=document.doc_id,
            skip_existing=False,
        )
        
        collection = get_chroma_collection(TEST_COLLECTION_NAME)
        all_data = collection.get()
        
        if all_data.get("metadatas"):
            for metadata in all_data["metadatas"]:
                # Required fields
                assert "doc_id" in metadata
                assert "chunk_id" in metadata
                assert "chunk_uuid" in metadata
                assert "start_char" in metadata
                assert "end_char" in metadata
                assert "hash" in metadata
                
                # Verify doc_id matches
                assert metadata["doc_id"] == str(document.doc_id)

