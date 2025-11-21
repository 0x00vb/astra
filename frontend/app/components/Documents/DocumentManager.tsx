"use client";

import { useState, useEffect, useCallback } from "react";
import { Upload, FileText, CheckCircle2, Loader2, XCircle, Trash2, AlertCircle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import {
  uploadDocument,
  getDocuments,
  getIndexProgress,
  deleteDocument,
  type Document,
} from "../../lib/api";

export default function DocumentManager() {
  const { documents, setDocuments, indexProgress, setIndexProgress, removeDocument } =
    useStore();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadingFiles, setUploadingFiles] = useState<Set<string>>(
    new Set()
  );
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    // Poll for indexing progress
    const interval = setInterval(() => {
      documents.forEach((doc) => {
        if (doc.status === "processing" || doc.status === "pending") {
          checkProgress(doc.id);
        }
      });
    }, 2000);

    return () => clearInterval(interval);
  }, [documents]);

  // Clear success/error messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const loadDocuments = async () => {
    try {
      const docs = await getDocuments();
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to load documents:", error);
    }
  };

  const checkProgress = async (documentId: string) => {
    try {
      const progress = await getIndexProgress(documentId);
      setIndexProgress(documentId, progress);

      if (progress.status === "indexed") {
        loadDocuments(); // Refresh document list
      }
    } catch (error) {
      console.error("Failed to check progress:", error);
    }
  };

  const handleFileSelect = async (files: FileList | null) => {
    if (!files) return;

    setError(null);
    setSuccess(null);

    // Validate file types
    const allowedTypes = [".pdf", ".docx", ".doc", ".txt", ".html", ".htm"];
    const invalidFiles = Array.from(files).filter(
      (file) => !allowedTypes.some((ext) => file.name.toLowerCase().endsWith(ext))
    );

    if (invalidFiles.length > 0) {
      setError(`Invalid file type(s): ${invalidFiles.map((f) => f.name).join(", ")}`);
      return;
    }

    // Validate file size (50MB limit)
    const maxSize = 50 * 1024 * 1024;
    const oversizedFiles = Array.from(files).filter((file) => file.size > maxSize);
    if (oversizedFiles.length > 0) {
      setError(`File(s) too large (max 50MB): ${oversizedFiles.map((f) => f.name).join(", ")}`);
      return;
    }

    Array.from(files).forEach(async (file) => {
      const fileId = `${file.name}-${Date.now()}`;
      setUploadingFiles((prev) => new Set(prev).add(fileId));

      try {
        const result = await uploadDocument(file, (progress) => {
          // Upload progress handled here
        });

        setUploadingFiles((prev) => {
          const next = new Set(prev);
          next.delete(fileId);
          return next;
        });

        setSuccess(`Successfully uploaded ${file.name}`);
        await loadDocuments();
        // Start polling for indexing progress
        setTimeout(() => checkProgress(result.document_id), 1000);
      } catch (error) {
        console.error("Upload failed:", error);
        setError(error instanceof Error ? error.message : `Failed to upload ${file.name}`);
        setUploadingFiles((prev) => {
          const next = new Set(prev);
          next.delete(fileId);
          return next;
        });
      }
    });
  };

  const handleDelete = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    setDeletingIds((prev) => new Set(prev).add(documentId));
    setError(null);

    try {
      await deleteDocument(documentId);
      removeDocument(documentId);
      setSuccess(`Successfully deleted ${filename}`);
    } catch (error) {
      console.error("Delete failed:", error);
      setError(error instanceof Error ? error.message : `Failed to delete ${filename}`);
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  };

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      handleFileSelect(e.dataTransfer.files);
    },
    []
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const getStatusIcon = (doc: Document) => {
    switch (doc.status) {
      case "indexed":
        return <CheckCircle2 className="h-5 w-5 text-white" />;
      case "processing":
        return <Loader2 className="h-5 w-5 animate-spin text-white" />;
      case "error":
        return <XCircle className="h-5 w-5 text-gray-500" />;
      default:
        return <FileText className="h-5 w-5 text-gray-500" />;
    }
  };

  const getProgress = (doc: Document) => {
    const progress = indexProgress[doc.id];
    if (progress) {
      return progress.progress;
    }
    return doc.status === "indexed" ? 100 : doc.status === "error" ? 0 : 0;
  };

  return (
    <div className="h-full overflow-y-auto p-6 bg-bg-void">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Success/Error Messages */}
        <AnimatePresence>
          {success && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4 flex items-center gap-2 text-white"
            >
              <CheckCircle2 className="h-5 w-5" />
              <p>{success}</p>
            </motion.div>
          )}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4 flex items-center gap-2 text-gray-500"
            >
              <AlertCircle className="h-5 w-5" />
              <p>{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload Area - Drag and Drop Zone */}
        <motion.div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className={`relative rounded-2xl border-2 border-dashed p-12 text-center transition-all ${
            isDragging
              ? "border-white/30 bg-white/10 backdrop-blur-xl"
              : "border-white/10 bg-white/5 backdrop-blur-xl"
          }`}
        >
          <input
            type="file"
            id="file-upload"
            multiple
            accept=".pdf,.txt,.docx,.doc,.html,.htm"
            onChange={(e) => handleFileSelect(e.target.files)}
            className="hidden"
          />
          <label
            htmlFor="file-upload"
            className="flex cursor-pointer flex-col items-center gap-4 transition-all"
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              className="flex h-16 w-16 items-center justify-center rounded-full bg-white/5 border border-white/10"
            >
              <Upload className="h-8 w-8 text-gray-500" />
            </motion.div>
            <div>
              <p className="text-lg font-semibold text-white">
                Drop files here or click to upload
              </p>
              <p className="mt-1 text-sm text-gray-500">
                Supports PDF, DOCX, TXT, HTML (max 50MB)
              </p>
            </div>
          </label>
        </motion.div>

        {/* Documents List */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-white">
            Documents ({documents.length})
          </h2>
          <div className="space-y-3">
            {documents.map((doc, idx) => (
              <motion.div
                key={doc.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05, duration: 0.4, ease: "easeOut" }}
                className="group rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-4 transition-all hover:border-white/20 hover:bg-white/10"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    {getStatusIcon(doc)}
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white truncate">
                        {doc.filename}
                      </p>
                      <p className="mt-1 text-sm text-gray-500">
                        {formatFileSize(doc.file_size)} • {doc.file_type.toUpperCase()}
                        {doc.chunks_count > 0 && ` • ${doc.chunks_count} chunks`}
                        {doc.total_pages && ` • ${doc.total_pages} pages`}
                      </p>
                      {(doc.status === "processing" || doc.status === "pending") && (
                        <div className="mt-3">
                          <div className="mb-1 flex items-center justify-between text-xs text-gray-500">
                            <span>Indexing...</span>
                            <span>{getProgress(doc)}%</span>
                          </div>
                          <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10 border border-white/10">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${getProgress(doc)}%` }}
                              transition={{ duration: 0.3, ease: "easeOut" }}
                              className="h-full bg-white"
                            />
                          </div>
                        </div>
                      )}
                      {doc.status === "error" && (
                        <p className="mt-2 text-sm text-gray-500">
                          Processing failed. Please try uploading again.
                        </p>
                      )}
                    </div>
                  </div>
                  <div className="ml-4 flex items-center gap-2">
                    <div className="text-xs text-gray-500">
                      {new Date(doc.created_at).toLocaleDateString()}
                    </div>
                    <motion.button
                      onClick={() => handleDelete(doc.id, doc.filename)}
                      disabled={deletingIds.has(doc.id)}
                      whileHover={{ scale: 1.1 }}
                      whileTap={{ scale: 0.9 }}
                      className="p-1.5 rounded border border-transparent hover:border-white/10 text-gray-500 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete document"
                    >
                      {deletingIds.has(doc.id) ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="h-4 w-4" />
                      )}
                    </motion.button>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
          {documents.length === 0 && (
            <p className="py-12 text-center text-gray-500">
              No documents uploaded yet
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
