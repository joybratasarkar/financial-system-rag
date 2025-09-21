#!/usr/bin/env python3
"""
Financial Q&A System with Agent Capabilities
Main FastAPI application entry point
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from fastapi import FastAPI
from api.routes import router

app = FastAPI(
    title="Financial Q&A System",
    description="RAG-based financial Q&A system with agent capabilities for SEC 10-K filings",
    version="1.0.0"
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Financial Q&A System with Agent Capabilities",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)