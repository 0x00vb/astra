"use client";

import { useEffect, useState } from "react";
import { FileText, TrendingUp, BarChart3 } from "lucide-react";
import { motion } from "framer-motion";
import { useStore } from "../../store/useStore";
import {
  getDocumentSummaries,
  getWordCloud,
  getEmbeddings2D,
} from "../../lib/api";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function InsightsPanel() {
  const {
    summaries,
    wordCloud,
    embeddings2D,
    setSummaries,
    setWordCloud,
    setEmbeddings2D,
  } = useStore();
  const [activeTab, setActiveTab] = useState<"summaries" | "wordcloud" | "embeddings">("summaries");

  useEffect(() => {
    loadInsights();
  }, []);

  const loadInsights = async () => {
    try {
      const [summariesData, wordCloudData, embeddingsData] = await Promise.all([
        getDocumentSummaries(),
        getWordCloud(),
        getEmbeddings2D(),
      ]);

      setSummaries(summariesData);
      setWordCloud(wordCloudData);
      setEmbeddings2D(embeddingsData);
    } catch (error) {
      console.error("Failed to load insights:", error);
    }
  };

  return (
    <div className="flex h-full flex-col bg-bg-void">
      {/* Tabs */}
      <div className="flex border-b border-white/10">
        {[
          { id: "summaries", label: "Summaries", icon: FileText },
          { id: "wordcloud", label: "Word Cloud", icon: BarChart3 },
          { id: "embeddings", label: "Embeddings", icon: TrendingUp },
        ].map((tab) => (
          <motion.button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            className={`flex items-center gap-2 border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-white text-white"
                : "border-transparent text-gray-500 hover:text-white"
            }`}
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </motion.button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {activeTab === "summaries" && <SummariesView summaries={summaries} />}
        {activeTab === "wordcloud" && <WordCloudView wordCloud={wordCloud} />}
        {activeTab === "embeddings" && <EmbeddingsView embeddings={embeddings2D} />}
      </div>
    </div>
  );
}

function SummariesView({
  summaries,
}: {
  summaries: Array<{
    document_id: string;
    document_name: string;
    summary: string;
    key_topics: string[];
    word_count: number;
  }>;
}) {
  if (summaries.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-500">
          No summaries available
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {summaries.map((summary, idx) => (
        <motion.div
          key={summary.document_id}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.1, duration: 0.4, ease: "easeOut" }}
          className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl p-6 transition-all hover:border-white/20 hover:bg-white/10"
        >
          <h3 className="mb-2 text-lg font-semibold text-white">
            {summary.document_name}
          </h3>
          <p className="mb-4 text-sm text-gray-100">
            {summary.summary}
          </p>
          <div className="flex flex-wrap gap-2">
            {summary.key_topics.map((topic, topicIdx) => (
              <motion.span
                key={topicIdx}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: idx * 0.1 + topicIdx * 0.05 }}
                className="rounded-md border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white"
              >
                {topic}
              </motion.span>
            ))}
          </div>
          <p className="mt-4 text-xs text-gray-500">
            {summary.word_count.toLocaleString()} words
          </p>
        </motion.div>
      ))}
    </div>
  );
}

function WordCloudView({
  wordCloud,
}: {
  wordCloud: Array<{ word: string; count: number }>;
}) {
  if (wordCloud.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-500">
          No word cloud data available
        </p>
      </div>
    );
  }

  // Simple word cloud visualization using font sizes
  const maxCount = Math.max(...wordCloud.map((w) => w.count));
  const minSize = 12;
  const maxSize = 48;

  return (
    <div className="flex flex-wrap items-center justify-center gap-4 p-8">
      {wordCloud.slice(0, 50).map((item, idx) => {
        const size = minSize + ((item.count / maxCount) * (maxSize - minSize));
        const opacity = 0.6 + (item.count / maxCount) * 0.4;

        return (
          <motion.span
            key={item.word}
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity, scale: 1 }}
            transition={{ delay: idx * 0.02, duration: 0.4, ease: "easeOut" }}
            whileHover={{ scale: 1.2, color: "var(--text-white)" }}
            className="font-semibold text-gray-100 transition-colors"
            style={{ fontSize: `${size}px` }}
          >
            {item.word}
          </motion.span>
        );
      })}
    </div>
  );
}

function EmbeddingsView({
  embeddings,
}: {
  embeddings: Array<{
    x: number;
    y: number;
    chunk_id: string;
    document_id: string;
    document_name: string;
    chunk_text: string;
    cluster_id?: number;
  }>;
}) {
  if (embeddings.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-sm text-gray-500">
          No embeddings data available
        </p>
      </div>
    );
  }

  // Group by document for different colors
  const documentGroups = embeddings.reduce((acc, point) => {
    if (!acc[point.document_name]) {
      acc[point.document_name] = [];
    }
    acc[point.document_name].push({
      x: point.x,
      y: point.y,
      name: point.document_name,
      chunk: point.chunk_text.slice(0, 50),
    });
    return acc;
  }, {} as Record<string, any[]>);

  // Grayscale colors - different shades of white/gray
  const colors = [
    "var(--text-white)",
    "#e5e5e5",
    "#cccccc",
    "#b3b3b3",
    "#999999",
    "#808080",
  ];

  return (
    <div className="h-[600px] w-full">
      <h3 className="mb-4 text-lg font-semibold text-white">
        2D Embeddings Visualization (UMAP/t-SNE)
      </h3>
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart
          margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" />
          <XAxis
            type="number"
            dataKey="x"
            name="Dimension 1"
            stroke="var(--text-gray-500)"
            label={{ value: "Dimension 1", position: "insideBottom", offset: -5, fill: "var(--text-gray-500)" }}
          />
          <YAxis
            type="number"
            dataKey="y"
            name="Dimension 2"
            stroke="var(--text-gray-500)"
            label={{ value: "Dimension 2", angle: -90, position: "insideLeft", fill: "var(--text-gray-500)" }}
          />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            contentStyle={{
              backgroundColor: "var(--glass-bg)",
              border: "1px solid var(--glass-border)",
              borderRadius: "8px",
              color: "var(--text-white)",
              backdropFilter: "blur(24px)",
            }}
            formatter={(value: any, name: string, props: any) => [
              props.payload.chunk || value,
              name,
            ]}
          />
          <Legend
            wrapperStyle={{ color: "var(--text-white)" }}
          />
          {Object.entries(documentGroups).map(([docName, points], idx) => (
            <Scatter
              key={docName}
              name={docName}
              data={points}
              fill={colors[idx % colors.length]}
              opacity={0.6}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
