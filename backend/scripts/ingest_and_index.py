#!/usr/bin/env python3
"""Offline script for indexing embeddings for documents.

This script can be run independently of the API to generate and persist
embeddings for documents already chunkified and stored in the database.

Usage:
    python scripts/ingest_and_index.py [--doc-id DOC_ID] [--all] [--skip-existing]
"""
import sys
import os
import argparse
import logging
import uuid
from typing import List, Optional

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.db.models import Document, DocumentStatus
from app.core.indexing import EmbeddingIndexer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger(__name__)


def get_pending_documents(db: Session) -> List[Document]:
    """Get documents that have chunks but may not be indexed."""
    return (
        db.query(Document)
        .filter(
            Document.status == DocumentStatus.INDEXED,
            Document.total_chunks > 0,
        )
        .all()
    )


def index_document(
    db: Session,
    indexer: EmbeddingIndexer,
    doc_id: uuid.UUID,
    skip_existing: bool = True,
) -> dict:
    """Index a single document."""
    logger.info(f"Indexing document {doc_id}")
    try:
        result = indexer.index_document_chunks(
            db=db,
            doc_id=doc_id,
            skip_existing=skip_existing,
        )
        logger.info(
            f"✓ Document {doc_id}: {result['chunks_indexed']}/{result['total_chunks']} "
            f"chunks indexed in {result['total_time_seconds']:.2f}s"
        )
        return result
    except Exception as e:
        logger.error(f"✗ Error indexing document {doc_id}: {e}", exc_info=True)
        return {
            "doc_id": str(doc_id),
            "error": str(e),
            "chunks_indexed": 0,
        }


def main():
    """Main entry point for the indexing script."""
    parser = argparse.ArgumentParser(
        description="Index embeddings for documents already stored in the database"
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        help="Specific document ID to index (UUID)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Index all documents with chunks",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip chunks already indexed in ChromaDB (default: True)",
    )
    parser.add_argument(
        "--no-skip-existing",
        dest="skip_existing",
        action="store_false",
        help="Re-index all chunks even if already indexed",
    )
    
    args = parser.parse_args()
    
    if not args.doc_id and not args.all:
        parser.error("Either --doc-id or --all must be specified")
    
    # Initialize indexer
    logger.info("Initializing embedding indexer...")
    indexer = EmbeddingIndexer()
    
    # Create database session
    db: Session = SessionLocal()
    
    try:
        documents_to_index = []
        
        if args.doc_id:
            # Index specific document
            try:
                doc_uuid = uuid.UUID(args.doc_id)
            except ValueError:
                logger.error(f"Invalid document ID format: {args.doc_id}")
                sys.exit(1)
            
            document = db.query(Document).filter(Document.doc_id == doc_uuid).first()
            if not document:
                logger.error(f"Document {args.doc_id} not found")
                sys.exit(1)
            
            if document.total_chunks == 0:
                logger.warning(f"Document {args.doc_id} has no chunks to index")
                sys.exit(0)
            
            documents_to_index = [document]
            
        elif args.all:
            # Get all documents with chunks
            documents_to_index = get_pending_documents(db)
            logger.info(f"Found {len(documents_to_index)} documents to index")
        
        if not documents_to_index:
            logger.info("No documents to index")
            return
        
        # Index each document
        total_indexed = 0
        total_chunks = 0
        errors = []
        
        for i, document in enumerate(documents_to_index, 1):
            logger.info(f"\n[{i}/{len(documents_to_index)}] Processing document: {document.filename}")
            
            result = index_document(
                db=db,
                indexer=indexer,
                doc_id=document.doc_id,
                skip_existing=args.skip_existing,
            )
            
            if "error" in result:
                errors.append({
                    "doc_id": str(document.doc_id),
                    "filename": document.filename,
                    "error": result["error"],
                })
            else:
                total_indexed += result.get("chunks_indexed", 0)
                total_chunks += result.get("total_chunks", 0)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("INDEXING SUMMARY")
        logger.info("="*60)
        logger.info(f"Documents processed: {len(documents_to_index)}")
        logger.info(f"Chunks indexed: {total_indexed}/{total_chunks}")
        logger.info(f"Collection size: {indexer._get_collection_size()}")
        
        if errors:
            logger.warning(f"\nErrors encountered: {len(errors)}")
            for error in errors:
                logger.warning(f"  - {error['filename']} ({error['doc_id']}): {error['error']}")
        
        logger.info("="*60)
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()

