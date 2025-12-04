# api.py
"""
FastAPI Backend for Paper Summarizer
Provides REST endpoints for PDF upload, processing, and chat.
"""

import os
import shutil
import asyncio
import nest_asyncio
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

# Import ingestion function
from ingest import process_paper

# Load environment variables
load_dotenv()

# Configure Google GenAI
Settings.llm = GoogleGenAI(model="gemini-2.0-flash")
Settings.embed_model = GoogleGenAIEmbedding(model_name="text-embedding-004")

# Thread pool for running sync operations
executor = ThreadPoolExecutor(max_workers=2)

# FastAPI app
app = FastAPI(
    title="Paper Summarizer API",
    description="Upload research papers and chat with them using AI",
    version="1.0.0"
)

# CORS for frontend (allow all origins for ngrok)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for ngrok tunnels
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
UPLOAD_DIR = Path("./uploads")
STORAGE_DIR = Path("./storage")
UPLOAD_DIR.mkdir(exist_ok=True)

# Cache for loaded engines
_engine_cache: dict = {}


class ChatRequest(BaseModel):
    paper_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list


class PaperInfo(BaseModel):
    id: str
    name: str
    status: str


def get_engine(paper_id: str):
    """Get or create a query engine for a paper."""
    if paper_id in _engine_cache:
        return _engine_cache[paper_id]
    
    save_dir = STORAGE_DIR / paper_id
    if not save_dir.exists():
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
    
    # Load index
    storage_context = StorageContext.from_defaults(persist_dir=str(save_dir))
    index = load_index_from_storage(storage_context)
    
    # Build retriever with auto-merging
    base_retriever = index.as_retriever(similarity_top_k=6)
    retriever = AutoMergingRetriever(base_retriever, index.storage_context, verbose=False)
    
    # Create query engine
    response_synthesizer = get_response_synthesizer(response_mode="compact")
    engine = RetrieverQueryEngine.from_args(retriever, response_synthesizer=response_synthesizer)
    
    _engine_cache[paper_id] = engine
    return engine


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Paper Summarizer API is running"}


@app.get("/papers", response_model=list[PaperInfo])
async def list_papers():
    """List all processed papers."""
    papers = []
    if STORAGE_DIR.exists():
        for folder in STORAGE_DIR.iterdir():
            if folder.is_dir():
                papers.append(PaperInfo(
                    id=folder.name,
                    name=folder.name.replace("_", " ").title(),
                    status="ready"
                ))
    return papers


@app.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload and process a PDF paper."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Generate paper ID from filename
    paper_id = Path(file.filename).stem.replace(" ", "_").lower()
    
    # Check if already processed
    if (STORAGE_DIR / paper_id).exists():
        return {
            "status": "exists",
            "paper_id": paper_id,
            "message": f"Paper '{paper_id}' already processed"
        }
    
    # Save uploaded file
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # Process the paper in a thread to avoid event loop issues
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(executor, process_paper, str(file_path), paper_id)
        
        return {
            "status": "success",
            "paper_id": paper_id,
            "message": f"Paper processed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing paper: {str(e)}")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with a processed paper."""
    try:
        engine = get_engine(request.paper_id)
        response = engine.query(request.question)
        
        sources = []
        for node in response.source_nodes:
            sources.append({
                "text": node.text[:300] + "..." if len(node.text) > 300 else node.text,
                "score": round(getattr(node, 'score', 0), 3)
            })
        
        return ChatResponse(
            answer=str(response),
            sources=sources
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a processed paper."""
    save_dir = STORAGE_DIR / paper_id
    if not save_dir.exists():
        raise HTTPException(status_code=404, detail=f"Paper '{paper_id}' not found")
    
    # Remove from cache
    if paper_id in _engine_cache:
        del _engine_cache[paper_id]
    
    # Delete storage
    shutil.rmtree(save_dir)
    
    return {"status": "success", "message": f"Paper '{paper_id}' deleted"}


# Serve frontend static files
FRONTEND_DIR = Path("./frontend/dist")
if FRONTEND_DIR.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve the React frontend for all non-API routes."""
        file_path = FRONTEND_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
