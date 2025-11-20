# Embedding Indexing Module

## Overview

This module provides a robust pipeline for generating and persisting embeddings for chunks already stored in the database. It enables semantic retrieval over ingested documents with efficient CPU-based processing, comprehensive metrics tracking, and OOM handling.

## Architecture

### Components

1. **EmbeddingIndexer** (`app/core/indexing.py`)
   - Generates embeddings for chunks in batches
   - Handles OOM by adaptively reducing batch size
   - Tracks comprehensive metrics (time, memory, errors)
   - Persists embeddings to ChromaDB with complete metadata

2. **API Endpoint** (`/api/ingest/index`)
   - POST endpoint to index a specific document
   - Returns indexing summary with metrics

3. **Offline Script** (`scripts/ingest_and_index.py`)
   - Can be run independently of the API
   - Supports indexing single documents or all documents
   - Provides detailed logging and summary

## Configuration

### Model
- **Model**: `all-MiniLM-L6-v2` (SentenceTransformers)
- **Device**: CPU (forced for consistency)
- **Normalization**: Enabled (for cosine similarity)

### Batch Processing
- **Initial batch size**: 6 chunks
- **Adaptive range**: 2-8 chunks
- **OOM handling**: Automatically reduces batch size on memory errors

### Chunk Configuration
- **Expected chunk size**: 1200-1800 characters (configurable in ingestion)
- **Expected overlap**: 150-300 characters (configurable in ingestion)

### Vector Database
- **Collection**: `documents` (configurable)
- **Persistence**: ChromaDB persistent storage
- **Location**: Configured via `CHROMA_PERSIST_DIR` environment variable

## Usage

### API Endpoint

```bash
POST /api/ingest/index?doc_id=<uuid>&skip_existing=true
```

**Parameters:**
- `doc_id` (required): Document UUID to index
- `skip_existing` (optional, default: true): Skip chunks already indexed

**Response:**
```json
{
  "doc_id": "uuid",
  "chunks_indexed": 42,
  "total_chunks": 42,
  "total_time_seconds": 12.34,
  "collection_size": 150,
  "metrics": {
    "batches_processed": 7,
    "embedding_time_seconds": 10.5,
    "persistence_time_seconds": 1.2,
    "peak_memory_mb": 512.3,
    "errors": [],
    "avg_batch_time_seconds": 1.76
  }
}
```

### Offline Script

```bash
# Index a specific document
python scripts/ingest_and_index.py --doc-id <uuid>

# Index all documents
python scripts/ingest_and_index.py --all

# Re-index all chunks (even if already indexed)
python scripts/ingest_and_index.py --all --no-skip-existing
```

## Features

### Batch Processing with OOM Handling
- Processes chunks in configurable batches
- Automatically reduces batch size on memory errors
- Continues processing even if individual batches fail

### Comprehensive Metrics
- Total processing time
- Embedding generation time
- Persistence time
- Peak memory usage
- Batch processing times
- Error tracking

### Metadata Preservation
Each embedding includes:
- `doc_id`: Document UUID
- `chunk_id`: Sequential chunk number
- `chunk_uuid`: Chunk database UUID
- `start_char`: Character offset start
- `end_char`: Character offset end
- `page_number`: Page number (if available)
- `hash`: SHA256 hash of chunk text (first 16 chars)

### Duplicate Prevention
- Checks existing embeddings before indexing
- Skips already-indexed chunks by default
- Prevents duplicate IDs in collection

## Testing

Functional tests are available in `tests/test_indexing.py`:

- **Semantic Retrieval**: Validates that queries return semantically relevant chunks
- **Geometric Coherence**: Tests L2 and cosine distances between embeddings
- **Persistence**: Verifies collection stability across restarts
- **Duplicate Detection**: Ensures no duplicate IDs in collection

Run tests:
```bash
pytest tests/test_indexing.py -v
```

## Monitoring Points

The following metrics should be monitored:

1. **Latency per chunk** (ms): `embedding_time_seconds / chunks_indexed * 1000`
2. **Latency per batch**: Available in `metrics.avg_batch_time_seconds`
3. **RAM peak**: Available in `metrics.peak_memory_mb`
4. **Collection size**: Available in response `collection_size`
5. **Duplicate detection**: Check collection IDs for duplicates

## Integration

The indexing module integrates seamlessly with the existing architecture:

- Uses existing database models (`Document`, `Chunk`)
- Reuses ChromaDB client configuration
- Follows project logging standards
- Maintains error handling patterns
- Compatible with existing ingestion pipeline

## Example Workflow

1. **Ingest document**: `POST /api/ingest/upload`
2. **Index embeddings**: `POST /api/ingest/index?doc_id=<uuid>`
3. **Query semantically**: Use ChromaDB collection.query() with embeddings

## Troubleshooting

### OOM Errors
- Batch size will automatically reduce
- If minimum batch size fails, check available RAM
- Consider reducing initial batch size in configuration

### Slow Performance
- Check batch processing times in metrics
- Verify CPU usage (should be high during embedding generation)
- Consider adjusting batch size based on available resources

### Collection Size Issues
- Monitor collection size growth
- Check for duplicate IDs
- Verify persistence directory has sufficient space

