"use client";

import { useState } from "react";
import { MessageSquare, FileText, BarChart3, X, Sidebar, LogOut } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "../../store/useStore";
import { useAuth } from "../../contexts/AuthContext";
import { logout } from "../../lib/api";
import ChatWindow from "../Chat/ChatWindow";
import DocumentManager from "../Documents/DocumentManager";
import InsightsPanel from "../Insights/InsightsPanel";
import ReasoningPanel from "../Reasoning/ReasoningPanel";
import Navbar from "../Navbar";

interface MainLayoutProps {
  children?: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const {
    activeTab,
    setActiveTab,
    showReasoningPanel,
    setShowReasoningPanel,
    showPDFViewer,
    selectedDocumentId,
    messages,
  } = useStore();
  const { user, refreshUser } = useAuth();
  const [showSidebar, setShowSidebar] = useState(true);

  const currentMessage = messages[messages.length - 1];
  const hasReasoningSteps =
    currentMessage?.reasoning_steps && currentMessage.reasoning_steps.length > 0;

  return (
    <div className="relative flex h-screen overflow-hidden bg-bg-void">
      {/* Floating Sidebar - Left with margins, pushes content */}
      <motion.aside
        layout
        initial={false}
        animate={{
          width: showSidebar ? 288 : 0, // w-64 (256px) + m-4 margins (32px total)
          opacity: showSidebar ? 1 : 0,
          scale: showSidebar ? 1 : 0.98,
        }}
        transition={{
          duration: 0.5,
          ease: "easeOut",
        }}
        className="flex-shrink-0 flex flex-col m-4 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-xl overflow-hidden"
      >
        {showSidebar && (
          <>
            <div className="flex items-center justify-between border-b border-white/10 p-4">
              <h2 className="text-lg font-semibold text-white">Navigation</h2>
              <button
                onClick={() => setShowSidebar(false)}
                className="rounded-lg p-1.5 text-gray-500 transition-colors hover:text-white hover:bg-white/5"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex flex-col flex-1">
              <nav className="space-y-1 p-2 overflow-y-auto">
                {[
                  { id: "chat", label: "Chat", icon: MessageSquare },
                  { id: "documents", label: "Documents", icon: FileText },
                  { id: "insights", label: "Insights", icon: BarChart3 },
                ].map((tab) => (
                  <motion.button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    whileHover={{ x: 2 }}
                    whileTap={{ scale: 0.98 }}
                    className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all ${
                      activeTab === tab.id
                        ? "bg-white/5 text-white"
                        : "text-gray-500 hover:bg-white/5 hover:text-white"
                    }`}
                  >
                    <tab.icon className="h-5 w-5" />
                    <span>{tab.label}</span>
                  </motion.button>
                ))}
              </nav>
              <div className="p-2 mt-auto border-t border-white/10">
                {user && (
                  <div className="mb-2 px-3 py-1 text-xs text-gray-400">
                    Logged in as: {user.full_name || user.email}
                  </div>
                )}
                <motion.button
                  onClick={() => {
                    logout();
                    refreshUser();
                  }}
                  whileHover={{ x: 2 }}
                  whileTap={{ scale: 0.98 }}
                  className="group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all text-gray-500 hover:bg-white/5 hover:text-white"
                >
                  <LogOut className="h-5 w-5" />
                  <span>Logout</span>
                </motion.button>
              </div>
            </div>
          </>
        )}
      </motion.aside>

      {/* Main Content - Resizes based on sidebar */}
      <motion.div
        layout
        className="flex flex-1 flex-col overflow-hidden min-w-0"
      >
        {/* Top Bar */}
        <header className="flex items-center justify-between border-b border-white/10 bg-bg-void/50 backdrop-blur-xl px-4 py-3 z-30">
          <div className="flex items-center gap-3">
            {!showSidebar && (
              <motion.button
                onClick={() => setShowSidebar(true)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="rounded-lg p-2 text-gray-500 transition-colors hover:text-white"
              >
                <Sidebar className="h-5 w-5" />
              </motion.button>
            )}
            <h1 className="text-xl font-bold text-white">Astra</h1>
          </div>
          <div className="flex items-center gap-2">
            {hasReasoningSteps && (
              <motion.button
                onClick={() => setShowReasoningPanel(!showReasoningPanel)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-all ${
                  showReasoningPanel
                    ? "bg-white text-black"
                    : "bg-white/5 text-white border border-white/10 hover:bg-white/10"
                }`}
              >
                Reasoning
              </motion.button>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="flex flex-1 overflow-hidden">
          {/* Main Panel */}
          <main className="flex-1 overflow-hidden">
            {children || (
              <>
                {activeTab === "chat" && <ChatWindow />}
                {activeTab === "documents" && <DocumentManager />}
                {activeTab === "insights" && <InsightsPanel />}
              </>
            )}
          </main>

          {/* Reasoning Panel (Right Side) */}
          <AnimatePresence>
            {showReasoningPanel && hasReasoningSteps && (
              <motion.aside
                initial={{ x: 400, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: 400, opacity: 0 }}
                transition={{
                  duration: 0.4,
                  ease: "easeOut",
                }}
                className="w-96 border-l border-white/10 bg-bg-void/50 backdrop-blur-xl"
              >
                <ReasoningPanel steps={currentMessage.reasoning_steps || []} />
              </motion.aside>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
