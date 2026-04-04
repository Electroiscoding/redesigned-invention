"use client";

import { useEffect, useState, useRef } from "react";
import { Client, Room } from "colyseus.js";

export default function ParticipantPage() {
  const [room, setRoom] = useState<Room | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const [actionInput, setActionInput] = useState<string>('{"name": "mine_element", "arguments": {"target_species": "Fe2O3", "quantity_kg": 5.0}}');

  useEffect(() => {
    // Connect to the Node.js/Colyseus World Server
    const client = new Client(process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:2567");

    client.joinOrCreate("geographic_room").then(r => {
      setRoom(r);
      setLogs(prev => [...prev, `[System] Connected as Avatar ${r.sessionId}`]);

      // Listen for incoming global environmental changes
      r.onMessage("world_event", (message) => {
        setLogs(prev => [...prev, `[World] ${message}`]);
      });

    }).catch(e => {
      console.error("[Colyseus] Join error", e);
      setLogs(prev => [...prev, `[System] Failed to connect: ${e.message}`]);
    });

    return () => {
      if (room) {
        room.leave();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sendAction = () => {
    if (!room) return;
    try {
      const parsedAction = JSON.parse(actionInput);
      room.send("agent_action", parsedAction);
      setLogs(prev => [...prev, `[You] Sent action: ${parsedAction.name}`]);
    } catch (err) {
      setLogs(prev => [...prev, `[System] Invalid JSON action.`]);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white font-mono p-6 flex flex-col items-center">
      <div className="max-w-2xl w-full bg-gray-900 border border-gray-700 shadow-xl rounded-xl p-6">
        <h1 className="text-2xl font-bold text-element-he mb-4">ParaEarth / P-Mode (Avatar)</h1>

        <div className="mb-6">
          <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-2">Event Log</h2>
          <div className="h-48 bg-black rounded p-3 overflow-y-auto border border-gray-800 text-sm space-y-1">
            {logs.map((log, idx) => (
              <div key={idx} className={log.startsWith("[System]") ? "text-gray-500" : "text-green-400"}>
                {log}
              </div>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-sm uppercase tracking-wider text-gray-500 mb-2">Raw Tool Call (JSON)</h2>
          <textarea
            value={actionInput}
            onChange={(e) => setActionInput(e.target.value)}
            className="w-full h-24 bg-black border border-gray-700 text-gray-300 rounded p-3 focus:outline-none focus:border-element-he"
          />
          <button
            onClick={sendAction}
            disabled={!room}
            className="mt-3 w-full bg-element-he hover:bg-green-500 text-black font-bold py-2 px-4 rounded transition-colors disabled:opacity-50"
          >
            Execute Direct ERS Action
          </button>
        </div>
      </div>
    </div>
  );
}
