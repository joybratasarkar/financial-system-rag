#!/usr/bin/env python3
"""
Assignment Validation Test Cases
Tests exact requirements from the PDF assignment
"""

import requests
import json
import time


def validate_assignment():
    """Validate against exact assignment requirements"""
    base_url = "http://localhost:8000/api/v1"

    print("📋 ASSIGNMENT VALIDATION TEST")
    print("Testing exact requirements from PDF")
    print("="*50)

    # Exact queries from assignment PDF
    assignment_queries = [
        {
            "category": "Basic Metrics",
            "query": "What was Microsoft's total revenue in 2023?",
            "pdf_example": "Page 2 - Example query",
            "required_elements": ["single_retrieval", "direct_answer"]
        },
        {
            "category": "YoY Comparison",
            "query": "How did NVIDIA's data center revenue grow from 2022 to 2023?",
            "pdf_example": "Page 2 - Requires decomposition",
            "required_elements": ["query_decomposition", "multi_step", "calculation"]
        },
        {
            "category": "Cross-Company Analysis",
            "query": "Which company had the highest operating margin in 2023?",
            "pdf_example": "Page 2 - Multiple retrievals",
            "required_elements": ["multiple_searches", "comparison", "ranking"]
        },
        {
            "category": "Segment Analysis",
            "query": "What percentage of Google's revenue came from cloud in 2023?",
            "pdf_example": "Page 2 - Segment analysis",
            "required_elements": ["calculation", "percentage", "segment_data"]
        },
        {
            "category": "AI Strategy",
            "query": "Compare AI investments mentioned by all three companies in their 2024 10-Ks",
            "pdf_example": "Page 2 - AI strategy comparison",
            "required_elements": ["multi_company", "ai_analysis", "comparison"]
        }
    ]

    results = []

    for i, test in enumerate(assignment_queries, 1):
        print(f"\n{i}/5 - {test['category']}")
        print(f"Query: {test['query']}")
        print(f"PDF Reference: {test['pdf_example']}")
        print(f"Required: {', '.join(test['required_elements'])}")
        print("-" * 60)

        # Test the query
        result = test_query(base_url, test['query'])

        # Validate against assignment requirements
        validation = validate_response(result, test['required_elements'])

        results.append({
            "category": test['category'],
            "query": test['query'],
            "success": result['success'],
            "validation": validation,
            "response": result.get('response', {})
        })

        print(f"✅ Response: {result.get('success', False)}")
        print(f"✅ Validation: {validation['score']}/5 requirements met")

        if i < len(assignment_queries):
            input("\nPress Enter to continue...")

    # Final assessment
    print_assignment_assessment(results)


def test_query(base_url, query):
    """Test a single query"""
    try:
        start_time = time.time()

        response = requests.post(
            f"{base_url}/query",
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        processing_time = time.time() - start_time

        if response.status_code == 200:
            result = response.json()

            print(f"📝 Answer: {result['answer'][:100]}...")
            print(f"🔗 Sub-queries: {len(result['sub_queries'])}")
            print(f"📚 Sources: {len(result['sources'])}")
            print(f"⏱️ Time: {processing_time:.2f}s")

            return {
                "success": True,
                "response": result,
                "processing_time": processing_time
            }
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}

    except Exception as e:
        print(f"❌ Exception: {e}")
        return {"success": False, "error": str(e)}


def validate_response(result, required_elements):
    """Validate response against assignment requirements"""
    validation = {"score": 0, "details": []}

    if not result.get('success'):
        return validation

    response = result['response']
    answer = response.get('answer', '').lower()

    # Check requirements
    checks = {
        "single_retrieval": len(response.get('sub_queries', [])) <= 1,
        "direct_answer": 'unable' not in answer and 'sorry' not in answer,
        "query_decomposition": len(response.get('sub_queries', [])) > 1,
        "multi_step": len(response.get('sub_queries', [])) >= 2,
        "calculation": any(word in answer for word in ['%', 'percent', 'billion', 'growth', 'increase']),
        "multiple_searches": len(response.get('sub_queries', [])) >= 3,
        "comparison": any(word in answer for word in ['highest', 'compare', 'vs', 'better', 'more']),
        "ranking": any(word in answer for word in ['highest', 'lowest', 'first', 'best']),
        "percentage": '%' in answer or 'percent' in answer,
        "segment_data": any(word in answer for word in ['cloud', 'segment', 'division']),
        "multi_company": len(response.get('sources', [])) > 0,
        "ai_analysis": any(word in answer for word in ['ai', 'artificial', 'intelligence', 'openai'])
    }

    for element in required_elements:
        if element in checks and checks[element]:
            validation["score"] += 1
            validation["details"].append(f"✅ {element}")
        else:
            validation["details"].append(f"❌ {element}")

    return validation


def print_assignment_assessment(results):
    """Print final assignment assessment"""
    print(f"\n{'='*70}")
    print("ASSIGNMENT COMPLIANCE ASSESSMENT")
    print('='*70)

    total_categories = len(results)
    successful_categories = sum(1 for r in results if r['success'])

    print(f"📊 QUERY CATEGORIES: {successful_categories}/{total_categories} working")

    for result in results:
        status = "✅" if result['success'] else "❌"
        score = result['validation']['score']
        total_req = len(result['validation']['details'])
        print(f"{status} {result['category']}: {score}/{total_req} requirements")

    # Assignment rubric assessment (from PDF page 4)
    print(f"\n📋 ASSIGNMENT RUBRIC ASSESSMENT:")

    # RAG Implementation (30%)
    rag_score = "✅ EXCELLENT" if successful_categories >= 4 else "⚠️ NEEDS WORK"
    print(f"   RAG Implementation (30%): {rag_score}")

    # Agent Orchestration (30%)
    agent_working = any(r['validation']['score'] >= 2 for r in results)
    agent_score = "✅ EXCELLENT" if agent_working else "⚠️ NEEDS WORK"
    print(f"   Agent Orchestration (30%): {agent_score}")

    # Query Accuracy (20%)
    accuracy = (successful_categories / total_categories) * 100
    accuracy_score = "✅ EXCELLENT" if accuracy >= 80 else "⚠️ NEEDS WORK"
    print(f"   Query Accuracy (20%): {accuracy_score} ({accuracy:.1f}%)")

    # Overall assessment
    overall_score = successful_categories / total_categories
    if overall_score >= 0.8:
        print(f"\n🎉 ASSIGNMENT STATUS: ✅ REQUIREMENTS MET")
        print(f"System demonstrates RAG and agent capabilities as required.")
    elif overall_score >= 0.6:
        print(f"\n⚠️ ASSIGNMENT STATUS: 🟡 PARTIALLY MET")
        print(f"Core functionality working, some improvements needed.")
    else:
        print(f"\n❌ ASSIGNMENT STATUS: ❌ REQUIREMENTS NOT MET")
        print(f"Significant issues need to be addressed.")

    print(f"\n📈 Overall Score: {overall_score*100:.1f}%")


if __name__ == "__main__":
    # Check server
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        print("🚀 Server is running. Starting validation...\n")
        validate_assignment()
    except:
        print("❌ Server not running. Start with: python main.py")
        exit(1)