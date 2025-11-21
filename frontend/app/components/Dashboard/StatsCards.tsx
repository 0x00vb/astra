"use client";

import { useEffect, useState } from "react";
import { FileText, Database, MessageSquare } from "lucide-react";
import { useStore } from "../../store/useStore";
import { getDashboardStats } from "../../lib/api";
import { SkeletonCard } from "../UI/Skeleton";

export default function StatsCards() {
  const { stats, setStats } = useStore();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true);
        const data = await getDashboardStats();
        setStats(data);
      } catch (error) {
        console.error("Failed to fetch stats:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 30000); // Refresh every 30s

    return () => clearInterval(interval);
  }, [setStats]);

  if (loading && !stats) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  const statItems = [
    {
      label: "Documents Indexed",
      value: stats?.documents_indexed ?? 0,
      icon: FileText,
      color: "bg-blue-500/10 text-blue-500",
    },
    {
      label: "Tokens Processed",
      value: stats?.total_tokens_processed
        ? formatNumber(stats.total_tokens_processed)
        : 0,
      icon: Database,
      color: "bg-purple-500/10 text-purple-500",
    },
    {
      label: "Total Chunks",
      value: stats?.total_chunks ?? 0,
      icon: Database,
      color: "bg-green-500/10 text-green-500",
    },
    {
      label: "Queries Processed",
      value: stats?.queries_processed ?? 0,
      icon: MessageSquare,
      color: "bg-orange-500/10 text-orange-500",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {statItems.map((item, index) => (
        <div
          key={item.label}
          className="group relative overflow-hidden rounded-xl border border-zinc-200 bg-white p-6 shadow-sm transition-all hover:shadow-md hover-lift fade-in dark:border-zinc-800 dark:bg-zinc-900"
          style={{ animationDelay: `${index * 50}ms` }}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <p className="text-sm font-medium text-zinc-600 dark:text-zinc-400">
                {item.label}
              </p>
              <p className="mt-2 text-3xl font-bold text-zinc-900 dark:text-zinc-50">
                {item.value}
              </p>
            </div>
            <div
              className={`flex h-12 w-12 items-center justify-center rounded-lg ${item.color}`}
            >
              <item.icon className="h-6 w-6" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return `${(num / 1_000_000).toFixed(1)}M`;
  }
  if (num >= 1_000) {
    return `${(num / 1_000).toFixed(1)}K`;
  }
  return num.toString();
}

