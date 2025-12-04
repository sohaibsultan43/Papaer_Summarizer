# 📚 Paper Summarizer

An intelligent research paper analyzer using LlamaParse and LlamaIndex with hierarchical chunking and auto-merging retrieval, powered by Google Gemini AI.

## Features

- **LlamaParse**: Layout-aware PDF parsing that preserves tables, headers, and structure
- **Hierarchical Chunking**: Parent-child chunk structure for better context
- **Auto-Merging Retriever**: Automatically "zooms out" to larger context when needed
- **Gemini AI**: Uses gemini-2.0-flash for chat and text-embedding-004 for embeddings
- **React Frontend**: Modern UI with Tailwind CSS
- **Persistent Storage**: Process once, chat forever

## 🚀 Deployment

### Option 1: Deploy Backend on Render

1. Create a new **Web Service** on [Render](https://render.com)
2. Connect your GitHub repo: `sohaibsultan43/Papaer_Summarizer`
3. Configure:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn api:app --host 0.0.0.0 --port $PORT`
4. Set environment variables:
   - `LLAMA_CLOUD_API_KEY`: Your LlamaCloud API key
   - `GOOGLE_API_KEY`: Your Google AI API key
5. Deploy!

### Option 2: Deploy Frontend on Vercel

1. Go to [Vercel](https://vercel.com) and import your repo
2. Set **Root Directory** to `frontend`
3. Set environment variable:
   - `VITE_API_URL`: Your Render backend URL (e.g., `https://paper-summarizer.onrender.com`)
4. Deploy!

## 💻 Local Development

### 1. Clone and Setup

```bash
git clone https://github.com/sohaibsultan43/Papaer_Summarizer.git
cd Papaer_Summarizer

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file:

```env
LLAMA_CLOUD_API_KEY=llx-your-key-here
GOOGLE_API_KEY=your-google-ai-key-here
```

**Get your keys:**
- **LlamaCloud**: [cloud.llamaindex.ai](https://cloud.llamaindex.ai) → API Key → Generate New Key
- **Google AI**: [aistudio.google.com](https://aistudio.google.com/app/apikey)

### 3. Run the Backend

```bash
python api.py
```

Backend will be available at `http://localhost:8000`

### 4. Run the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:5173`

## 📁 File Structure

```
Paper_Summarizer/
├── api.py              # FastAPI backend
├── ingest.py           # PDF processing (used by API)
├── chat.py             # CLI chat interface
├── requirements.txt    # Python dependencies
├── Procfile            # For Render deployment
├── .env                # API keys (not committed)
├── storage/            # Saved indexes (per paper)
├── uploads/            # Uploaded PDFs
├── Papers/             # Sample papers
└── frontend/           # React + Vite frontend
    ├── src/
    │   ├── App.jsx     # Main React component
    │   └── api.js      # API client
    ├── vercel.json     # Vercel config
    └── package.json
```

## 🔧 How It Works

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

## 🛠️ API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/papers` | GET | List all processed papers |
| `/upload` | POST | Upload and process a new PDF |
| `/chat` | POST | Ask a question about a paper |
| `/papers/{id}` | DELETE | Delete a paper and its index |

## 📝 CLI Usage

### Process a PDF manually

```bash
python ingest.py path/to/paper.pdf
```

### Chat via command line

```bash
python chat.py paper_name
```

## 🐛 Troubleshooting

**"Index not found"**: Upload a PDF first via the web UI or run `ingest.py`.

**"API key not found"**: Make sure your `.env` file has valid keys.

**Slow parsing**: LlamaParse processes asynchronously. Large PDFs may take 1-2 minutes.

## 📊 Free Tier Limits

- **LlamaParse**: 1,000 pages/day
- **Google AI (Gemini)**: Generous free tier for development
