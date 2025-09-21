"""
Document Processing Module
Handles PDF text extraction, chunking, and metadata preservation
"""

import os
import re
import hashlib
import sys
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import PyPDF2
import pdfplumber
from bs4 import BeautifulSoup

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import DocumentChunk, DocumentMetadata


class DocumentProcessor:
    """Processes SEC 10-K filings into semantic chunks with metadata"""

    # Key sections in 10-K filings
    SEC_SECTIONS = {
        "Item 1": "Business",
        "Item 1A": "Risk Factors",
        "Item 1B": "Unresolved Staff Comments",
        "Item 2": "Properties",
        "Item 3": "Legal Proceedings",
        "Item 4": "Mine Safety Disclosures",
        "Item 5": "Market for Registrant's Common Equity",
        "Item 6": "Selected Financial Data",
        "Item 7": "Management's Discussion and Analysis",
        "Item 7A": "Quantitative and Qualitative Disclosures",
        "Item 8": "Financial Statements and Supplementary Data",
        "Item 9": "Changes in and Disagreements",
        "Item 9A": "Controls and Procedures",
        "Item 9B": "Other Information",
        "Item 10": "Directors, Executive Officers and Corporate Governance",
        "Item 11": "Executive Compensation",
        "Item 12": "Security Ownership",
        "Item 13": "Certain Relationships and Related Party Transactions",
        "Item 14": "Principal Accounting Fees and Services",
        "Item 15": "Exhibits and Financial Statement Schedules"
    }

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_html(self, html_path: str) -> Tuple[str, int]:
        """Extract text from HTML file (SEC XBRL format)"""
        try:
            with open(html_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)

            # Estimate page count (rough approximation for HTML)
            page_count = max(1, len(text) // 3000)

            return text, page_count

        except Exception as e:
            print(f"Error extracting text from HTML {html_path}: {e}")
            return "", 0

    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, int]:
        """Extract text from PDF file"""
        try:
            text = ""
            page_count = 0

            # Try pdfplumber first (better for tables)
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    page_count = len(pdf.pages)
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
                return text, page_count

            except Exception:
                # Fallback to PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    page_count = len(pdf_reader.pages)

                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"

                return text, page_count

        except Exception as e:
            print(f"Error extracting text from {pdf_path}: {e}")
            return "", 0

    def identify_sections(self, text: str) -> Dict[str, int]:
        """Identify the starting positions of key sections in the document"""
        sections = {}

        for item, description in self.SEC_SECTIONS.items():
            # Look for section headers like "Item 1. Business" or "ITEM 1 - BUSINESS"
            patterns = [
                rf"{re.escape(item)}\s*[\.\-]\s*{re.escape(description)}",
                rf"{re.escape(item.upper())}\s*[\.\-]\s*{re.escape(description.upper())}",
                rf"(?:PART\s+I.*?)?{re.escape(item)}\s*[\.\-]\s*{re.escape(description)}",
                rf"{re.escape(item)}\s*{re.escape(description)}",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
                if match:
                    sections[item] = match.start()
                    break

        return sections

    def get_section_for_position(self, position: int, sections: Dict[str, int]) -> Optional[str]:
        """Determine which section a text position belongs to"""
        if not sections:
            return None

        # Sort sections by position
        sorted_sections = sorted(sections.items(), key=lambda x: x[1])

        current_section = None
        for section, start_pos in sorted_sections:
            if position >= start_pos:
                current_section = section
            else:
                break

        return current_section

    def semantic_chunking(self, text: str, sections: Dict[str, int]) -> List[Tuple[str, Optional[str], int]]:
        """Create semantic chunks respecting section boundaries"""
        chunks = []

        # Split by sentences first
        sentences = re.split(r'(?<=[.!?])\s+', text)

        current_chunk = ""
        current_position = 0

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(potential_chunk.split()) > self.chunk_size and current_chunk:
                # Save current chunk
                section = self.get_section_for_position(current_position, sections)
                chunks.append((current_chunk.strip(), section, current_position))

                # Start new chunk with overlap
                overlap_words = current_chunk.split()[-self.chunk_overlap:]
                current_chunk = " ".join(overlap_words) + " " + sentence
                current_position = text.find(sentence, current_position)
            else:
                current_chunk = potential_chunk
                if not current_chunk or len(current_chunk.split()) == 1:
                    current_position = text.find(sentence, current_position)

        # Add final chunk
        if current_chunk.strip():
            section = self.get_section_for_position(current_position, sections)
            chunks.append((current_chunk.strip(), section, current_position))

        return chunks

    def extract_metadata_from_filename(self, filepath: str) -> DocumentMetadata:
        """Extract metadata from filename (company_year_filename.pdf)"""
        filename = Path(filepath).name

        # Parse filename: COMPANY_YEAR_*.pdf
        parts = filename.split('_')
        if len(parts) >= 2:
            company = parts[0]
            year = parts[1]
        else:
            # Fallback: try to extract from parent directory
            company = Path(filepath).parent.name
            year = "unknown"

        return DocumentMetadata(
            company=company,
            year=year,
            filing_type="10-K"
        )

    def process_document(self, filepath: str) -> List[DocumentChunk]:
        """Process a single document into chunks with metadata"""
        print(f"Processing document: {filepath}")

        # Extract text based on file type
        if filepath.lower().endswith(('.htm', '.html')):
            text, page_count = self.extract_text_from_html(filepath)
        else:
            text, page_count = self.extract_text_from_pdf(filepath)

        if not text:
            print(f"No text extracted from {filepath}")
            return []

        # Extract metadata
        metadata = self.extract_metadata_from_filename(filepath)
        metadata.total_pages = page_count

        # Identify sections
        sections = self.identify_sections(text)
        metadata.sections = list(sections.keys())

        print(f"Found {len(sections)} sections in {filepath}")

        # Create semantic chunks
        chunks_data = self.semantic_chunking(text, sections)

        # Create DocumentChunk objects
        document_chunks = []
        for i, (chunk_text, section, position) in enumerate(chunks_data):
            # Create unique chunk ID
            chunk_id = hashlib.md5(
                f"{metadata.company}_{metadata.year}_{i}_{chunk_text[:50]}".encode()
            ).hexdigest()

            # Estimate page number based on position
            estimated_page = min(int((position / len(text)) * page_count) + 1, page_count)

            chunk = DocumentChunk(
                chunk_id=chunk_id,
                content=chunk_text,
                metadata=metadata,
                page_number=estimated_page,
                section=section,
                token_count=len(chunk_text.split())
            )

            document_chunks.append(chunk)

        print(f"Created {len(document_chunks)} chunks from {filepath}")
        return document_chunks

    def process_all_documents(self, filings_dict: Dict[str, List[str]]) -> List[DocumentChunk]:
        """Process all downloaded documents"""
        all_chunks = []

        for company, filepaths in filings_dict.items():
            print(f"Processing {len(filepaths)} documents for {company}")

            for filepath in filepaths:
                chunks = self.process_document(filepath)
                all_chunks.extend(chunks)

        print(f"Total chunks created: {len(all_chunks)}")
        return all_chunks


if __name__ == "__main__":
    # Test document processing
    processor = DocumentProcessor()

    # Test with a sample file (if available)
    test_files = {
        "GOOGL": ["data/filings/GOOGL/GOOGL_2023_10-k.htm"]
    }

    chunks = processor.process_all_documents(test_files)
    print(f"Processed {len(chunks)} chunks")