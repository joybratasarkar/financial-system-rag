"""
Pydantic models for API request/response schemas
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    max_results: Optional[int] = 5


class Source(BaseModel):
    company: str
    year: str
    excerpt: str
    page: Optional[int] = None
    section: Optional[str] = None
    chunk_id: Optional[str] = None
    similarity_score: Optional[float] = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    reasoning: str
    sub_queries: List[str]
    sources: List[Source]
    processing_time: Optional[float] = None


class DocumentMetadata(BaseModel):
    company: str
    year: str
    filing_type: str = "10-K"
    total_pages: Optional[int] = None
    sections: Optional[List[str]] = None


class DocumentChunk(BaseModel):
    chunk_id: str
    content: str
    metadata: DocumentMetadata
    page_number: Optional[int] = None
    section: Optional[str] = None
    token_count: Optional[int] = None


class DownloadRequest(BaseModel):
    companies: List[str] = ["GOOGL", "MSFT", "NVDA"]
    years: List[str] = ["2022", "2023", "2024"]
    force_download: bool = False


class ProcessingStatus(BaseModel):
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None