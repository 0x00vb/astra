import { create } from "zustand";
import type {
  Document,
  ChatMessage,
  DashboardStats,
  IndexProgress,
  EmbeddingPoint,
  DocumentSummary,
  WordCloudData,
} from "../lib/api";

interface AppState {
  // Documents
  documents: Document[];
  selectedDocumentId: string | null;
  indexProgress: Record<string, IndexProgress>;
  
  // Chat
  messages: ChatMessage[];
  isStreaming: boolean;
  currentStreamingMessage: string | null;
  
  // Dashboard
  stats: DashboardStats | null;
  
  // Insights
  embeddings2D: EmbeddingPoint[];
  summaries: DocumentSummary[];
  wordCloud: WordCloudData[];
  
  // UI State
  activeTab: "chat" | "documents" | "insights";
  showReasoningPanel: boolean;
  showPDFViewer: boolean;
  
  // Actions
  setDocuments: (documents: Document[]) => void;
  addDocument: (document: Document) => void;
  updateDocument: (id: string, updates: Partial<Document>) => void;
  removeDocument: (id: string) => void;
  setSelectedDocumentId: (id: string | null) => void;
  setIndexProgress: (documentId: string, progress: IndexProgress) => void;
  
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (updates: Partial<ChatMessage>) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  appendStreamingContent: (chunk: string) => void;
  clearStreaming: () => void;
  
  setStats: (stats: DashboardStats) => void;
  
  setEmbeddings2D: (embeddings: EmbeddingPoint[]) => void;
  setSummaries: (summaries: DocumentSummary[]) => void;
  setWordCloud: (wordCloud: WordCloudData[]) => void;
  
  setActiveTab: (tab: "chat" | "documents" | "insights") => void;
  setShowReasoningPanel: (show: boolean) => void;
  setShowPDFViewer: (show: boolean) => void;
}

export const useStore = create<AppState>((set) => ({
  // Initial state
  documents: [],
  selectedDocumentId: null,
  indexProgress: {},
  messages: [],
  isStreaming: false,
  currentStreamingMessage: null,
  stats: null,
  embeddings2D: [],
  summaries: [],
  wordCloud: [],
  activeTab: "chat",
  showReasoningPanel: false,
  showPDFViewer: false,
  
  // Document actions
  setDocuments: (documents) => set({ documents }),
  addDocument: (document) =>
    set((state) => ({ documents: [...state.documents, document] })),
  updateDocument: (id, updates) =>
    set((state) => ({
      documents: state.documents.map((doc) =>
        doc.id === id ? { ...doc, ...updates } : doc
      ),
    })),
  removeDocument: (id) =>
    set((state) => ({
      documents: state.documents.filter((doc) => doc.id !== id),
      selectedDocumentId: state.selectedDocumentId === id ? null : state.selectedDocumentId,
    })),
  setSelectedDocumentId: (id) => set({ selectedDocumentId: id }),
  setIndexProgress: (documentId, progress) =>
    set((state) => ({
      indexProgress: { ...state.indexProgress, [documentId]: progress },
    })),
  
  // Chat actions
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  updateLastMessage: (updates) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0) {
        messages[messages.length - 1] = {
          ...messages[messages.length - 1],
          ...updates,
        };
      }
      return { messages };
    }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  appendStreamingContent: (chunk) =>
    set((state) => {
      const messages = [...state.messages];
      if (messages.length > 0 && messages[messages.length - 1].role === "assistant") {
        const lastMessage = messages[messages.length - 1];
        messages[messages.length - 1] = {
          ...lastMessage,
          content: (lastMessage.content || "") + chunk,
        };
      } else {
        messages.push({
          id: crypto.randomUUID(),
          role: "assistant",
          content: chunk,
          timestamp: new Date().toISOString(),
        });
      }
      return { messages, currentStreamingMessage: chunk };
    }),
  clearStreaming: () => set({ isStreaming: false, currentStreamingMessage: null }),
  
  // Dashboard actions
  setStats: (stats) => set({ stats }),
  
  // Insights actions
  setEmbeddings2D: (embeddings) => set({ embeddings2D: embeddings }),
  setSummaries: (summaries) => set({ summaries }),
  setWordCloud: (wordCloud) => set({ wordCloud }),
  
  // UI actions
  setActiveTab: (tab) => set({ activeTab: tab }),
  setShowReasoningPanel: (show) => set({ showReasoningPanel: show }),
  setShowPDFViewer: (show) => set({ showPDFViewer: show }),
}));

