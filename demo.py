#!/usr/bin/env python3
"""
Financial Q&A System Demo
Shows the system working with sample data
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import json
from models.schemas import DocumentChunk, DocumentMetadata, QueryResponse, Source
from core.vector_store import FAISSVectorStore
from core.financial_agent import FinancialAgent


def create_sample_data():
    """Create sample financial data chunks for demonstration"""

    # Sample financial data from the companies
    sample_texts = [
        # Microsoft 2023 Revenue
        "Microsoft Corporation reported total revenue of $211.9 billion for fiscal year 2023, representing a 7% increase from the prior year. Our Productivity and Business Processes segment generated $69.3 billion in revenue, while More Personal Computing contributed $54.7 billion. The Intelligent Cloud segment was our fastest growing, reaching $87.9 billion in revenue.",

        # Microsoft Operating Margin 2023
        "For fiscal year 2023, Microsoft achieved an operating margin of 42.1%, demonstrating strong operational efficiency. This margin reflects our disciplined approach to cost management while continuing to invest in strategic growth areas including cloud computing and artificial intelligence capabilities.",

        # Google 2023 Revenue
        "Alphabet Inc. reported total revenues of $307.4 billion for fiscal year 2023. Google advertising revenues were $237.9 billion, representing 77% of total revenues. Google Cloud generated $33.1 billion in revenue, showing 26% year-over-year growth. YouTube advertising revenues reached $31.5 billion.",

        # Google Operating Margin 2023
        "Alphabet's operating margin for 2023 was 29.8%, reflecting strong performance across our core advertising business and growing cloud operations. We continue to focus on operational efficiency while investing in AI and machine learning capabilities.",

        # NVIDIA 2023 Revenue
        "NVIDIA Corporation reported record revenues of $95.0 billion for fiscal year 2024, up 126% from the previous year. Data Center revenue reached $47.5 billion, up 217% year-over-year, driven by strong demand for our AI and high-performance computing solutions. Gaming revenue was $10.4 billion.",

        # NVIDIA Operating Margin 2023
        "NVIDIA achieved an operating margin of 32.9% for fiscal year 2024, demonstrating the strong profitability of our AI and data center products. This represents a significant improvement from the prior year margin of 17.0%.",

        # Microsoft Cloud Growth
        "Microsoft Cloud revenue grew to $111.6 billion in fiscal year 2023, representing 22% growth year-over-year. Azure and other cloud services revenue increased by 27%, while Office 365 Commercial products grew by 11%. Our cloud business now represents over 50% of total company revenue.",

        # NVIDIA Data Center Growth
        "NVIDIA Data Center revenue reached $47.5 billion in fiscal year 2024, compared to $15.0 billion in fiscal year 2023, representing growth of 217%. This growth was driven by strong demand for our H100 Tensor Core GPUs and accelerated computing platforms for AI workloads.",

        # Google Cloud Growth
        "Google Cloud revenue increased to $33.1 billion in 2023, up from $26.3 billion in 2022, representing 26% year-over-year growth. Our cloud infrastructure and platform services continue to gain market share, with strong adoption of our AI and machine learning tools.",

        # AI Investments Comparison
        "Microsoft has invested heavily in AI capabilities, including our partnership with OpenAI and integration of AI across our product portfolio. We are incorporating AI into Office 365, Azure, and our development tools. Google has made significant investments in AI research and development, with our Bard conversational AI and AI-powered search enhancements. NVIDIA's AI investments focus on our GPU architecture and software platforms that enable AI training and inference across industries."
    ]

    # Create chunks with metadata
    chunks = []
    companies = ["MSFT", "GOOGL", "NVDA"]
    sections = ["Item 7", "Item 8", "Item 1"]

    for i, text in enumerate(sample_texts):
        company = companies[i % 3]
        year = "2023"

        metadata = DocumentMetadata(
            company=company,
            year=year,
            filing_type="10-K",
            total_pages=100,
            sections=["Item 7", "Item 8"]
        )

        chunk = DocumentChunk(
            chunk_id=f"chunk_{i}",
            content=text,
            metadata=metadata,
            page_number=10 + (i % 5),
            section=sections[i % 3],
            token_count=len(text.split())
        )
        chunks.append(chunk)

    return chunks


def demo_vector_store(chunks):
    """Demonstrate vector store functionality"""
    print("=== Vector Store Demo ===")

    # Initialize vector store
    vector_store = FAISSVectorStore()

    # Add sample documents
    print(f"Adding {len(chunks)} sample chunks to vector store...")
    vector_store.add_documents(chunks)

    # Show stats
    stats = vector_store.get_stats()
    print(f"Vector store contains {stats['total_chunks']} chunks")
    print(f"Companies: {stats['companies']}")
    print(f"Years: {stats['years']}")

    # Test search
    print("\n--- Search Demo ---")
    test_queries = [
        "Microsoft revenue 2023",
        "operating margin",
        "cloud growth"
    ]

    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = vector_store.search(query, k=2)
        for chunk, score in results:
            print(f"  Score: {score:.3f} | Company: {chunk.metadata.company}")
            print(f"  Text: {chunk.content[:100]}...")

    return vector_store


def demo_agent(vector_store):
    """Demonstrate agent functionality"""
    print("\n=== Agent Demo ===")

    # Initialize agent
    try:
        agent = FinancialAgent(vector_store)
        print("Agent initialized successfully")
    except Exception as e:
        print(f"Agent initialization failed: {e}")
        print("Continuing with vector store demo only...")
        return

    # Test queries
    test_queries = [
        "What was Microsoft's total revenue in 2023?",
        "Which company had the highest operating margin in 2023?",
        "How did Microsoft's cloud revenue grow?"
    ]

    print("\n--- Agent Query Demo ---")
    for i, query in enumerate(test_queries, 1):
        print(f"\n{i}. Query: {query}")
        try:
            response = agent.process_query(query)
            print(f"   Answer: {response.answer}")
            print(f"   Sub-queries: {response.sub_queries}")
            print(f"   Sources: {len(response.sources)}")
        except Exception as e:
            print(f"   Error: {e}")


def main():
    """Run the complete demo"""
    print("Financial Q&A System Demo")
    print("=" * 50)

    # Create sample data
    print("Creating sample financial data...")
    chunks = create_sample_data()
    print(f"Created {len(chunks)} sample chunks")

    # Demo vector store
    vector_store = demo_vector_store(chunks)

    # Demo agent (if Google Cloud is set up)
    demo_agent(vector_store)

    print("\n" + "=" * 50)
    print("Demo completed!")
    print("\nThe system demonstrates:")
    print("- PDF text processing and chunking")
    print("- Vector embeddings with FAISS")
    print("- Semantic search capabilities")
    print("- Agent-based query processing (if Google Cloud configured)")
    print("\nTo use with real SEC data:")
    print("1. Fix SEC API endpoints in sec_downloader.py")
    print("2. Run: python utils/pipeline.py")


if __name__ == "__main__":
    main()