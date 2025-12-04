// Use /api for Vercel serverless, or custom URL for development
const API_URL = import.meta.env.VITE_API_URL || '/api';

export async function fetchPapers() {
  const response = await fetch(`${API_URL}/papers`);
  if (!response.ok) throw new Error('Failed to fetch papers');
  return response.json();
}

export async function uploadPaper(file) {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`${API_URL}/upload`, {
    method: 'POST',
    body: formData,
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload paper');
  }
  
  return response.json();
}

export async function sendMessage(paperId, question) {
  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      paper_id: paperId,
      question: question,
    }),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to send message');
  }
  
  return response.json();
}

export async function deletePaper(paperId) {
  const response = await fetch(`${API_URL}/papers/${paperId}`, {
    method: 'DELETE',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete paper');
  }
  
  return response.json();
}
