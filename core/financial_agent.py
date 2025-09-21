"""
Financial Q&A Agent using LangGraph
Handles query decomposition, multi-step retrieval, and result synthesis
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, TypedDict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from factory import get_vertex_ai_llm
from core.vector_store import FAISSVectorStore
from models.schemas import QueryResponse, Source


class AgentState(TypedDict):
    query: str
    query_type: str
    sub_queries: List[str]
    search_results: Dict[str, List[Any]]
    final_answer: str
    reasoning: str
    sources: List[Source]
    error: Optional[str]


class FinancialAgent:
    """LangGraph-based agent for financial Q&A with query decomposition"""

    def __init__(self, vector_store: FAISSVectorStore):
        self.llm = get_vertex_ai_llm(temperature=0.3)
        self.vector_store = vector_store
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("classify_query", self._classify_query)
        graph.add_node("decompose_query", self._decompose_query)
        graph.add_node("execute_searches", self._execute_searches)
        graph.add_node("synthesize_answer", self._synthesize_answer)

        # Define edges
        graph.set_entry_point("classify_query")

        graph.add_conditional_edges(
            "classify_query",
            self._should_decompose,
            {
                "simple": "execute_searches",
                "complex": "decompose_query"
            }
        )

        graph.add_edge("decompose_query", "execute_searches")
        graph.add_edge("execute_searches", "synthesize_answer")
        graph.add_edge("synthesize_answer", END)

        return graph.compile()

    def _classify_query(self, state: AgentState) -> AgentState:
        """Classify query as simple or complex"""
        query = state["query"]

        classification_prompt = f"""
        Analyze this financial query and classify it as either "simple" or "complex":

        Query: {query}

        Classification criteria:
        - Simple: Single company, single metric, single year (e.g., "What was Microsoft's revenue in 2023?")
        - Complex: Multiple companies, comparisons, calculations, or multi-step reasoning required

        Examples:
        - Simple: "What was NVIDIA's total revenue in 2023?"
        - Complex: "Which company had the highest operating margin in 2023?"
        - Complex: "How did Microsoft's cloud revenue grow from 2022 to 2023?"

        Respond with just "simple" or "complex".
        """

        try:
            response = self.llm.invoke([HumanMessage(content=classification_prompt)])
            query_type = response.content.strip().lower()

            if query_type not in ["simple", "complex"]:
                query_type = "complex"  # Default to complex for safety

            state["query_type"] = query_type
            print(f"Query classified as: {query_type}")

        except Exception as e:
            print(f"Error in query classification: {e}")
            state["query_type"] = "complex"
            state["error"] = f"Classification error: {e}"

        return state

    def _should_decompose(self, state: AgentState) -> str:
        """Determine if query should be decomposed"""
        return state["query_type"]

    def _decompose_query(self, state: AgentState) -> AgentState:
        """Decompose complex query into sub-queries"""
        query = state["query"]

        decomposition_prompt = f"""
        Break down this complex financial query into specific sub-queries that can be answered independently:

        Original Query: {query}

        Guidelines:
        - Create specific, searchable sub-queries
        - Focus on concrete financial metrics (revenue, margin, etc.)
        - Include company name and year when possible
        - For comparisons, create separate queries for each company
        - For growth calculations, query both years separately

        Examples:
        Query: "Which company had the highest operating margin in 2023?"
        Sub-queries:
        1. Microsoft operating margin 2023
        2. Google operating margin 2023
        3. NVIDIA operating margin 2023

        Query: "How did NVIDIA's data center revenue grow from 2022 to 2023?"
        Sub-queries:
        1. NVIDIA data center revenue 2022
        2. NVIDIA data center revenue 2023

        Respond with a JSON array of sub-queries:
        ["sub-query 1", "sub-query 2", ...]
        """

        try:
            response = self.llm.invoke([HumanMessage(content=decomposition_prompt)])
            content = response.content.strip()

            # Parse JSON response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()

            sub_queries = json.loads(content)
            state["sub_queries"] = sub_queries
            print(f"Decomposed into {len(sub_queries)} sub-queries: {sub_queries}")

        except Exception as e:
            print(f"Error in query decomposition: {e}")
            # Fallback: use original query
            state["sub_queries"] = [query]
            state["error"] = f"Decomposition error: {e}"

        return state

    def _execute_searches(self, state: AgentState) -> AgentState:
        """Execute vector searches for queries"""
        # For simple queries, use the original query; for complex queries, use sub-queries
        if state["query_type"] == "simple":
            queries = [state["query"]]
            # Set sub_queries for response tracking
            state["sub_queries"] = [state["query"]]
        else:
            queries = state.get("sub_queries", [state["query"]])

        search_results = {}
        all_sources = []

        for query in queries:
            try:
                print(f"Searching for: {query}")
                results = self.vector_store.search(query, k=5)

                # Convert results to serializable format
                search_data = []
                for chunk, score in results:
                    source = self.vector_store.chunk_to_source(chunk, score)
                    search_data.append({
                        "content": chunk.content,
                        "score": score,
                        "company": chunk.metadata.company,
                        "year": chunk.metadata.year,
                        "section": chunk.section,
                        "page": chunk.page_number
                    })
                    all_sources.append(source)

                search_results[query] = search_data
                print(f"Found {len(search_data)} results for: {query}")

            except Exception as e:
                print(f"Error searching for '{query}': {e}")
                search_results[query] = []

        state["search_results"] = search_results
        state["sources"] = all_sources
        return state

    def _synthesize_answer(self, state: AgentState) -> AgentState:
        """Synthesize final answer from search results"""
        original_query = state["query"]
        search_results = state["search_results"]

        # Prepare context from search results
        context_parts = []
        for query, results in search_results.items():
            context_parts.append(f"Search: {query}")
            for i, result in enumerate(results[:3]):  # Limit to top 3 per query
                context_parts.append(f"Result {i+1}: {result['content'][:500]}...")
            context_parts.append("")

        context = "\n".join(context_parts)

        synthesis_prompt = f"""You are a financial analyst. Based on the search results, answer the question in JSON format.

Question: {original_query}

Search Results:
{context}

Instructions:
1. Analyze the search results for relevant financial information
2. Extract specific numbers, percentages, and facts when available
3. If no relevant data is found, state that clearly
4. Respond with ONLY valid JSON in this format:

{{"answer": "your detailed answer with specific numbers", "reasoning": "explain how you derived this answer"}}

Example response:
{{"answer": "Microsoft's total revenue in 2023 was $211.9 billion, representing a 7% increase from 2022.", "reasoning": "This information was found in Microsoft's 2023 10-K filing in the consolidated statements of income section."}}

IMPORTANT: Return ONLY the JSON object, no other text or formatting."""

        try:
            response = self.llm.invoke([HumanMessage(content=synthesis_prompt)])
            content = response.content.strip()

            # Clean JSON response
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '').strip()
            elif content.startswith('```'):
                content = content.replace('```', '').strip()

            # Clean and parse JSON response
            print(f"Raw LLM response: {content[:100]}...")

            # Remove any markdown formatting
            if content.startswith('```'):
                content = content.split('```')[1] if '```' in content else content
                if content.startswith('json'):
                    content = content[4:].strip()

            # Try to parse JSON
            try:
                result = json.loads(content)
                state["final_answer"] = result.get("answer", "Unable to determine answer from available data")
                state["reasoning"] = result.get("reasoning", "Analysis based on search results")
                print(f"Successfully parsed JSON response")

            except json.JSONDecodeError as e:
                print(f"JSON parsing failed: {e}")
                print(f"Attempting fallback parsing...")

                # Fallback 1: Extract JSON with regex
                import re
                json_match = re.search(r'\{[^{}]*"answer"[^{}]*"reasoning"[^{}]*\}', content, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\{.*?\}', content, re.DOTALL)

                if json_match:
                    try:
                        json_str = json_match.group()
                        result = json.loads(json_str)
                        state["final_answer"] = result.get("answer", "Unable to extract answer")
                        state["reasoning"] = result.get("reasoning", "Extracted from partial JSON")
                        print(f"Fallback JSON parsing successful")
                    except:
                        # Fallback 2: Create structured response from raw content
                        if content and len(content.strip()) > 10:
                            state["final_answer"] = content.strip()[:500]
                            state["reasoning"] = "Direct LLM response (JSON parsing failed)"
                        else:
                            state["final_answer"] = "Unable to generate answer from search results"
                            state["reasoning"] = "No valid response received"
                        print(f"Using raw content as fallback")
                else:
                    # Fallback 3: Generate answer from search context if available
                    if search_results and any(results for results in search_results.values()):
                        # Extract some relevant content from search results
                        sample_content = ""
                        for query, results in search_results.items():
                            if results:
                                sample_content += f"From search '{query}': {results[0]['content'][:200]}... "
                                break

                        state["final_answer"] = f"Based on available data: {sample_content}"
                        state["reasoning"] = "Generated from search results due to synthesis failure"
                        print(f"Using search context as fallback")
                    else:
                        state["final_answer"] = "Unable to find relevant information in the search results"
                        state["reasoning"] = "No search results available for analysis"
                        print(f"No search results available")

        except Exception as e:
            print(f"Error in answer synthesis: {e}")
            state["final_answer"] = "Unable to synthesize answer due to processing error"
            state["reasoning"] = f"Synthesis error: {e}"
            if not state.get("error"):
                state["error"] = f"Synthesis error: {e}"

        return state

    def process_query(self, query: str) -> QueryResponse:
        """Process a query through the agent workflow"""
        print(f"Processing query: {query}")

        initial_state = AgentState(
            query=query,
            query_type="",
            sub_queries=[],
            search_results={},
            final_answer="",
            reasoning="",
            sources=[],
            error=None
        )

        try:
            # Run the graph
            final_state = self.graph.invoke(initial_state)

            # Create response
            response = QueryResponse(
                query=query,
                answer=final_state["final_answer"],
                reasoning=final_state["reasoning"],
                sub_queries=final_state.get("sub_queries", [query]),
                sources=final_state.get("sources", [])
            )

            return response

        except Exception as e:
            print(f"Error processing query: {e}")
            return QueryResponse(
                query=query,
                answer=f"Error processing query: {e}",
                reasoning="Processing failed due to system error",
                sub_queries=[query],
                sources=[]
            )


if __name__ == "__main__":
    # Test the agent
    from core.vector_store import FAISSVectorStore

    vector_store = FAISSVectorStore()
    agent = FinancialAgent(vector_store)

    # Test queries
    test_queries = [
        "What was Microsoft's total revenue in 2023?",
        "Which company had the highest operating margin in 2023?",
        "How did NVIDIA's data center revenue grow from 2022 to 2023?"
    ]

    for query in test_queries:
        print(f"\n{'='*50}")
        response = agent.process_query(query)
        print(f"Query: {response.query}")
        print(f"Answer: {response.answer}")
        print(f"Sub-queries: {response.sub_queries}")
        print(f"Sources: {len(response.sources)}")