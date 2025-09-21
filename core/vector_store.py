"""
Vector Store using FAISS and SentenceTransformers
Handles document embeddings and similarity search
"""

import numpy as np
import faiss
import pickle
import json
import sys
import os
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from sentence_transformers import SentenceTransformer

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.schemas import DocumentChunk, Source
from factory import get_embedding_model


class FAISSVectorStore:
    """FAISS-based vector store for document chunks"""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
                 index_path: str = "data/vector_index"):
        self.model_name = model_name
        self.embedding_model = get_embedding_model(model_name)
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Initialize FAISS index
        self.index = None
        self.chunks_metadata = []  # Store chunk metadata
        self.dimension = None

        # Load existing index if available
        self._load_index()

    def _get_embedding_dimension(self) -> int:
        """Get embedding dimension from the model"""
        if self.dimension is None:
            # Get dimension by encoding a sample text
            sample_embedding = self.embedding_model.encode(["sample text"])
            self.dimension = sample_embedding.shape[1]
        return self.dimension

    def _create_index(self, dimension: int) -> faiss.Index:
        """Create a new FAISS index"""
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        index = faiss.IndexFlatIP(dimension)
        return index

    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        if self.index is None:
            return

        # Save FAISS index
        index_file = self.index_path / "faiss_index.bin"
        faiss.write_index(self.index, str(index_file))

        # Save chunks metadata
        metadata_file = self.index_path / "chunks_metadata.json"
        # Convert DocumentChunk objects to dict for JSON serialization
        metadata_dicts = []
        for chunk in self.chunks_metadata:
            chunk_dict = {
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "metadata": {
                    "company": chunk.metadata.company,
                    "year": chunk.metadata.year,
                    "filing_type": chunk.metadata.filing_type,
                    "total_pages": chunk.metadata.total_pages,
                    "sections": chunk.metadata.sections
                },
                "page_number": chunk.page_number,
                "section": chunk.section,
                "token_count": chunk.token_count
            }
            metadata_dicts.append(chunk_dict)

        with open(metadata_file, 'w') as f:
            json.dump(metadata_dicts, f, indent=2)

        print(f"Saved index with {self.index.ntotal} vectors to {self.index_path}")

    def _load_index(self):
        """Load FAISS index and metadata from disk"""
        index_file = self.index_path / "faiss_index.bin"
        metadata_file = self.index_path / "chunks_metadata.json"

        if not (index_file.exists() and metadata_file.exists()):
            print("No existing index found")
            return

        try:
            # Load FAISS index
            self.index = faiss.read_index(str(index_file))
            self.dimension = self.index.d

            # Load chunks metadata
            with open(metadata_file, 'r') as f:
                metadata_dicts = json.load(f)

            # Convert back to DocumentChunk objects
            from models.schemas import DocumentMetadata
            self.chunks_metadata = []
            for chunk_dict in metadata_dicts:
                metadata = DocumentMetadata(**chunk_dict["metadata"])
                chunk = DocumentChunk(
                    chunk_id=chunk_dict["chunk_id"],
                    content=chunk_dict["content"],
                    metadata=metadata,
                    page_number=chunk_dict.get("page_number"),
                    section=chunk_dict.get("section"),
                    token_count=chunk_dict.get("token_count")
                )
                self.chunks_metadata.append(chunk)

            print(f"Loaded index with {self.index.ntotal} vectors from {self.index_path}")

        except Exception as e:
            print(f"Error loading index: {e}")
            self.index = None
            self.chunks_metadata = []

    def add_documents(self, chunks: List[DocumentChunk]):
        """Add document chunks to the vector store"""
        if not chunks:
            return

        print(f"Adding {len(chunks)} chunks to vector store")

        # Extract text content for embedding
        texts = [chunk.content for chunk in chunks]

        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.embedding_model.encode(texts, show_progress_bar=True)

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(embeddings)

        # Initialize index if needed
        if self.index is None:
            dimension = embeddings.shape[1]
            self.index = self._create_index(dimension)
            self.dimension = dimension

        # Add embeddings to index
        self.index.add(embeddings.astype(np.float32))

        # Store chunk metadata
        self.chunks_metadata.extend(chunks)

        # Save to disk
        self._save_index()

        print(f"Added {len(chunks)} chunks. Total vectors: {self.index.ntotal}")

    def search(self, query: str, k: int = 5,
               company_filter: Optional[str] = None,
               year_filter: Optional[str] = None,
               section_filter: Optional[str] = None) -> List[Tuple[DocumentChunk, float]]:
        """Search for similar chunks"""
        if self.index is None or self.index.ntotal == 0:
            print("No vectors in index")
            return []

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query])
        faiss.normalize_L2(query_embedding)

        # Search in FAISS index
        scores, indices = self.index.search(query_embedding.astype(np.float32), min(k * 3, self.index.ntotal))

        # Convert results to chunks with scores
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.chunks_metadata):
                chunk = self.chunks_metadata[idx]

                # Apply filters
                if company_filter and chunk.metadata.company != company_filter:
                    continue
                if year_filter and chunk.metadata.year != year_filter:
                    continue
                if section_filter and chunk.section != section_filter:
                    continue

                results.append((chunk, float(score)))

        # Return top k results
        return results[:k]

    def search_multiple_queries(self, queries: List[str], k: int = 5) -> Dict[str, List[Tuple[DocumentChunk, float]]]:
        """Search for multiple queries simultaneously"""
        results = {}
        for query in queries:
            results[query] = self.search(query, k)
        return results

    def get_stats(self) -> Dict:
        """Get statistics about the vector store"""
        if self.index is None:
            return {"total_chunks": 0, "companies": [], "years": []}

        companies = set()
        years = set()
        sections = set()

        for chunk in self.chunks_metadata:
            companies.add(chunk.metadata.company)
            years.add(chunk.metadata.year)
            if chunk.section:
                sections.add(chunk.section)

        return {
            "total_chunks": self.index.ntotal,
            "companies": sorted(list(companies)),
            "years": sorted(list(years)),
            "sections": sorted(list(sections)),
            "embedding_dimension": self.dimension,
            "model_name": self.model_name
        }

    def chunk_to_source(self, chunk: DocumentChunk, similarity_score: float) -> Source:
        """Convert a DocumentChunk to a Source object"""
        # Get excerpt (first 200 chars of content)
        excerpt = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content

        return Source(
            company=chunk.metadata.company,
            year=chunk.metadata.year,
            excerpt=excerpt,
            page=chunk.page_number,
            section=chunk.section,
            chunk_id=chunk.chunk_id,
            similarity_score=similarity_score
        )


if __name__ == "__main__":
    # Test vector store
    vector_store = FAISSVectorStore()

    # Print stats
    stats = vector_store.get_stats()
    print(f"Vector store stats: {stats}")

    # Test search
    if stats["total_chunks"] > 0:
        results = vector_store.search("revenue growth", k=3)
        print(f"Found {len(results)} results for 'revenue growth'")
        for chunk, score in results:
            print(f"Score: {score:.3f}, Company: {chunk.metadata.company}, Year: {chunk.metadata.year}")
            print(f"Content: {chunk.content[:100]}...")
            print("---")