#!/usr/bin/env python3
"""
Financial Q&A System with Agent Capabilities
Main FastAPI application entry point
"""

import sys
import os
from pathlib import Path

# Add project root to Python path FIRST - before any local imports
project_root = Path(__file__).parent.resolve()



# Debug: Print paths for deployment troubleshooting
print(f"DEBUG: Project root: {project_root}")
print(f"DEBUG: Current working dir: {os.getcwd()}")
print(f"DEBUG: __file__: {__file__}")
print(f"DEBUG: sys.path before: {sys.path[:3]}")

# Add comprehensive paths for deployment compatibility
paths_to_add = [
    str(project_root),
    str(project_root / "api"),
    str(project_root / "core"),
    str(project_root / "models"),
    "/app",  # Render deployment path
    "/app/api",
    "/app/core",
    "/app/models",
    os.getcwd(),  # Current working directory
    os.path.join(os.getcwd(), "api"),
    os.path.join(os.getcwd(), "core"),
    os.path.join(os.getcwd(), "models")
]

for path in paths_to_add:
    if path not in sys.path:
        sys.path.insert(0, path)

print(f"DEBUG: sys.path after: {sys.path[:8]}")

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