"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Loader2, FileText, ExternalLink } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { sendChatMessage, type Citation } from "../../lib/api";
import DocumentViewerModal from "./DocumentViewerModal";
import TypingIndicator from "./TypingIndicator";

export default function ChatWindow() {
  const {
    messages,
    addMessage,
    updateLastMessage,
    setIsStreaming,
    appendStreamingContent,
    clearStreaming,
    isStreaming,
    selectedDocumentId,
    showPDFViewer,
    setShowPDFViewer,
  } = useStore();
  const [input, setInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [isFocused, setIsFocused] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const currentMessage = messages[messages.length - 1];
  const currentCitations = currentMessage?.citations;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user" as const,
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    addMessage(userMessage);
    setInput("");
    setIsThinking(true);
    setIsStreaming(true);

    try {
      const response = await sendChatMessage(
        { query: userMessage.content, stream: false }
      );

      addMessage({
        id: response.id || crypto.randomUUID(),
        role: "assistant",
        content: response.content,
        citations: response.citations,
        reasoning_steps: response.reasoning_steps,
        timestamp: response.timestamp || new Date().toISOString(),
      });

      setIsStreaming(false);
      clearStreaming();
    } catch (error) {
      console.error("Chat error:", error);
      addMessage({
        id: crypto.randomUUID(),
        role: "assistant",
        content: "Sorry, I encountered an error. Please try again.",
        timestamp: new Date().toISOString(),
      });
      setIsStreaming(false);
      clearStreaming();
    } finally {
      setIsThinking(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <>
      <div className="relative flex h-full flex-col bg-bg-void">
        {/* Messages Area - Centered Container with margins */}
        <div className="flex-1 overflow-y-auto px-4 py-8 pb-32">
          <div className="mx-auto max-w-4xl space-y-6">
            <AnimatePresence mode="popLayout">
              {messages.length === 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className="flex h-full min-h-[400px] items-center justify-center"
                >
                  <div className="text-center">
                    <h3 className="text-xl font-semibold text-white">
                      Start a conversation
                    </h3>
                    <p className="mt-2 text-sm text-gray-500">
                      Ask questions about your documents
                    </p>
                  </div>
                </motion.div>
              )}
              {messages.map((message, index) => (
                <MessageBubble key={message.id} message={message} index={index} />
              ))}
            </AnimatePresence>

            {isThinking && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
              >
                <div className="flex justify-start">
                  <div className="max-w-[80%] rounded-2xl px-4 py-3">
                    <TypingIndicator />
                  </div>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Floating Input Bar - Bottom Center, Pill Shaped */}
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="fixed bottom-0 left-1/2 -translate-x-1/2 mb-6 z-50 w-full max-w-2xl px-4"
        >
          <motion.div
            initial={false}
            animate={{
              borderColor: isFocused ? "var(--glass-border-focus)" : "var(--glass-border)",
              backgroundColor: isFocused ? "var(--glass-bg-focus)" : "var(--glass-bg)",
            }}
            transition={{ duration: 0.2 }}
            className="flex items-end gap-3 rounded-full border bg-white/5 px-6 py-4 backdrop-blur-2xl shadow-2xl transition-all"
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask a question..."
              rows={1}
              className="focus-ring flex-1 resize-none bg-transparent text-white placeholder:text-gray-500 focus:outline-none"
              style={{ minHeight: "24px", maxHeight: "120px" }}
            />
            <motion.button
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-black transition-all disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
              {isStreaming ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </motion.button>
          </motion.div>
        </motion.div>
      </div>

      {/* Document Viewer Modal */}
      {selectedDocumentId && (
        <DocumentViewerModal
          documentId={selectedDocumentId}
          citations={currentCitations?.filter(
            (c) => c.document_id === selectedDocumentId
          )}
          isOpen={showPDFViewer}
          onClose={() => setShowPDFViewer(false)}
        />
      )}
    </>
  );
}

// Helper function to deduplicate citations by document_id and page_number
function getUniqueCitations(citations: Citation[]): Citation[] {
  const seen = new Set<string>();
  const unique: Citation[] = [];

  for (const citation of citations) {
    const key = `${citation.document_id}-${citation.page_number ?? "no-page"}`;
    if (!seen.has(key)) {
      seen.add(key);
      unique.push(citation);
    }
  }

  return unique;
}

function MessageBubble({
  message,
  index,
}: {
  message: {
    id: string;
    role: "user" | "assistant" | "system";
    content: string;
    citations?: Citation[];
    timestamp: string;
  };
  index: number;
}) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut", delay: index * 0.05 }}
      className={`flex gap-4 ${isUser ? "justify-end" : "justify-start"}`}
    >
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/5 border border-white/10 text-gray-500 text-xs font-semibold">
          AI
        </div>
      )}
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 ${
          isUser
            ? "bg-white text-black"
            : "bg-transparent text-gray-100"
        }`}
      >
        <p className="whitespace-pre-wrap text-sm leading-relaxed">
          {message.content}
        </p>
        {message.citations && message.citations.length > 0 && (
          <div className="mt-3 space-y-2 border-t border-white/10 pt-3">
            <p className="text-xs font-medium text-gray-500">Sources:</p>
            <div className="flex flex-wrap gap-2">
              {getUniqueCitations(message.citations).map((citation, idx) => (
                <CitationBadge key={idx} citation={citation} index={idx} />
              ))}
            </div>
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/5 border border-white/10 text-white text-xs font-semibold">
          U
        </div>
      )}
    </motion.div>
  );
}

function CitationBadge({ citation, index }: { citation: Citation; index: number }) {
  const { setSelectedDocumentId, setShowPDFViewer } = useStore();

  const handleClick = () => {
    setSelectedDocumentId(citation.document_id);
    setShowPDFViewer(true);
  };

  const pageText = citation.page_number ? `Page ${citation.page_number}` : "";

  return (
    <motion.button
      onClick={handleClick}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className="group flex items-center gap-2 rounded-md border border-white/20 bg-white/10 px-2 py-0.5 text-xs text-gray-100 transition-all hover:bg-white/15"
    >
      <FileText className="h-3 w-3 shrink-0 text-gray-500" />
      <div className="flex-1 min-w-0">
        <p className="truncate font-medium">{citation.document_name}</p>
        {pageText && (
          <p className="mt-0.5 text-gray-500">{pageText}</p>
        )}
      </div>
      <ExternalLink className="h-3 w-3 shrink-0 text-gray-500 opacity-0 transition-opacity group-hover:opacity-100" />
    </motion.button>
  );
}
