"use client";

import { useEffect, useState, useRef } from "react";

interface ReasoningStreamProps {
  agentId: string;
}

export function ReasoningStream({ agentId }: ReasoningStreamProps) {
  const [streamData, setStreamData] = useState<string>("");
  const endOfStreamRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // In a real application, this connects to the FastAPI orchestration SSE endpoint
    // `http://localhost:8000/api/agent/${agentId}/reasoning-stream`

    // Local mocking logic for demonstration
    const fakeTokens = [
      "The ", "sun ", "is ", "setting. ", "I ", "must ", "find ", "shelter ", "before ",
      "my ", "thermal ", "tolerance ", "is ", "exceeded. ", "\n\n",
      "Searching ", "episodic ", "memory...\n",
      "I ", "remember ", "a ", "cave ", "200m ", "north.\n\n",
      "<tool_call: move_to_location(lat=45.1, lon=-110.2)>"
    ];

    let currentIdx = 0;
    const interval = setInterval(() => {
      if (currentIdx < fakeTokens.length) {
        setStreamData((prev) => prev + fakeTokens[currentIdx]);
        currentIdx++;
      } else {
        clearInterval(interval);
      }
    }, 100); // Token streaming cadence

    return () => clearInterval(interval);
  }, [agentId]);

  // Auto-scroll
  useEffect(() => {
    if (endOfStreamRef.current) {
      endOfStreamRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [streamData]);

  return (
    <div className="bg-glass-bg backdrop-blur-glass p-5 rounded-xl border border-gray-700 shadow-xl text-green-400 flex-1 flex flex-col overflow-hidden font-mono">
      <div className="flex justify-between items-center mb-4 border-b border-gray-600 pb-2">
        <h3 className="text-sm font-bold text-gray-300 tracking-wider">LIVE LLM REASONING</h3>
        <span className="text-xs px-2 py-0.5 bg-green-900/50 text-green-400 rounded-full animate-pulse border border-green-500">
          STREAMING
        </span>
      </div>

      <div className="flex-1 overflow-y-auto text-sm leading-relaxed whitespace-pre-wrap scrollbar-thin scrollbar-thumb-gray-600">
        {streamData}
        <span className="animate-pulse text-gray-500">▋</span>
        <div ref={endOfStreamRef} />
      </div>
    </div>
  );
}
