# 📚 Paper Summarizer

An intelligent research paper analyzer using LlamaParse and LlamaIndex with hierarchical chunking and auto-merging retrieval.

## Features

- **LlamaParse**: Layout-aware PDF parsing that preserves tables, headers, and structure
- **Hierarchical Chunking**: Parent-child chunk structure for better context
- **Auto-Merging Retriever**: Automatically "zooms out" to larger context when needed
- **Persistent Storage**: Process once, chat forever

## Setup

### 1. Install Dependencies

```bash
pip install llama-index llama-parse llama-index-retrievers-auto-merging python-dotenv
```

### 2. Configure API Keys

Edit the `.env` file with your actual API keys:

```env
LLAMA_CLOUD_API_KEY=llx-your-key-here
OPENAI_API_KEY=sk-your-key-here
```

**Get your keys:**
- **LlamaCloud**: [cloud.llamaindex.ai](https://cloud.llamaindex.ai) → API Key → Generate New Key
- **OpenAI**: [platform.openai.com](https://platform.openai.com/api-keys)

## Usage

### Step 1: Process a PDF

```bash
python ingest.py path/to/your/paper.pdf
```

This will:
1. Parse the PDF with LlamaParse (preserves layout)
2. Create hierarchical chunks (1024 → 512 → 256 tokens)
3. Save the index to `./storage/<paper_name>/`

### Step 2: Chat with the Paper

```bash
python chat.py
```

Or specify a paper directly:
```bash
python chat.py paper_name
```

## File Structure

```
Paper_Summarizer/
├── .env                 # API keys (not committed to git)
├── ingest.py           # PDF processing script
├── chat.py             # Chat interface
├── storage/            # Saved indexes
│   └── paper_name/     # One folder per paper
└── README.md           # This file
```

## How It Works

### Hierarchical Chunking

```
                    ┌─────────────────────┐
                    │   Parent (1024)     │  ← Full context
                    └─────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌──────────┐    ┌──────────┐    ┌──────────┐
        │ Mid(512) │    │ Mid(512) │    │ Mid(512) │
        └──────────┘    └──────────┘    └──────────┘
              │               │               │
        ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐
        ▼           ▼   ▼           ▼   ▼           ▼
     ┌─────┐     ┌─────┐ ...                      ┌─────┐
     │Leaf │     │Leaf │  ← Search happens here  │Leaf │
     │(256)│     │(256)│                         │(256)│
     └─────┘     └─────┘                         └─────┘
```

### Auto-Merging Retrieval

When multiple leaf chunks from the same parent match your query, the retriever automatically "merges" up to return the parent chunk instead. This gives you better context without losing precision.

## API Integration

For integrating into your backend:

```python
from chat import load_chat_engine, single_query

# Load once at startup
engine = load_chat_engine("paper_name")

# Use in your API endpoint
result = single_query(engine, "What is the main contribution?")
print(result["answer"])
print(result["sources"])
```

## Troubleshooting

**"Index not found"**: Run `ingest.py` first to process your PDF.

**"API key not found"**: Make sure your `.env` file has valid keys.

**Slow parsing**: LlamaParse processes asynchronously. Large PDFs may take 1-2 minutes.

## Free Tier Limits

- **LlamaParse**: 1,000 pages/day (plenty for research papers)
- **OpenAI**: Pay-as-you-go (embeddings + completions)
