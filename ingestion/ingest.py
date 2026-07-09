"""
ingestion/ingest.py — Orchestrator for Phase 2: Data Ingestion.

End-to-End Pipeline:
1. Scrape URLs -> ScrapedPage objects (scraper.py)
2. Clean text -> (cleaner.py, implicit in scraper)
3. Extract metadata -> (extractor.py, implicit in scraper)
4. Chunk text -> Chunk objects (chunker.py)
5. Embed chunks -> np.ndarray (embedder.py)
6. Build + save index -> index.faiss + metadata.json (vector_store.py)
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingestion.scraper import scrape_all_funds
from ingestion.chunker import chunk_page, Chunk
from ingestion.embedder import embed_chunks
from ingestion.vector_store import build_and_save_index

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

def run_ingestion():
    logger.info("=== Starting Data Ingestion Pipeline ===")
    
    # 1. Scrape
    logger.info("Step 1/4: Scraping Groww URLs...")
    scrape_result = scrape_all_funds()
    
    if scrape_result.failure_count > 0:
        logger.warning(f"  [!] Failed to scrape {scrape_result.failure_count} funds.")
        for f in scrape_result.failures:
            logger.warning(f"      - {f['fund_name']}: {f['reason']}")
            
    if scrape_result.success_count == 0:
        logger.error("  [X] All scrapes failed. Aborting pipeline.")
        sys.exit(1)
        
    logger.info(f"  [OK] Successfully scraped {scrape_result.success_count} funds.")
    
    # 2. Chunk
    logger.info("\nStep 2/4: Chunking text...")
    all_chunks: list[Chunk] = []
    for page in scrape_result.pages:
        chunks = chunk_page(page)
        all_chunks.extend(chunks)
        
    logger.info(f"  [OK] Total chunks generated: {len(all_chunks)}")
    
    if len(all_chunks) == 0:
        logger.error("  [X] No chunks generated. Aborting pipeline.")
        sys.exit(1)
        
    # 3. Embed
    logger.info("\nStep 3/4: Embedding chunks...")
    embeddings = embed_chunks(all_chunks)
    logger.info(f"  [OK] Embeddings generated: {embeddings.shape}")
    
    # 4. Vector Store
    logger.info("\nStep 4/4: Building FAISS index...")
    try:
        stats = build_and_save_index(all_chunks, embeddings)
        logger.info(f"  [OK] FAISS index saved successfully.")
        logger.info(f"       Index:    {stats['index_path']}")
        logger.info(f"       Metadata: {stats['metadata_path']}")
        logger.info(f"       Chunks:   {stats['num_chunks']}")
    except Exception as e:
        logger.error(f"  [X] Failed to build vector store: {e}")
        sys.exit(1)
        
    logger.info("\n=== Data Ingestion Complete! ===")

if __name__ == "__main__":
    run_ingestion()
