"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function VaultPage() {
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ openrouter_key: apiKey }),
      });

      if (!response.ok) {
        throw new Error("Failed to securely register API key.");
      }

      const data = await response.json();

      // Store temporary proxy token on the client-side
      sessionStorage.setItem("proxy-token", data.token);

      // Redirect to world config
      router.push("/config");
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950 p-6 font-sans">
      <div className="bg-glass-bg border border-gray-800 shadow-2xl rounded-xl p-8 max-w-md w-full backdrop-blur-glass">
        <h2 className="text-3xl font-extrabold text-white mb-2 text-center">ParaEarth Vault</h2>
        <p className="text-gray-400 text-sm mb-6 text-center">
          Securely submit your OpenRouter API Key. It is immediately encrypted using a server-side HSM key and never stored in localStorage.
        </p>

        {error && (
          <div className="bg-red-500 bg-opacity-20 border border-element-h text-element-h p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister}>
          <div className="mb-6">
            <label htmlFor="apiKey" className="block text-gray-300 text-sm font-medium mb-2">
              OpenRouter API Key
            </label>
            <input
              type="password"
              id="apiKey"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-or-v1-..."
              required
              className="w-full bg-gray-900 border border-gray-700 text-white text-sm rounded-lg focus:ring-element-o focus:border-element-o block p-3 placeholder-gray-600 outline-none transition"
            />
            <p className="mt-2 text-xs text-gray-500">
              Only free models like `nvidia/nemotron-nano-12b-v2-vl:free` will be used to prevent runaway costs.
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || !apiKey.trim()}
            className="w-full text-black bg-white hover:bg-gray-200 focus:ring-4 focus:outline-none focus:ring-gray-300 font-bold rounded-lg text-sm px-5 py-3 text-center transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Encrypting & Storing..." : "Secure Key & Enter"}
          </button>
        </form>
      </div>
    </div>
  );
}
