"""
FastAPI routes for Financial Q&A System
"""

import time
from typing import Dict, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from models.schemas import (
        QueryRequest, QueryResponse, DownloadRequest,
        ProcessingStatus, DocumentMetadata
    )
    from core.sec_downloader import SECDownloader
    from core.document_processor import DocumentProcessor
    from core.vector_store import FAISSVectorStore
    from core.financial_agent import FinancialAgent
except ImportError as e:
    print(f"Import error in routes.py: {e}")
    print(f"Python path: {sys.path}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    if project_root.exists():
        print(f"Files in project root: {list(project_root.iterdir())}")
    raise

router = APIRouter()

# Global instances (in production, use dependency injection)
vector_store = None
agent = None
downloader = SECDownloader()
processor = DocumentProcessor()


def initialize_system():
    """Initialize vector store and agent"""
    global vector_store, agent
    if vector_store is None:
        vector_store = FAISSVectorStore()
    if agent is None:
        agent = FinancialAgent(vector_store)


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Financial Q&A System is running"}


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    initialize_system()
    stats = vector_store.get_stats()
    return {
        "vector_store": stats,
        "system_status": "operational"
    }


@router.post("/download", response_model=ProcessingStatus)
async def download_filings(request: DownloadRequest, background_tasks: BackgroundTasks):
    """Download SEC filings"""
    try:
        print(f"Starting download for companies: {request.companies}, years: {request.years}")

        # Download in background
        def download_task():
            try:
                results = downloader.download_all_filings(request.companies, request.years)
                print(f"Download completed: {results}")
            except Exception as e:
                print(f"Download error: {e}")

        background_tasks.add_task(download_task)

        return ProcessingStatus(
            status="started",
            message="Download started in background",
            details={
                "companies": request.companies,
                "years": request.years
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.post("/process", response_model=ProcessingStatus)
async def process_documents(background_tasks: BackgroundTasks):
    """Process downloaded documents into vector store"""
    try:
        initialize_system()

        def process_task():
            try:
                # Find downloaded files
                import os
                from pathlib import Path

                filings_dir = Path("data/filings")
                if not filings_dir.exists():
                    print("No filings directory found")
                    return

                # Collect all files
                filings_dict = {}
                for company_dir in filings_dir.iterdir():
                    if company_dir.is_dir():
                        company = company_dir.name
                        files = []
                        for file in company_dir.iterdir():
                            if file.suffix.lower() in ['.pdf', '.htm', '.html']:
                                files.append(str(file))
                        if files:
                            filings_dict[company] = files

                print(f"Found filings: {filings_dict}")

                if filings_dict:
                    # Process documents
                    chunks = processor.process_all_documents(filings_dict)

                    # Add to vector store
                    if chunks:
                        vector_store.add_documents(chunks)
                        print(f"Added {len(chunks)} chunks to vector store")
                    else:
                        print("No chunks created from documents")
                else:
                    print("No documents found to process")

            except Exception as e:
                print(f"Processing error: {e}")

        background_tasks.add_task(process_task)

        return ProcessingStatus(
            status="started",
            message="Document processing started in background"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.post("/query", response_model=QueryResponse)
async def ask_question(request: QueryRequest):
    """Process a financial question"""
    try:
        start_time = time.time()

        initialize_system()

        # Check if vector store has data
        stats = vector_store.get_stats()
        if stats["total_chunks"] == 0:
            raise HTTPException(
                status_code=400,
                detail="No documents loaded. Please download and process documents first."
            )

        # Process query through agent
        response = agent.process_query(request.query)

        # Add processing time
        processing_time = time.time() - start_time
        response.processing_time = processing_time

        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.get("/search")
async def search_documents(
    query: str,
    k: int = 5,
    company: str = None,
    year: str = None,
    section: str = None
):
    """Direct search in vector store"""
    try:
        initialize_system()

        results = vector_store.search(
            query=query,
            k=k,
            company_filter=company,
            year_filter=year,
            section_filter=section
        )

        # Convert results to response format
        search_results = []
        for chunk, score in results:
            search_results.append({
                "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                "similarity_score": score,
                "company": chunk.metadata.company,
                "year": chunk.metadata.year,
                "section": chunk.section,
                "page": chunk.page_number,
                "chunk_id": chunk.chunk_id
            })

        return {
            "query": query,
            "results": search_results,
            "total_found": len(search_results)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/companies")
async def get_companies():
    """Get list of available companies"""
    initialize_system()
    stats = vector_store.get_stats()
    return {
        "companies": stats.get("companies", []),
        "years": stats.get("years", []),
        "sections": stats.get("sections", [])
    }


# Test queries endpoint
@router.get("/test-queries")
async def get_test_queries():
    """Get sample test queries"""
    return {
        "simple_queries": [
            "What was NVIDIA's total revenue in fiscal year 2024?",
            "What percentage of Google's 2023 revenue came from advertising?",
            "What was Microsoft's operating margin in 2023?"
        ],
        "comparative_queries": [
            "How much did Microsoft's cloud revenue grow from 2022 to 2023?",
            "Which of the three companies had the highest gross margin in 2023?",
            "How did NVIDIA's data center revenue grow from 2022 to 2023?"
        ],
        "complex_queries": [
            "Compare the R&D spending as a percentage of revenue across all three companies in 2023",
            "How did each company's operating margin change from 2022 to 2024?",
            "What are the main AI risks mentioned by each company and how do they differ?",
            "Which company had the highest operating margin in 2023?",
            "Compare cloud revenue growth rates across all three companies from 2022 to 2023"
        ]
    }