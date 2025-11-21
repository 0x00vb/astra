"use client";

import { useEffect, useState } from "react";
import ProtectedRoute from "../components/Auth/ProtectedRoute";
import Navbar from "../components/Navbar";
import { getUserAnalytics, getQueryHistory, UserAnalytics, QueryHistoryItem } from "../lib/api";
import { BarChart3, FileText, MessageSquare, Zap, Clock, TrendingUp } from "lucide-react";

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<UserAnalytics | null>(null);
  const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(30);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    loadAnalytics();
  }, [days]);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError("");
      const [analyticsData, historyData] = await Promise.all([
        getUserAnalytics(days),
        getQueryHistory(50),
      ]);
      setAnalytics(analyticsData);
      setQueryHistory(historyData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar analytics");
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("es-ES", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <ProtectedRoute>
      <div className="min-h-screen bg-zinc-50 dark:bg-black">
        <Navbar />
        <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
              Analytics
            </h1>
            <p className="text-zinc-600 dark:text-zinc-400">
              Estadísticas de uso y rendimiento
            </p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-zinc-900 border-r-transparent dark:border-zinc-50"></div>
                <p className="mt-4 text-sm text-zinc-600 dark:text-zinc-400">
                  Cargando analytics...
                </p>
              </div>
            </div>
          ) : error ? (
            <div className="rounded-md bg-red-50 p-4 dark:bg-red-900/20">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                {error}
              </p>
            </div>
          ) : analytics ? (
            <>
              {/* Period Selector */}
              <div className="mb-6 flex gap-2">
                {[7, 30, 90, 365].map((d) => (
                  <button
                    key={d}
                    onClick={() => setDays(d)}
                    className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                      days === d
                        ? "bg-zinc-900 text-white dark:bg-zinc-50 dark:text-zinc-900"
                        : "bg-white text-zinc-700 hover:bg-zinc-100 dark:bg-zinc-900 dark:text-zinc-300 dark:hover:bg-zinc-800"
                    }`}
                  >
                    {d} días
                  </button>
                ))}
              </div>

              {/* Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                      Consultas
                    </h3>
                    <MessageSquare className="h-5 w-5 text-zinc-400" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    {analytics.query_stats.total_queries}
                  </p>
                </div>

                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                      Tokens Usados
                    </h3>
                    <Zap className="h-5 w-5 text-zinc-400" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    {analytics.query_stats.total_tokens_used.toLocaleString()}
                  </p>
                </div>

                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                      Documentos
                    </h3>
                    <FileText className="h-5 w-5 text-zinc-400" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    {analytics.document_stats.total_documents}
                  </p>
                </div>

                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                      Latencia Promedio
                    </h3>
                    <Clock className="h-5 w-5 text-zinc-400" />
                  </div>
                  <p className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">
                    {Math.round(analytics.query_stats.average_latency_ms)}ms
                  </p>
                </div>
              </div>

              {/* Detailed Stats */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
                    Estadísticas de Consultas
                  </h2>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Total de consultas</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.query_stats.total_queries}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Tokens totales</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.query_stats.total_tokens_used.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Chunks promedio</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.query_stats.average_chunks_retrieved.toFixed(1)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Latencia promedio</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {Math.round(analytics.query_stats.average_latency_ms)}ms
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
                    Estadísticas de Documentos
                  </h2>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Total documentos</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.document_stats.total_documents}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Tamaño total</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {formatBytes(analytics.document_stats.total_size_bytes)}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Total chunks</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.document_stats.total_chunks}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Caracteres totales</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.document_stats.total_characters.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Subidas</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.document_stats.uploads_count}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-zinc-600 dark:text-zinc-400">Eliminaciones</span>
                      <span className="font-medium text-zinc-900 dark:text-zinc-50">
                        {analytics.document_stats.deletes_count}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Query History */}
              {queryHistory.length > 0 && (
                <div className="bg-white dark:bg-zinc-900 rounded-lg p-6 border border-zinc-200 dark:border-zinc-800">
                  <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-50 mb-4">
                    Historial de Consultas Recientes
                  </h2>
                  <div className="space-y-4">
                    {queryHistory.slice(0, 10).map((query) => (
                      <div
                        key={query.id}
                        className="border-b border-zinc-200 dark:border-zinc-800 pb-4 last:border-0 last:pb-0"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50 flex-1">
                            {query.query_text.length > 100
                              ? query.query_text.substring(0, 100) + "..."
                              : query.query_text}
                          </p>
                          <span className="text-xs text-zinc-500 dark:text-zinc-400 ml-4">
                            {formatDate(query.created_at)}
                          </span>
                        </div>
                        <div className="flex gap-4 text-xs text-zinc-600 dark:text-zinc-400">
                          <span>{query.chunks_retrieved} chunks</span>
                          <span>{Math.round(query.total_latency_ms)}ms</span>
                          {query.tokens_used && <span>{query.tokens_used} tokens</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          ) : null}
        </div>
      </div>
    </ProtectedRoute>
  );
}

