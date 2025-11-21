"use client";

import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { getDocumentContent, type Citation } from "../../lib/api";
import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { ErrorBoundary } from "../UI/ErrorBoundary";

// Dynamically import react-pdf with SSR disabled to avoid Promise.withResolvers issues
const Document = dynamic(
  () => import("react-pdf").then((mod) => mod.Document),
  { ssr: false }
);
const Page = dynamic(
  () => import("react-pdf").then((mod) => mod.Page),
  { ssr: false }
);

// Initialize PDF.js worker only on client side
if (typeof window !== "undefined") {
  import("react-pdf").then(({ pdfjs }) => {
    pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;
  });
}

interface DocumentViewerModalProps {
  documentId: string;
  citations?: Citation[];
  isOpen: boolean;
  onClose: () => void;
}

export default function DocumentViewerModal({
  documentId,
  citations,
  isOpen,
  onClose,
}: DocumentViewerModalProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [isClosing, setIsClosing] = useState(false);

  useEffect(() => {
    if (isOpen && documentId) {
      setIsClosing(false);
      loadDocument();
    }
  }, [isOpen, documentId]);

  const loadDocument = async () => {
    try {
      setLoading(true);
      const { file_url } = await getDocumentContent(documentId);
      setFileUrl(file_url);
    } catch (error) {
      console.error("Failed to load document:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setIsClosing(true);
    setTimeout(() => {
      onClose();
      setIsClosing(false);
    }, 300);
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= numPages) {
      setPageNumber(page);
    }
  };

  const highlightChunks = (pageNum: number) => {
    if (!citations) return [];
    return citations.filter((c) => c.page_number === pageNum);
  };

  if (!isOpen && !isClosing) return null;

  return (
    <>
      {/* Backdrop */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={handleClose}
          />
        )}
      </AnimatePresence>

      {/* Modal - slides from right */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{
              duration: 0.4,
              ease: "easeOut",
            }}
            className="fixed right-0 top-0 z-50 h-full w-full max-w-4xl bg-bg-void border-l border-white/10 backdrop-blur-xl"
          >
            <div className="flex h-full flex-col">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-white/10 bg-white/5 backdrop-blur-xl px-6 py-4">
                <div className="flex items-center gap-4">
                  <motion.button
                    onClick={() => goToPage(pageNumber - 1)}
                    disabled={pageNumber <= 1}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="rounded-lg p-2 text-gray-500 transition-colors hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="h-5 w-5" />
                  </motion.button>
                  <span className="text-sm font-medium text-white">
                    {loading ? "Loading..." : `Page ${pageNumber} of ${numPages}`}
                  </span>
                  <motion.button
                    onClick={() => goToPage(pageNumber + 1)}
                    disabled={pageNumber >= numPages || loading}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    className="rounded-lg p-2 text-gray-500 transition-colors hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="h-5 w-5" />
                  </motion.button>
                </div>
                <motion.button
                  onClick={handleClose}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="rounded-lg p-2 text-gray-500 transition-colors hover:text-white"
                >
                  <X className="h-5 w-5" />
                </motion.button>
              </div>

              {/* PDF Viewer */}
              <div className="flex-1 overflow-auto bg-bg-void p-6">
                <div className="mx-auto max-w-3xl">
                  <ErrorBoundary
                    fallback={
                      <div className="py-12 text-center">
                        <p className="text-gray-500">
                          Failed to load PDF. Please try again.
                        </p>
                      </div>
                    }
                  >
                    {loading ? (
                      <div className="flex items-center justify-center py-12">
                        <div className="h-8 w-8 animate-spin rounded-full border-4 border-white/10 border-t-white" />
                      </div>
                    ) : fileUrl ? (
                      <>
                        <Document
                          file={fileUrl}
                          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
                          loading={
                            <div className="flex items-center justify-center py-12">
                              <div className="h-8 w-8 animate-spin rounded-full border-4 border-white/10 border-t-white" />
                            </div>
                          }
                          error={
                            <div className="py-12 text-center text-gray-500">
                              Failed to load PDF
                            </div>
                          }
                        >
                          <Page
                            pageNumber={pageNumber}
                            width={700}
                            renderTextLayer={true}
                            renderAnnotationLayer={true}
                            className="shadow-lg"
                          />
                        </Document>

                        {/* Citations on this page */}
                        {highlightChunks(pageNumber).length > 0 && (
                          <motion.div
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.4, ease: "easeOut" }}
                            className="mt-6 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4"
                          >
                            <h4 className="mb-3 text-sm font-semibold text-white">
                              Citations on this page:
                            </h4>
                            <div className="space-y-2">
                              {highlightChunks(pageNumber).map((citation, idx) => (
                                <div
                                  key={idx}
                                  className="rounded-md border border-white/10 bg-white/5 p-3 text-xs"
                                >
                                  <p className="font-medium text-white">
                                    {citation.document_name}
                                  </p>
                                  <p className="mt-1 text-gray-500">
                                    {citation.chunk_text.slice(0, 150)}...
                                  </p>
                                </div>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </>
                    ) : null}
                  </ErrorBoundary>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
