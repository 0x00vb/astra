"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Brain, Zap, Eye, CheckCircle } from "lucide-react";
import { motion } from "framer-motion";
import type { ReasoningStep } from "../../lib/api";

interface ReasoningPanelProps {
  steps: ReasoningStep[];
}

export default function ReasoningPanel({ steps }: ReasoningPanelProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleStep = (stepId: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepId)) {
        next.delete(stepId);
      } else {
        next.add(stepId);
      }
      return next;
    });
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case "thought":
        return <Brain className="h-4 w-4 text-white" />;
      case "action":
        return <Zap className="h-4 w-4 text-white" />;
      case "observation":
        return <Eye className="h-4 w-4 text-white" />;
      case "final_answer":
        return <CheckCircle className="h-4 w-4 text-white" />;
      default:
        return <Brain className="h-4 w-4 text-gray-500" />;
    }
  };

  if (steps.length === 0) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl m-4">
        <p className="text-sm text-gray-500">
          No reasoning steps available
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto p-4 bg-bg-void">
      <div className="mb-4 flex items-center gap-2">
        <Brain className="h-5 w-5 text-white" />
        <h3 className="font-semibold text-white">
          Reasoning Steps ({steps.length})
        </h3>
      </div>
      <div className="space-y-2">
        {steps.map((step, index) => {
          const isExpanded = expandedSteps.has(step.step_id);
          const isFinalAnswer = step.type === "final_answer";

          return (
            <motion.div
              key={step.step_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05, duration: 0.4, ease: "easeOut" }}
              className="rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl"
            >
              <button
                onClick={() => !isFinalAnswer && toggleStep(step.step_id)}
                className="interactive flex w-full items-center gap-3 p-3 text-left transition-all hover:bg-white/5"
                disabled={isFinalAnswer}
              >
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-white/5 border border-white/10">
                  {getStepIcon(step.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium uppercase text-gray-500">
                      {step.type.replace("_", " ")}
                    </span>
                    <span className="text-xs text-gray-500/70">
                      Step {index + 1}
                    </span>
                  </div>
                  {isExpanded || isFinalAnswer ? (
                    <p className="mt-1 text-sm text-gray-100">
                      {step.content}
                    </p>
                  ) : (
                    <p className="mt-1 truncate text-sm text-gray-500">
                      {step.content.slice(0, 100)}...
                    </p>
                  )}
                </div>
                {!isFinalAnswer && (
                  <div className="shrink-0">
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-500" />
                    )}
                  </div>
                )}
              </button>

              {isExpanded && step.metadata && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="border-t border-white/10 bg-white/5 p-3 transition-all"
                >
                  <pre className="overflow-x-auto text-xs text-gray-500">
                    {JSON.stringify(step.metadata, null, 2)}
                  </pre>
                </motion.div>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
