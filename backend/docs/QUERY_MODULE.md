# RAG Query Module

## Overview

The RAG Query Module is a core component that retrieves the K most relevant chunks from the vector database and assembles a deterministic, compact, properly tagged context that maximizes grounding and minimizes token waste.

## Architecture

### Components

1. **QueryRetriever** (`app/core/query.py`)
   - Generates query embeddings using the same model as ingestion
   - Queries ChromaDB vector database for top_k ranked chunks
   - Assembles structured context with proper citation tags
   - Implements LRU caching for query results and assembled contexts
   - Provides extractive summarization fallback for long chunks

2. **LLM Provider Interface** (`app/core/llm.py`)
   - Flexible interface for cloud provider integrations
   - Placeholder implementation included
   - Ready for OpenAI, Anthropic, or other providers

3. **API Endpoint** (`POST /api/query`)
   - Accepts query with optional top_k and max_context_chars
   - Returns grounded answer with citations and metrics
   - Includes cache management endpoint

## Usage

### API Endpoint

```bash
POST /api/query
```

**Request:**
```json
{
  "q": "What is Python?",
  "top_k": 6,
  "max_context_chars": 4000
}
```

**Response:**
```json
{
  "answer": "[🔹 Summary]\n...\n[🔹 Detailed Analysis]\n...\n[🔹 Final Answer]\n...",
  "citations": [
    {
      "doc_id": "uuid",
      "chunk_id": 0,
      "page": 1,
      "similarity": 0.85
    }
  ],
  "sources": [...],
  "metrics": {
    "retrieval_latency_ms": 123.45,
    "llm_latency_ms": 456.78,
    "total_latency_ms": 580.23,
    "context_length": 3500,
    "chunks_retrieved": 5,
    "tokens_used": {...},
    "model": "placeholder"
  },
  "query_id": "uuid"
}
```

### Python API

```python
from app.core.query import QueryRetriever
from app.core.llm import get_llm_provider

# Initialize retriever
retriever = QueryRetriever()

# Assemble context
context, citations = retriever.assemble_context(
    query="What is Python?",
    top_k=6,
    max_context_chars=4000,
    db_session=db_session,
)

# Generate answer with LLM
llm = get_llm_provider()
result = llm.generate(
    system_prompt="You are a helpful assistant...",
    context=context,
    user_question="What is Python?",
)
```

## Context Format

The assembled context follows a strict format:

```
[SYSTEM CONTEXT RULES]
Use only the information provided below.
Cite evidence using [DOC:doc_id | CHUNK:chunk_id].

[CONTEXT SOURCES]
--- SOURCE 1 ---
[DOC: doc_id | CHUNK: chunk_id | PAGE: page_number]

<chunk text>

--- SOURCE 2 ---
[DOC: doc_id | CHUNK: chunk_id | PAGE: page_number]

<chunk text>

[USER QUESTION]
<original_query>
```

## Features

### 1. Query Handling

- **Embedding Generation**: Uses the same embedding model (`all-MiniLM-L6-v2`) as ingestion
- **Vector DB Query**: Queries ChromaDB collection with similarity search
- **Metadata Preservation**: Each chunk includes doc_id, chunk_id, page_number, and similarity score

### 2. Context Construction

- **Deterministic Formatting**: Consistent structure across calls
- **Character Limit**: Respects `max_context_chars` by:
  1. Omitting lowest-ranked chunks if limit exceeded
  2. Using extractive summarization (top sentences) for long chunks
  3. Hard truncation as final fallback
- **Citation Tags**: Proper `[DOC:X | CHUNK:Y]` format for grounding

### 3. Caching

- **LRU Cache**: Lightweight caching of:
  - Query → retrieved chunks
  - Query → assembled context
- **Cache Size**: Configurable (default: 128 entries)
- **Cache Management**: Clear cache via `/api/query/clear-cache`

### 4. Performance Metrics

- **Retrieval Latency**: Time to query vector DB
- **Context Assembly Time**: Time to assemble context
- **LLM Latency**: Time for LLM generation
- **Token Usage**: Prompt and completion tokens
- **Total Latency**: End-to-end query time

## Testing

Comprehensive tests are available in `tests/test_query.py`:

- **Retrieval Correctness**: Validates retrieved chunks match expected sources
- **Grounding Ratio**: Ensures answers contain valid citations
- **Performance Metrics**: Tracks retrieval and assembly latency
- **Safety**: No fabricated citations, no non-existing documents
- **Determinism**: Stable formatting across calls
- **Caching**: Validates cache hits and eviction

Run tests:
```bash
pytest tests/test_query.py -v
```

## LLM Integration

The module includes a placeholder LLM provider that can be replaced with actual cloud provider integrations:

### Current Implementation

- `PlaceholderLLM`: Returns structured response without actual LLM call
- Extracts citations from context
- Provides token usage estimates

### Extending for Real Providers

To integrate OpenAI:
```python
class OpenAIProvider(LLMProvider):
    def generate(self, system_prompt, context, user_question, **kwargs):
        import openai
        # Implement OpenAI API call
        ...
```

To integrate Anthropic:
```python
class AnthropicProvider(LLMProvider):
    def generate(self, system_prompt, context, user_question, **kwargs):
        import anthropic
        # Implement Anthropic API call
        ...
```

Set provider via environment variable:
```bash
export LLM_PROVIDER=openai  # or anthropic, etc.
```

## Configuration

### QueryRetriever Parameters

- `model_name`: Embedding model (default: "all-MiniLM-L6-v2")
- `collection_name`: ChromaDB collection (default: "documents")
- `cache_size`: LRU cache size (default: 128)

### Default Values

- `top_k`: 6 chunks
- `max_context_chars`: 4000 characters

## Safety & Determinism

### Guarantees

1. **No Fabricated Citations**: All citations reference actual retrieved chunks
2. **No Non-Existing Documents**: Citations validated against database
3. **Stable Formatting**: Consistent context structure across calls
4. **Deterministic Ordering**: Chunks sorted by similarity (descending)

### Validation

- Citations match retrieved chunk metadata
- Document IDs validated against database
- Chunk IDs within valid range
- Similarity scores normalized (0-1)

## Performance Considerations

### Optimization

- **Caching**: Reduces repeated embedding computation and vector DB queries
- **Batch Processing**: Embeddings generated efficiently
- **Character Limits**: Prevents token waste with truncation

### Monitoring

Key metrics to monitor:
- Retrieval latency (target: < 500ms)
- Context assembly time (target: < 100ms)
- LLM latency (depends on provider)
- Cache hit rate
- Token usage per request

## Integration

The query module integrates seamlessly with:

- **Ingestion Pipeline**: Uses same embedding model and collection
- **Database Models**: Works with Document and Chunk models
- **ChromaDB**: Uses existing ChromaDB client configuration
- **API Routes**: Registered in FastAPI router

## Example Workflow

1. **User Query**: `POST /api/query` with `{"q": "What is Python?", "top_k": 6}`
2. **Embedding**: Query embedded using `all-MiniLM-L6-v2`
3. **Retrieval**: Top 6 chunks retrieved from ChromaDB
4. **Context Assembly**: Chunks formatted with citations
5. **LLM Generation**: Context sent to LLM with system prompt
6. **Response**: Answer with citations and metrics returned

## Troubleshooting

### No Results Returned

- Check if documents are indexed: `POST /api/ingest/index?doc_id=<uuid>`
- Verify ChromaDB collection has embeddings
- Check query relevance to indexed content

### High Latency

- Check cache hit rate
- Monitor vector DB query performance
- Consider reducing `top_k` or `max_context_chars`

### Citation Issues

- Verify chunk metadata in ChromaDB
- Check document IDs match database
- Ensure citations reference actual chunks

