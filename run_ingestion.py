#!/usr/bin/env python3
"""
Phase 1: Data Ingestion
Downloads real SEC 10-K filings and builds vector store
"""

import sys
import os
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent.resolve()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.sec_downloader import SECDownloader
from core.document_processor import DocumentProcessor
from core.vector_store import FAISSVectorStore
import time


def run_ingestion():
    """Run complete data ingestion pipeline"""
    print("=" * 60)
    print("PHASE 1: DATA INGESTION")
    print("=" * 60)
    print("Downloading real SEC 10-K filings and building vector store...")
    print()

    # Configuration
    companies = ['GOOGL', 'MSFT', 'NVDA']
    years = ['2022', '2023', '2024']

    start_time = time.time()

    # Step 1: Download SEC filings
    print("Step 1: Downloading SEC 10-K filings")
    print("-" * 40)
    downloader = SECDownloader()

    total_files = 0
    for company in companies:
        print(f"Downloading {company} filings...")
        try:
            files = downloader.download_company_filings(company, years)
            total_files += len(files)
            print(f"  Downloaded {len(files)} files for {company}")

            # Show file details
            for file_path in files:
                if os.path.exists(file_path):
                    size_kb = os.path.getsize(file_path) / 1024
                    filename = os.path.basename(file_path)
                    print(f"    - {filename} ({size_kb:.1f} KB)")

        except Exception as e:
            print(f"  Error downloading {company}: {e}")

    print(f"\nDownload Summary: {total_files} files downloaded")
    print()

    # Step 2: Process documents and build vector store
    print("Step 2: Processing documents and building vector store")
    print("-" * 50)

    processor = DocumentProcessor()
    vector_store = FAISSVectorStore()

    total_chunks = 0
    processed_files = 0

    data_dir = 'data/filings'

    for company in companies:
        company_dir = os.path.join(data_dir, company)
        if os.path.exists(company_dir):
            print(f"Processing {company} files...")

            for filename in os.listdir(company_dir):
                if filename.endswith('.htm'):
                    filepath = os.path.join(company_dir, filename)
                    print(f"  Processing {filename}...")

                    try:
                        chunks = processor.process_document(filepath)
                        if chunks:
                            vector_store.add_documents(chunks)
                            total_chunks += len(chunks)
                            processed_files += 1
                            print(f"    Generated {len(chunks)} chunks")
                        else:
                            print(f"    No chunks generated")

                    except Exception as e:
                        print(f"    Error processing {filename}: {e}")
        else:
            print(f"No files found for {company}")

    # Final statistics
    elapsed_time = time.time() - start_time

    print()
    print("=" * 60)
    print("INGESTION COMPLETE!")
    print("=" * 60)
    print(f"Files processed: {processed_files}")
    print(f"Total chunks created: {total_chunks}")
    print(f"Vector store size: {vector_store.index.ntotal if vector_store.index else 0} vectors")
    print(f"Processing time: {elapsed_time:.1f} seconds")
    print()
    print("Vector store saved to: data/vector_index")
    print("Ready for Phase 2: Interface (run python main.py)")
    print("=" * 60)

    return {
        "files_processed": processed_files,
        "total_chunks": total_chunks,
        "vector_count": vector_store.index.ntotal if vector_store.index else 0,
        "processing_time": elapsed_time
    }


if __name__ == "__main__":
    try:
        results = run_ingestion()

        # Check if ingestion was successful
        if results["vector_count"] > 0:
            print("\nSUCCESS: Ingestion completed successfully!")
            print("You can now run Phase 2: python main.py")
        else:
            print("\nWARNING: No vectors created. Check for errors above.")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user.")
    except Exception as e:
        print(f"\nERROR: Ingestion failed: {e}")
        import traceback
        traceback.print_exc()