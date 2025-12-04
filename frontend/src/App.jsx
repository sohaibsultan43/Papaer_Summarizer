import { useState, useRef, useEffect } from 'react';
import { Upload, Send, FileText, Trash2, MessageSquare, Loader2, ChevronDown, ChevronUp } from 'lucide-react';
import { fetchPapers, uploadPaper, sendMessage, deletePaper } from './api';

function App() {
  const [papers, setPapers] = useState([]);
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load papers on mount
  useEffect(() => {
    loadPapers();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadPapers = async () => {
    try {
      const data = await fetchPapers();
      setPapers(data);
      if (data.length > 0 && !selectedPaper) {
        setSelectedPaper(data[0]);
      }
    } catch (err) {
      setError('Failed to load papers');
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setError(null);

    try {
      const result = await uploadPaper(file);
      await loadPapers();
      
      // Select the newly uploaded paper
      const newPapers = await fetchPapers();
      const newPaper = newPapers.find(p => p.id === result.paper_id);
      if (newPaper) {
        setSelectedPaper(newPaper);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || !selectedPaper || isLoading) return;

    const question = input.trim();
    setInput('');
    setMessages(prev => [...prev, { type: 'user', content: question }]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(selectedPaper.id, question);
      setMessages(prev => [...prev, {
        type: 'assistant',
        content: response.answer,
        sources: response.sources
      }]);
    } catch (err) {
      setError(err.message);
      setMessages(prev => [...prev, {
        type: 'error',
        content: err.message
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (paperId) => {
    if (!confirm('Are you sure you want to delete this paper?')) return;

    try {
      await deletePaper(paperId);
      await loadPapers();
      if (selectedPaper?.id === paperId) {
        setSelectedPaper(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-gray-100">
      {/* Sidebar */}
      <div className="w-72 bg-gray-800 border-r border-gray-700 flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-400" />
            Paper Summarizer
          </h1>
        </div>

        {/* Upload Button */}
        <div className="p-4">
          <label className={`flex items-center justify-center gap-2 w-full py-3 px-4 rounded-lg cursor-pointer transition-colors ${
            isUploading 
              ? 'bg-gray-600 cursor-not-allowed' 
              : 'bg-blue-600 hover:bg-blue-700'
          }`}>
            {isUploading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <Upload className="w-5 h-5" />
                Upload PDF
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleUpload}
              disabled={isUploading}
              className="hidden"
            />
          </label>
        </div>

        {/* Papers List */}
        <div className="flex-1 overflow-y-auto p-2">
          <p className="text-xs text-gray-500 uppercase tracking-wide px-2 mb-2">
            Your Papers
          </p>
          {papers.length === 0 ? (
            <p className="text-sm text-gray-500 px-2">
              No papers yet. Upload a PDF to get started.
            </p>
          ) : (
            papers.map((paper) => (
              <div
                key={paper.id}
                className={`group flex items-center gap-2 p-3 rounded-lg cursor-pointer mb-1 transition-colors ${
                  selectedPaper?.id === paper.id
                    ? 'bg-gray-700'
                    : 'hover:bg-gray-700/50'
                }`}
                onClick={() => {
                  setSelectedPaper(paper);
                  setMessages([]);
                }}
              >
                <MessageSquare className="w-4 h-4 text-gray-400 flex-shrink-0" />
                <span className="flex-1 text-sm truncate">{paper.name}</span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(paper.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-600 rounded transition-all"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        {selectedPaper && (
          <div className="p-4 border-b border-gray-700 bg-gray-800">
            <h2 className="font-semibold">{selectedPaper.name}</h2>
            <p className="text-sm text-gray-400">Ask questions about this paper</p>
          </div>
        )}

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!selectedPaper ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <FileText className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg">Select a paper to start chatting</p>
              <p className="text-sm">or upload a new PDF</p>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <MessageSquare className="w-16 h-16 mb-4 opacity-50" />
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm">Ask anything about the paper</p>
              <div className="mt-6 grid gap-2">
                {[
                  "What is the main contribution?",
                  "Summarize the methodology",
                  "What are the key results?"
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-sm transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <MessageBubble key={idx} message={msg} />
            ))
          )}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mx-4 mb-2 p-3 bg-red-900/50 border border-red-700 rounded-lg text-red-200 text-sm">
            {error}
          </div>
        )}

        {/* Input Area */}
        {selectedPaper && (
          <div className="p-4 border-t border-gray-700 bg-gray-800">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask a question about the paper..."
                disabled={isLoading}
                className="flex-1 px-4 py-3 bg-gray-700 border border-gray-600 rounded-lg focus:outline-none focus:border-blue-500 disabled:opacity-50"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded-lg transition-colors"
              >
                <Send className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MessageBubble({ message }) {
  const [showSources, setShowSources] = useState(false);

  if (message.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[70%] bg-blue-600 rounded-2xl rounded-tr-md px-4 py-3">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="max-w-[70%] bg-red-900/50 border border-red-700 rounded-2xl rounded-tl-md px-4 py-3 text-red-200">
          {message.content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start">
      <div className="max-w-[80%] bg-gray-800 rounded-2xl rounded-tl-md px-4 py-3">
        <div className="whitespace-pre-wrap">{message.content}</div>
        
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 pt-3 border-t border-gray-700">
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-300"
            >
              {showSources ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {message.sources.length} sources
            </button>
            
            {showSources && (
              <div className="mt-2 space-y-2">
                {message.sources.map((source, idx) => (
                  <div key={idx} className="text-xs bg-gray-700/50 rounded-lg p-2">
                    <span className="text-blue-400">Score: {source.score}</span>
                    <p className="text-gray-400 mt-1">{source.text}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
