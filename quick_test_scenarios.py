#!/usr/bin/env python3
"""
Quick Test Scenarios - Essential 5 Query Types from Assignment
"""

import requests
import json


def test_scenario():
    """Test the 5 required query types from the assignment"""
    base_url = "http://localhost:8000/api/v1"

    print("🎯 ASSIGNMENT REQUIREMENT TEST - 5 Query Types")
    print("="*60)

    # Test scenarios based on assignment PDF requirements
    scenarios = [
        {
            "type": "1. Basic Metrics",
            "query": "What was Microsoft's total revenue in 2023?",
            "expect": "Should return $211.9 billion"
        },
        {
            "type": "2. YoY Comparison",
            "query": "How did NVIDIA's data center revenue grow from 2022 to 2023?",
            "expect": "Should calculate growth from $15.0B to $47.5B"
        },
        {
            "type": "3. Cross-Company",
            "query": "Which company had the highest operating margin in 2023?",
            "expect": "Should identify Microsoft at 42.1%"
        },
        {
            "type": "4. Segment Analysis",
            "query": "What percentage of Google's revenue came from cloud in 2023?",
            "expect": "Should calculate $33.1B / $307.4B ≈ 10.8%"
        },
        {
            "type": "5. AI Strategy",
            "query": "Compare AI investments mentioned by all three companies",
            "expect": "Should mention OpenAI partnership, AI capabilities"
        }
    ]

    results = []

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n{i}/5 - {scenario['type']}")
        print(f"Query: {scenario['query']}")
        print(f"Expected: {scenario['expect']}")
        print("-" * 50)

        try:
            # Make API call
            response = requests.post(
                f"{base_url}/query",
                json={"query": scenario["query"]},
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()

                print(f"✅ ANSWER: {result['answer']}")
                print(f"🔗 Sub-queries: {len(result['sub_queries'])}")
                print(f"📚 Sources: {len(result['sources'])}")
                print(f"⏱️ Time: {result.get('processing_time', 0):.2f}s")

                # Simple validation
                answer_lower = result['answer'].lower()
                success = not ('unable' in answer_lower or 'sorry' in answer_lower)

                results.append({
                    "type": scenario['type'],
                    "success": success,
                    "answer": result['answer']
                })

                print(f"📊 Status: {'✅ PASS' if success else '❌ FAIL'}")

            else:
                print(f"❌ HTTP Error: {response.status_code}")
                results.append({"type": scenario['type'], "success": False, "error": response.status_code})

        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({"type": scenario['type'], "success": False, "error": str(e)})

        if i < len(scenarios):
            input("\nPress Enter for next test...")

    # Summary
    print(f"\n{'='*60}")
    print("ASSIGNMENT COMPLIANCE SUMMARY")
    print('='*60)

    passed = sum(1 for r in results if r.get('success', False))
    total = len(results)

    print(f"📊 Results: {passed}/{total} query types working ({(passed/total)*100:.1f}%)")

    for result in results:
        status = "✅" if result.get('success', False) else "❌"
        print(f"{status} {result['type']}")

    if passed >= 4:
        print(f"\n🎉 ASSIGNMENT REQUIREMENTS: MOSTLY MET!")
        print(f"System demonstrates agent capabilities and multi-step reasoning.")
    else:
        print(f"\n⚠️ ASSIGNMENT REQUIREMENTS: NEEDS IMPROVEMENT")

    return results


if __name__ == "__main__":
    # Check server
    try:
        response = requests.get("http://localhost:8000/api/v1/health", timeout=5)
        print("🚀 Server is running. Starting tests...\n")
    except:
        print("❌ Server not running. Start with: python main.py")
        exit(1)

    test_scenario()