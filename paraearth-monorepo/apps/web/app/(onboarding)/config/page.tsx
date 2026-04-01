"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ConfigPage() {
  const [population, setPopulation] = useState<number>(50);
  const [preset, setPreset] = useState<string>("archaic-earth");
  const router = useRouter();

  const handleLaunch = () => {
    // In a real app, this sends config data to the backend before redirecting
    console.log("Launching simulation with:", { population, preset });
    router.push("/observer");
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-900 text-white p-6">
      <div className="bg-glass-bg backdrop-blur-glass p-8 rounded-2xl border border-gray-700 shadow-xl max-w-lg w-full">
        <h1 className="text-3xl font-bold mb-6 text-center text-element-o">Configure World</h1>

        <div className="mb-6">
          <label className="block text-sm font-medium mb-2" htmlFor="preset">
            World Preset
          </label>
          <select
            id="preset"
            value={preset}
            onChange={(e) => setPreset(e.target.value)}
            className="w-full bg-gray-800 text-white rounded-lg p-3 border border-gray-600 focus:outline-none focus:border-element-o"
          >
            <option value="archaic-earth">Archaic Earth (Hadean/Archean)</option>
            <option value="terra-nova">Terra Nova (Lush)</option>
            <option value="volcanic-hell">Volcanic Hellscape</option>
            <option value="ocean-world">Ocean World</option>
          </select>
        </div>

        <div className="mb-8">
          <label className="flex justify-between text-sm font-medium mb-2" htmlFor="population">
            <span>Agent Population Size</span>
            <span className="text-element-o font-bold">{population}</span>
          </label>
          <input
            id="population"
            type="range"
            min="10"
            max="1000"
            step="10"
            value={population}
            onChange={(e) => setPopulation(parseInt(e.target.value))}
            className="w-full accent-element-o"
          />
          <p className="text-xs text-gray-400 mt-2">
            Warning: Higher populations consume more API tokens and backend CPU compute.
          </p>
        </div>

        <button
          onClick={handleLaunch}
          className="w-full bg-element-o hover:bg-teal-500 text-black font-bold py-3 px-4 rounded-lg transition-colors"
        >
          Initialize Simulation
        </button>
      </div>
    </div>
  );
}
