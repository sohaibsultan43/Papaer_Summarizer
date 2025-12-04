# ingest.py
"""
PDF Ingestion Script - The "Background Worker"
This script parses a PDF using LlamaParse, creates hierarchical chunks,
and saves the index to disk for fast loading later.

Run this when a user uploads a PDF.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from llama_parse import LlamaParse
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load API keys from .env file
load_dotenv()

# Configure Google GenAI as the default embedding model
Settings.embed_model = GoogleGenAIEmbedding(model_name="text-embedding-004")

def process_paper(pdf_path: str, storage_name: str) -> str:
    """
    Process a PDF paper and create a searchable index.
    
    Args:
        pdf_path: Path to the PDF file
        storage_name: Unique name for storing the index (e.g., "user_123_paper_1")
    
    Returns:
        Path to the saved index directory
    
    Steps:
        1. Parses PDF using LlamaParse (Layout-aware, keeps tables/headers)
        2. Splits into Parent-Child chunks (hierarchical)
        3. Saves index to ./storage folder
    """
    
    # Verify the PDF exists
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    print(f"\n{'='*60}")
    print(f"📄 PARSING: {pdf_path}")
    print(f"{'='*60}\n")
    
    # Step 1: Parse PDF to Markdown (preserves structure, tables, headers)
    print("🔍 Step 1/3: Parsing PDF with LlamaParse...")
    parser = LlamaParse(
        result_type="markdown",  # Converts to markdown to keep formatting
        verbose=True,
        language="en"
    )
    
    parsed_docs = parser.load_data(pdf_path)
    
    # Convert to LlamaIndex Document format
    documents = [
        Document(
            text=doc.text, 
            metadata={**doc.metadata, "source": pdf_path}
        ) 
        for doc in parsed_docs
    ]
    
    print(f"✅ Parsed {len(documents)} document(s) from PDF\n")
    
    # Step 2: Create Hierarchical Chunks (Parent -> Child -> Leaf)
    print("🔨 Step 2/3: Creating hierarchical chunks...")
    
    # Chunk sizes: 1024 (Parent) -> 512 (Middle) -> 256 (Leaf/Search Unit)
    # This allows the retriever to "zoom out" when multiple small chunks match
    node_parser = HierarchicalNodeParser.from_defaults(
        chunk_sizes=[1024, 512, 256]
    )
    
    nodes = node_parser.get_nodes_from_documents(documents)
    leaf_nodes = get_leaf_nodes(nodes)  # Only index the smallest chunks for search
    
    print(f"✅ Created {len(nodes)} total nodes ({len(leaf_nodes)} leaf nodes for indexing)\n")
    
    # Step 3: Build Index and Save
    print("💾 Step 3/3: Building index and saving to disk...")
    
    # Create storage context - stores ALL nodes (needed to find parents later)
    storage_context = StorageContext.from_defaults()
    storage_context.docstore.add_documents(nodes)
    
    # Create vector index from leaf nodes only
    index = VectorStoreIndex(
        leaf_nodes,
        storage_context=storage_context,
        show_progress=True
    )
    
    # Save to disk
    save_dir = f"./storage/{storage_name}"
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=save_dir)
    
    print(f"\n{'='*60}")
    print(f"✅ SUCCESS! Index saved to: {save_dir}")
    print(f"{'='*60}\n")
    
    return save_dir


def list_processed_papers() -> list:
    """List all processed papers in the storage directory."""
    storage_path = Path("./storage")
    if not storage_path.exists():
        return []
    return [d.name for d in storage_path.iterdir() if d.is_dir()]


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("📚 PAPER SUMMARIZER - PDF Ingestion Tool")
    print("="*60 + "\n")
    
    # Check if PDF path is provided as argument
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        # Use filename (without extension) as storage name
        storage_name = Path(pdf_file).stem.replace(" ", "_").lower()
    else:
        # Default example - change this to your PDF path
        pdf_file = "example_paper.pdf"
        storage_name = "example_paper"
        
        print("Usage: python ingest.py <path_to_pdf>")
        print(f"No PDF provided. Using default: {pdf_file}\n")
    
    # Process the paper
    try:
        save_path = process_paper(pdf_file, storage_name)
        print(f"📁 Your paper is ready! Use this storage name in chat.py:")
        print(f"   storage_name = \"{storage_name}\"")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("\nPlease provide a valid PDF path:")
        print("   python ingest.py path/to/your/paper.pdf")
    except Exception as e:
        print(f"❌ Error processing paper: {e}")
        raise
