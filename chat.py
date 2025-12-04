# chat.py
"""
Chat Application - The "Chat Window"
This script loads a pre-built index and answers questions using
Auto-Merging Retriever for intelligent context retrieval.

Run this after ingesting a PDF with ingest.py.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from llama_index.core import StorageContext, load_index_from_storage, Settings
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.response_synthesizers import get_response_synthesizer
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load API keys from .env file
load_dotenv()

# Configure Google GenAI as the default LLM and embedding model
Settings.llm = GoogleGenAI(model="gemini-2.0-flash")
Settings.embed_model = GoogleGenAIEmbedding(model_name="text-embedding-004")


def load_chat_engine(storage_name: str, verbose: bool = True):
    """
    Load a saved index and create an Auto-Merging query engine.
    
    Args:
        storage_name: Name of the stored index (from ingest.py)
        verbose: Print when chunks are merged
    
    Returns:
        RetrieverQueryEngine ready for queries
    """
    save_dir = f"./storage/{storage_name}"
    
    # Verify the index exists
    if not os.path.exists(save_dir):
        available = list_available_papers()
        raise FileNotFoundError(
            f"Index not found: {save_dir}\n"
            f"Available papers: {available if available else 'None - run ingest.py first'}"
        )
    
    print(f"\n📂 Loading index from: {save_dir}")
    
    # Step 1: Load the saved index from disk (this is fast!)
    storage_context = StorageContext.from_defaults(persist_dir=save_dir)
    index = load_index_from_storage(storage_context)
    
    print("✅ Index loaded successfully!")
    
    # Step 2: Build the Auto-Merging Retriever
    # This retriever automatically "zooms out" to parent chunks when
    # multiple child chunks from the same section are relevant
    base_retriever = index.as_retriever(similarity_top_k=6)
    
    retriever = AutoMergingRetriever(
        base_retriever,
        index.storage_context,
        verbose=verbose  # Prints when it merges chunks
    )
    
    # Step 3: Create the query engine with a response synthesizer
    response_synthesizer = get_response_synthesizer(
        response_mode="compact"  # Combines chunks before sending to LLM
    )
    
    query_engine = RetrieverQueryEngine.from_args(
        retriever,
        response_synthesizer=response_synthesizer
    )
    
    print("🚀 Chat engine ready!\n")
    return query_engine


def list_available_papers() -> list:
    """List all available processed papers."""
    storage_path = Path("./storage")
    if not storage_path.exists():
        return []
    return [d.name for d in storage_path.iterdir() if d.is_dir()]


def chat_loop(engine):
    """Interactive chat loop."""
    print("="*60)
    print("💬 PAPER CHAT - Ask questions about your paper")
    print("="*60)
    print("Type 'quit' or 'exit' to stop\n")
    
    while True:
        try:
            query = input("🔍 Your question: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Goodbye!")
                break
            
            print("\n⏳ Thinking...\n")
            
            # Get response
            response = engine.query(query)
            
            # Print the answer
            print("="*60)
            print("📝 ANSWER:")
            print("="*60)
            print(f"\n{response}\n")
            
            # Print source nodes (evidence)
            if response.source_nodes:
                print("-"*60)
                print("📚 SOURCES (Evidence):")
                print("-"*60)
                for i, node in enumerate(response.source_nodes, 1):
                    score = getattr(node, 'score', 'N/A')
                    text_preview = node.text[:200].replace('\n', ' ')
                    print(f"\n[{i}] (Score: {score:.3f})" if isinstance(score, float) else f"\n[{i}]")
                    print(f"    {text_preview}...")
            
            print("\n" + "="*60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def single_query(engine, query: str) -> dict:
    """
    Single query function for API integration.
    
    Returns:
        dict with 'answer' and 'sources'
    """
    response = engine.query(query)
    
    sources = []
    for node in response.source_nodes:
        sources.append({
            "text": node.text[:500],
            "score": getattr(node, 'score', None),
            "metadata": node.metadata
        })
    
    return {
        "answer": str(response),
        "sources": sources
    }


if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("📚 PAPER SUMMARIZER - Chat Interface")
    print("="*60 + "\n")
    
    # List available papers
    available = list_available_papers()
    
    if not available:
        print("❌ No processed papers found!")
        print("   First run: python ingest.py <path_to_pdf>")
        sys.exit(1)
    
    print("📁 Available papers:")
    for i, paper in enumerate(available, 1):
        print(f"   {i}. {paper}")
    print()
    
    # Get storage name from argument or prompt
    if len(sys.argv) > 1:
        storage_name = sys.argv[1]
    else:
        if len(available) == 1:
            storage_name = available[0]
            print(f"📄 Auto-selecting: {storage_name}\n")
        else:
            try:
                choice = input("Enter paper name or number: ").strip()
                if choice.isdigit():
                    storage_name = available[int(choice) - 1]
                else:
                    storage_name = choice
            except (IndexError, ValueError):
                print("❌ Invalid selection")
                sys.exit(1)
    
    # Load the chat engine
    try:
        engine = load_chat_engine(storage_name)
        
        # Start interactive chat
        chat_loop(engine)
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
