"use client";

import { useState, useEffect } from "react";
import { X, ChevronLeft, ChevronRight } from "lucide-react";
import { useStore } from "../../store/useStore";
import { getDocumentContent, type Citation } from "../../lib/api";
import dynamic from "next/dynamic";
import { motion } from "framer-motion";
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

interface PDFViewerProps {
  documentId: string;
  citations?: Citation[];
}

export default function PDFViewer({ documentId, citations }: PDFViewerProps) {
  const { setShowPDFViewer } = useStore();
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState(1);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDocument();
  }, [documentId]);

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

  const goToPage = (page: number) => {
    if (page >= 1 && page <= numPages) {
      setPageNumber(page);
    }
  };

  const getPageForCitation = (citation: Citation): number | null => {
    return citation.page_number || null;
  };

  const highlightChunks = (pageNum: number) => {
    if (!citations) return [];

    return citations
      .filter((c) => c.page_number === pageNum)
      .map((c) => ({
        ...c,
        range: c.chunk_range || [0, 0],
      }));
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <div className="mb-4 h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-600 mx-auto" />
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Loading PDF...
          </p>
        </div>
      </div>
    );
  }

  if (!fileUrl) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Failed to load PDF
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col bg-zinc-50 dark:bg-zinc-950">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-zinc-200 bg-white px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
        <div className="flex items-center gap-4">
          <button
            onClick={() => goToPage(pageNumber - 1)}
            disabled={pageNumber <= 1}
            className="rounded-lg p-2 hover:bg-zinc-100 disabled:opacity-50 dark:hover:bg-zinc-800"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-sm font-medium text-zinc-900 dark:text-zinc-50">
            Page {pageNumber} of {numPages}
          </span>
          <button
            onClick={() => goToPage(pageNumber + 1)}
            disabled={pageNumber >= numPages}
            className="rounded-lg p-2 hover:bg-zinc-100 disabled:opacity-50 dark:hover:bg-zinc-800"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
        <button
          onClick={() => setShowPDFViewer(false)}
          className="rounded-lg p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* PDF Viewer */}
      <div className="flex-1 overflow-auto p-4">
        <div className="mx-auto max-w-4xl">
          <ErrorBoundary
            fallback={
              <div className="py-12 text-center">
                <p className="text-red-600 dark:text-red-400">
                  Failed to load PDF. Please try again.
                </p>
              </div>
            }
          >
            <Document
              file={fileUrl}
              onLoadSuccess={({ numPages }) => setNumPages(numPages)}
              loading={
                <div className="flex items-center justify-center py-12">
                  <div className="h-8 w-8 animate-spin rounded-full border-4 border-zinc-300 border-t-blue-600" />
                </div>
              }
              error={
                <div className="py-12 text-center text-red-600 dark:text-red-400">
                  Failed to load PDF
                </div>
              }
            >
              <Page
                pageNumber={pageNumber}
                width={800}
                renderTextLayer={true}
                renderAnnotationLayer={true}
                className="shadow-lg"
              />
            </Document>
          </ErrorBoundary>

          {/* Citation Highlights */}
          {citations && citations.length > 0 && (
            <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-4 dark:border-zinc-800 dark:bg-zinc-900">
              <h4 className="mb-2 text-sm font-semibold text-zinc-900 dark:text-zinc-50">
                Citations on this page:
              </h4>
              <div className="space-y-2">
                {highlightChunks(pageNumber).map((citation, idx) => (
                  <div
                    key={idx}
                    className="rounded border border-blue-200 bg-blue-50 p-2 text-xs dark:border-blue-800 dark:bg-blue-950/20"
                  >
                    <p className="font-medium text-blue-900 dark:text-blue-100">
                      {citation.document_name}
                    </p>
                    <p className="mt-1 text-blue-700 dark:text-blue-300">
                      {citation.chunk_text.slice(0, 150)}...
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

