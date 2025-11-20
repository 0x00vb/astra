# Document Ingestion Pipeline

## Overview

A robust, metadata-preserving document ingestion pipeline that extracts text from PDF, DOCX, TXT, and HTML files, cleans and normalizes the content, chunks it for embedding, and stores both metadata and embeddings.

## Architecture

### Components

1. **Parsers** (`app/core/parsers/`)
   - `PDFParser`: Extracts text and metadata from PDFs using pypdf
   - `DOCXParser`: Extracts text from Word documents using python-docx
   - `TXTParser`: Handles plain text files with encoding detection
   - `HTMLParser`: Extracts text content from HTML using BeautifulSoup

2. **Text Processing** (`app/core/text_utils.py`)
   - Removes repeated headers/footers
   - Normalizes whitespace and line endings
   - Cleans control characters

3. **Chunking** (`app/core/chunking.py`)
   - Creates overlapping chunks (default: 800 chars, 160 char overlap)
   - Preserves page numbers and character offsets
   - Configurable chunk sizes (min: 100, max: 1500 chars)

4. **Embeddings** (`app/core/embeddings.py`)
   - Uses SentenceTransformers (all-MiniLM-L6-v2 by default)
   - Batch processing for efficiency
   - GPU support when available

5. **Storage**
   - **PostgreSQL**: Document and chunk metadata
   - **ChromaDB**: Vector embeddings with metadata

## Data Model

### Documents Table
- `doc_id` (UUID): Primary key
- `filename`: Original filename
- `file_type`: pdf, docx, txt, html
- `file_size`: Size in bytes
- `uploaded_at`: Timestamp
- `owner`: For future auth integration
- `status`: pending, processing, indexed, error
- `total_pages`: Number of pages (if available)
- `total_chunks`: Number of chunks created
- `total_characters`: Total character count

### Chunks Table
- `id` (UUID): Primary key
- `doc_id`: Foreign key to documents
- `chunk_id`: Sequential chunk number
- `start_char`, `end_char`: Character offsets
- `page_number`: Page number (if available)
- `text`: Chunk text content
- `token_count`: Estimated token count

## API Endpoints

### POST `/api/ingest/upload`
Upload and ingest a document.

**Request:**
- `file`: Multipart file upload (PDF, DOCX, TXT, HTML)
- Max file size: 50MB

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "indexed",
  "stats": {
    "chunks": 42,
    "pages": 10,
    "characters": 35000
  }
}
```

### GET `/api/ingest/documents`
List all documents.

**Response:**
```json
[
  {
    "id": "uuid",
    "filename": "document.pdf",
    "file_type": "pdf",
    "file_size": 1024000,
    "status": "indexed",
    "chunks_count": 42,
    "total_pages": 10,
    "created_at": "2024-01-01T00:00:00"
  }
]
```

### GET `/api/ingest/progress/{document_id}`
Get indexing progress for a document.

**Response:**
```json
{
  "document_id": "uuid",
  "progress": 100,
  "status": "indexed",
  "chunks_processed": 42,
  "total_chunks": 42
}
```

### GET `/api/ingest/document/{document_id}/content`
Get document content and metadata.

### DELETE `/api/ingest/document/{document_id}`
Delete a document and all its chunks/embeddings.

## Usage

### Initialize Database

```bash
# Using Alembic (recommended)
cd backend
alembic upgrade head

# Or using init script
python -m app.db.init_db
```

### Run the Server

```bash
cd backend
python run.py
```

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/ingest/upload" \
  -F "file=@document.pdf"
```

## Configuration

### Chunking Parameters

Default values can be adjusted in `DocumentIngestionPipeline.ingest_document()`:
- `chunk_size`: 800 characters (target)
- `chunk_overlap`: 160 characters (20% overlap)
- `min_chunk_size`: 100 characters
- `max_chunk_size`: 1500 characters

### Embedding Model

Change the model in `app/core/embeddings.py`:
```python
EmbeddingGenerator(model_name="all-MiniLM-L6-v2")
```

Popular alternatives:
- `all-mpnet-base-v2`: Better quality, slower
- `paraphrase-multilingual-MiniLM-L12-v2`: Multilingual support

## Error Handling

- Parser failures are logged with detailed error messages
- Failed documents are marked with `status="error"` and `error_message`
- ChromaDB failures don't prevent database storage (embeddings can be regenerated)
- File size validation (50MB max)
- File type validation

## Performance Considerations

- PDF parsing can be memory-intensive for large files
- Embedding generation uses batch processing (32 chunks at a time)
- ChromaDB persists to disk (`./chroma_db` by default)
- Database connections use connection pooling

## Frontend Integration

The frontend (`DocumentManager.tsx`) is already configured to:
- Upload files via drag-and-drop or file picker
- Display upload progress
- Poll for indexing progress
- Show document status and metadata

## Future Enhancements

- Authentication/authorization (owner field ready)
- Async processing with background tasks
- Support for more file types (ODT, RTF, etc.)
- OCR for scanned PDFs
- Incremental updates (re-indexing changed documents)
- Chunk deduplication
- Custom chunking strategies (semantic, sentence-based)

