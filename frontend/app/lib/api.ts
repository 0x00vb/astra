const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user?: {
    id: string;
    email: string;
    full_name?: string;
  };
}

export interface ApiError {
  detail: string;
}

export async function registerUser(
  data: RegisterRequest
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || "Error al registrar usuario");
  }

  return response.json();
}

export async function loginUser(data: LoginRequest): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login/json`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || "Error al iniciar sesión");
  }

  return response.json();
}

export async function getCurrentUser(): Promise<AuthResponse["user"]> {
  const token = localStorage.getItem("access_token");
  if (!token) {
    throw new Error("No authentication token");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    if (response.status === 401) {
      localStorage.removeItem("access_token");
      throw new Error("Session expired");
    }
    const error: ApiError = await response.json();
    throw new Error(error.detail || "Error al obtener usuario");
  }

  return response.json();
}

export function logout() {
  localStorage.removeItem("access_token");
  window.location.href = "/login";
}

// Document & Ingestion APIs
export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "indexed" | "error";
  chunks_count: number;
  total_pages?: number | null;
  created_at: string;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  status: string;
  stats: {
    chunks: number;
    pages: number | null;
    characters: number;
  };
}

export interface IndexProgress {
  document_id: string;
  progress: number; // 0-100
  status: "pending" | "processing" | "indexed" | "error";
  chunks_processed: number;
  total_chunks: number;
}

export async function uploadDocument(
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const xhr = new XMLHttpRequest();

  return new Promise((resolve, reject) => {
    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        const progress = (e.loaded / e.total) * 100;
        onProgress(progress);
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch (e) {
          reject(new Error("Invalid response from server"));
        }
      } else {
        try {
          const error = JSON.parse(xhr.responseText);
          reject(new Error(error.detail || `Upload failed: ${xhr.statusText}`));
        } catch {
          reject(new Error(`Upload failed: ${xhr.statusText}`));
        }
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Upload failed")));

    xhr.open("POST", `${API_BASE_URL}/api/ingest/upload`);
    // Note: Backend doesn't require auth yet, but keeping structure for future
    const token = localStorage.getItem("access_token");
    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }
    xhr.send(formData);
  });
}

export async function getDocuments(): Promise<Document[]> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/api/ingest/documents`, {
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch documents" }));
    throw new Error(error.detail || "Failed to fetch documents");
  }

  return response.json();
}

export async function getIndexProgress(
  documentId: string
): Promise<IndexProgress> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/ingest/progress/${documentId}`,
    {
      headers,
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch progress" }));
    throw new Error(error.detail || "Failed to fetch progress");
  }

  return response.json();
}

export async function deleteDocument(documentId: string): Promise<void> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_BASE_URL}/api/ingest/document/${documentId}`,
    {
      method: "DELETE",
      headers,
    }
  );

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to delete document" }));
    throw new Error(error.detail || "Failed to delete document");
  }
}

// Chat & Query APIs
export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  reasoning_steps?: ReasoningStep[];
  timestamp: string;
}

export interface Citation {
  document_id: string;
  document_name: string;
  chunk_id: string;
  chunk_text: string;
  page_number?: number;
  chunk_range?: [number, number];
  relevance_score: number;
}

export interface ReasoningStep {
  step_id: string;
  type: "thought" | "action" | "observation" | "final_answer";
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  query: string;
  document_ids?: string[];
  stream?: boolean;
}

export async function sendChatMessage(
  request: ChatRequest,
  onChunk?: (chunk: string) => void
): Promise<ChatMessage> {
  const token = localStorage.getItem("access_token");
  
  if (request.stream) {
    // Streaming response
    const response = await fetch(`${API_BASE_URL}/api/query/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ ...request, stream: true }),
    });

    if (!response.ok) {
      throw new Error("Chat request failed");
    }

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();
    let fullContent = "";

    if (reader) {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter((l) => l.trim());

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = JSON.parse(line.slice(6));
            if (data.content) {
              fullContent += data.content;
              if (onChunk) onChunk(data.content);
            }
          }
        }
      }
    }

    // Return final message (would need to parse citations/reasoning from final chunk)
    return {
      id: crypto.randomUUID(),
      role: "assistant",
      content: fullContent,
      timestamp: new Date().toISOString(),
    };
  } else {
    // Non-streaming response
    const response = await fetch(`${API_BASE_URL}/api/query/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      throw new Error("Chat request failed");
    }

    return response.json();
  }
}

// Dashboard Stats API
export interface DashboardStats {
  documents_indexed: number;
  total_tokens_processed: number;
  total_chunks: number;
  queries_processed: number;
  average_response_time?: number;
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}/api/health/stats`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch stats");
  }

  return response.json();
}

// Embeddings & Insights APIs
export interface EmbeddingPoint {
  x: number;
  y: number;
  chunk_id: string;
  document_id: string;
  document_name: string;
  chunk_text: string;
  cluster_id?: number;
}

export interface DocumentSummary {
  document_id: string;
  document_name: string;
  summary: string;
  key_topics: string[];
  word_count: number;
}

export interface WordCloudData {
  word: string;
  count: number;
}

export async function getEmbeddings2D(
  documentIds?: string[]
): Promise<EmbeddingPoint[]> {
  const token = localStorage.getItem("access_token");
  const params = documentIds
    ? `?document_ids=${documentIds.join(",")}`
    : "";
  const response = await fetch(
    `${API_BASE_URL}/api/embeddings/2d${params}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!response.ok) {
    throw new Error("Failed to fetch embeddings");
  }

  return response.json();
}

export async function getDocumentSummaries(): Promise<DocumentSummary[]> {
  const token = localStorage.getItem("access_token");
  const response = await fetch(`${API_BASE_URL}/api/embeddings/summaries`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch summaries");
  }

  return response.json();
}

export async function getWordCloud(
  documentIds?: string[]
): Promise<WordCloudData[]> {
  const token = localStorage.getItem("access_token");
  const params = documentIds
    ? `?document_ids=${documentIds.join(",")}`
    : "";
  const response = await fetch(`${API_BASE_URL}/api/embeddings/wordcloud${params}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to fetch word cloud");
  }

  return response.json();
}

// PDF Viewer API
export interface DocumentContent {
  document_id: string;
  filename?: string;
  total_chunks?: number;
  chunks?: Array<{
    chunk_id: number;
    text: string;
    start_char: number;
    end_char: number;
    page_number: number | null;
    token_count: number | null;
  }>;
}

export async function getDocumentContent(
  documentId: string,
  chunkId?: number
): Promise<DocumentContent> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const url = chunkId !== undefined
    ? `${API_BASE_URL}/api/ingest/document/${documentId}/content?chunk_id=${chunkId}`
    : `${API_BASE_URL}/api/ingest/document/${documentId}/content`;

  const response = await fetch(url, {
    headers,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch document content" }));
    throw new Error(error.detail || "Failed to fetch document content");
  }

  return response.json();
}

// Analytics APIs
export interface UserAnalytics {
  user_id: string;
  email: string;
  query_stats: {
    total_queries: number;
    total_tokens_used: number;
    average_latency_ms: number;
    average_chunks_retrieved: number;
    total_answer_length: number;
  };
  document_stats: {
    total_documents: number;
    total_size_bytes: number;
    total_chunks: number;
    total_characters: number;
    uploads_count: number;
    deletes_count: number;
  };
  usage_by_date: Array<{
    date: string;
    queries_count: number;
    documents_uploaded: number;
    tokens_used: number;
  }>;
  period_start: string;
  period_end: string;
}

export interface QueryHistoryItem {
  id: string;
  query_id: string;
  query_text: string;
  answer_length: number;
  chunks_retrieved: number;
  context_length: number;
  retrieval_latency_ms: number;
  llm_latency_ms: number;
  total_latency_ms: number;
  tokens_used: number | null;
  model_used: string | null;
  created_at: string;
}

export async function getUserAnalytics(days: number = 30): Promise<UserAnalytics> {
  const token = localStorage.getItem("access_token");
  if (!token) {
    throw new Error("No authentication token");
  }

  const response = await fetch(`${API_BASE_URL}/api/analytics/stats?days=${days}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch analytics" }));
    throw new Error(error.detail || "Failed to fetch analytics");
  }

  return response.json();
}

export async function getQueryHistory(limit: number = 100, skip: number = 0): Promise<QueryHistoryItem[]> {
  const token = localStorage.getItem("access_token");
  if (!token) {
    throw new Error("No authentication token");
  }

  const response = await fetch(`${API_BASE_URL}/api/analytics/queries?limit=${limit}&skip=${skip}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Failed to fetch query history" }));
    throw new Error(error.detail || "Failed to fetch query history");
  }

  return response.json();
}

