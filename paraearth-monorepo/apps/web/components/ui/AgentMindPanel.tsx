"use client";

interface AgentMindPanelProps {
  agentId: string;
}

export function AgentMindPanel({ agentId }: AgentMindPanelProps) {
  // In a real application, fetch this from the /api/agent/{id}/state endpoint
  const mockAgentData = {
    name: "Tharavel",
    role: "Geologist",
    state: "ACTIVE",
    hexaco: {
      honesty: 0.8,
      emotionality: 0.3,
      extraversion: 0.5,
      agreeableness: 0.9,
      conscientiousness: 0.9,
      openness: 0.7,
    },
    goalStack: [
      "Smelt iron for a stronger pickaxe",
      "Find a carbon source (coal or wood)",
      "Mine 10kg of Fe2O3",
    ],
    inventory: {
      "Fe2O3": 12.5, // kg
      "Stone": 5.0,
      "Iron Pickaxe": 1
    }
  };

  return (
    <div className="bg-glass-bg backdrop-blur-glass p-5 rounded-xl border border-gray-700 shadow-xl text-white flex-shrink-0">
      <div className="flex justify-between items-center mb-4 border-b border-gray-600 pb-2">
        <h3 className="text-lg font-bold text-element-o tracking-wider">{mockAgentData.name}</h3>
        <span className="text-xs px-2 py-1 bg-element-o text-black rounded font-bold uppercase">
          {mockAgentData.role}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* HEXACO Profile */}
        <div>
          <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-2">Cognitive Profile</h4>
          {Object.entries(mockAgentData.hexaco).map(([trait, val]) => (
            <div key={trait} className="mb-1 flex items-center justify-between">
              <span className="text-xs capitalize">{trait.substring(0, 4)}</span>
              <div className="w-16 h-1.5 bg-gray-800 rounded overflow-hidden">
                <div className="h-full bg-element-o" style={{ width: `${val * 100}%` }} />
              </div>
            </div>
          ))}
        </div>

        {/* Goals & Inventory */}
        <div className="flex flex-col gap-4">
          <div>
            <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-2">Goal Stack</h4>
            <ul className="text-xs list-disc list-inside pl-2 space-y-1">
              {mockAgentData.goalStack.map((goal, idx) => (
                <li key={idx} className={idx === 0 ? "text-element-he font-bold" : "text-gray-300"}>
                  {goal}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h4 className="text-xs uppercase tracking-wider text-gray-400 mb-2">Inventory</h4>
            <div className="text-xs space-y-1">
              {Object.entries(mockAgentData.inventory).map(([item, qty]) => (
                <div key={item} className="flex justify-between">
                  <span>{item}</span>
                  <span className="text-gray-400">{qty} {typeof qty === 'number' && qty % 1 !== 0 ? 'kg' : ''}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
