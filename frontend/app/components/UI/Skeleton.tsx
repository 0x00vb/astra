"use client";

import { motion } from "framer-motion";

export function SkeletonCard() {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
      <div className="flex items-start justify-between">
        <div className="flex-1 space-y-3">
          <SkeletonLine className="h-4 w-24" />
          <SkeletonLine className="h-8 w-32" />
        </div>
        <SkeletonCircle className="h-12 w-12" />
      </div>
    </div>
  );
}

export function SkeletonLine({
  className = "",
}: {
  className?: string;
}) {
  return (
    <motion.div
      className={`rounded bg-zinc-200 dark:bg-zinc-800 ${className}`}
      animate={{
        opacity: [0.5, 1, 0.5],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

export function SkeletonCircle({
  className = "",
}: {
  className?: string;
}) {
  return (
    <motion.div
      className={`rounded-full bg-zinc-200 dark:bg-zinc-800 ${className}`}
      animate={{
        opacity: [0.5, 1, 0.5],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

export function MessageSkeleton() {
  return (
    <div className="flex gap-4">
      <SkeletonCircle className="h-8 w-8" />
      <div className="flex-1 space-y-2">
        <SkeletonLine className="h-4 w-full" />
        <SkeletonLine className="h-4 w-3/4" />
        <SkeletonLine className="h-4 w-1/2" />
      </div>
    </div>
  );
}

