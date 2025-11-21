"use client";

export default function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 px-4 py-3">
      <div className="flex gap-1">
        <div className="h-2 w-2 rounded-full bg-gray-500 bounce-dot" />
        <div className="h-2 w-2 rounded-full bg-gray-500 bounce-dot" />
        <div className="h-2 w-2 rounded-full bg-gray-500 bounce-dot" />
      </div>
      <span className="ml-2 text-sm text-gray-500">AI is thinking...</span>
    </div>
  );
}
