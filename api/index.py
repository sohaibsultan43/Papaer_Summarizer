"""
Vercel Serverless Function - FastAPI Backend
"""
import os
import json
import shutil
import asyncio
import nest_asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

load_dotenv()

# LlamaIndex imports
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
    Document
)
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_cloud_services import LlamaParse

# Configure Gemini
Settings.llm = GoogleGenAI(model="gemini-2.0-flash")
Settings.embed_model = GoogleGenAIEmbedding(model_name="text-embedding-004")

app = FastAPI(title="Paper Summarizer API")

# CORS for Vercel frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Use /tmp for Vercel (serverless has limited writable space)
STORAGE_DIR = Path("/tmp/storage")
UPLOAD_DIR = Path("/tmp/uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Thread pool for sync operations
executor = ThreadPoolExecutor(max_workers=2)


class ChatRequest(BaseModel):
    paper_id: str
    question: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]


def process_paper(pdf_path: str, storage_name: str) -> dict:
    """Process a PDF and create the index (synchronous)"""
    parser = LlamaParse(result_type="markdown")
    documents = parser.load_data(pdf_path)
    
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=[1024, 512, 256])
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)
    
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)
    
    index = VectorStoreIndex(leaf_nodes, storage_context=storage_context)
    
    storage_path = STORAGE_DIR / storage_name
    index.storage_context.persist(persist_dir=str(storage_path))
    
    return {"leaf_nodes": len(leaf_nodes), "total_nodes": len(nodes)}


@app.get("/")
async def root():
    return {"status": "ok", "message": "Paper Summarizer API"}


@app.get("/papers")
async def list_papers():
    """List all processed papers"""
    papers = []
    if STORAGE_DIR.exists():
        for folder in STORAGE_DIR.iterdir():
            if folder.is_dir():
                papers.append({
                    "id": folder.name,
                    "name": folder.name.replace("_", " ").title()
                })
    return {"papers": papers}


@app.post("/upload")
async def upload_paper(file: UploadFile = File(...)):
    """Upload and process a PDF"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    # Save uploaded file
    safe_name = file.filename.replace(" ", "_").replace("-", "_").lower()
    storage_name = safe_name.replace(".pdf", "")
    file_path = UPLOAD_DIR / safe_name
    
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    # Process in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            executor, 
            process_paper, 
            str(file_path), 
            storage_name
        )
        return {
            "success": True,
            "paper_id": storage_name,
            "message": f"Processed {result['leaf_nodes']} chunks"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Chat with a processed paper"""
    storage_path = STORAGE_DIR / request.paper_id
    
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found. Please upload it first.")
    
    try:
        # Load index
        storage_context = StorageContext.from_defaults(persist_dir=str(storage_path))
        index = load_index_from_storage(storage_context)
        
        # Create auto-merging retriever
        base_retriever = index.as_retriever(similarity_top_k=6)
        retriever = AutoMergingRetriever(
            base_retriever,
            storage_context=storage_context,
            verbose=True
        )
        
        # Query
        query_engine = RetrieverQueryEngine.from_args(retriever)
        response = query_engine.query(request.question)
        
        # Extract sources
        sources = []
        for node in response.source_nodes:
            text = node.node.get_content()[:200] + "..." if len(node.node.get_content()) > 200 else node.node.get_content()
            sources.append(text)
        
        return ChatResponse(
            answer=str(response),
            sources=sources
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/papers/{paper_id}")
async def delete_paper(paper_id: str):
    """Delete a paper and its index"""
    storage_path = STORAGE_DIR / paper_id
    
    if not storage_path.exists():
        raise HTTPException(status_code=404, detail="Paper not found")
    
    shutil.rmtree(storage_path)
    return {"success": True, "message": f"Deleted {paper_id}"}
