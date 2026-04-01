# Welcome to ParaEarth: A Massively Multi-Agent Photorealistic Parallel Earth Simulator

ParaEarth represents a complete, inhabitable simulation of reality—a world you can enter, modify, and in which cause and effect operate with perfect fidelity to physical law, powered entirely by OpenRouter AI models for emergent civilization dynamics.

## Features
- **Elemental Reaction Substrate (ERS)**: A WebAssembly chemistry engine (Rust) grounded in real-world periodic table thermodynamics.
- **Agent Civilization Emergence Framework (ACEF)**: Massive multi-agent orchestration (Python/FastAPI) driven by OpenRouter free-tier LLMs.
- **WebGPU Material Synthesis Pipeline (WMSP)**: Real-time Next.js + Three.js shader pipeline that renders exact chemical structures as PBR materials.
- **Spherical Tectonic Noise Model (STNM)**: A planetary generator driving terrain, weather, and climate systems.

---

## 🛠️ Hyper-Detailed Setup & Installation Guide

This monorepo uses `pnpm` and `turbo` to manage multiple microservices. You must have Node.js 20+, Rust (for WebAssembly compilation), and Python 3.12+ installed.

### 1. Prerequisites & Dependencies

**System Requirements:**
- Node.js >= 20.0.0
- pnpm >= 8.0.0
- Python 3.12+ (with `pip` and `venv`)
- Rust toolchain (`rustup`, `cargo`)
- PostgreSQL 16+ (with `pgvector` extension)
- Redis Server (local or Dockerized)

**Install Dependencies:**
```bash
# Clone the repository
git clone https://github.com/your-username/paraearth-monorepo.git
cd paraearth-monorepo

# Install monorepo Node dependencies
pnpm install

# Install wasm-pack for the Rust ERS-core
cargo install wasm-pack
```

### 2. Environment Configuration

Copy the `.env.example` file to create your own `.env` file at the root of the project:

```bash
cp .env.example .env
```

**Required Environment Variables:**
- `DATABASE_URL`: Your PostgreSQL connection string. Ensure the `pgvector` extension is enabled on this database.
- `REDIS_URL`: Your Redis connection string.
- `OPENROUTER_API_KEY`: Your OpenRouter key. ParaEarth is configured to use *only free models* by default (e.g., `nvidia/nemotron-nano-12b-v2-vl:free`, `meta-llama/llama-3.3-70b-instruct:free`, `google/gemini-2.0-flash-exp:free`).

*Note: ParaEarth leverages the same base LLM to simulate multiple unique agents. It accomplishes this by injecting heavily distinct HEXACO personality profiles, localized episodic memories, and specialized vocational system prompts per agent, effectively "treating different humans/bodies" via distinct isolated cognitive states.*

### 3. Building the Sub-Packages

Before running the main applications, you must build the shared libraries and the Rust WebAssembly engine.

```bash
# Compile the Rust ERS engine to WebAssembly
cd packages/ers-core
wasm-pack build --target web --release
cd ../..

# Build the shared TypeScript packages
pnpm turbo run build --filter="@paraearth/shared-types" --filter="@paraearth/planet-gen" --filter="@paraearth/ui-config"
```

### 4. Running the Services

ParaEarth requires three main services to be running concurrently:

**A. The AI Orchestration Backend (FastAPI)**
This service manages agent state, memory (MIP), and OpenRouter inferences.
```bash
cd apps/orchestration
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**B. The Authoritative World Server (Node.js/Colyseus)**
This service manages the real-time WebSocket/WebTransport connections, geographic sharding, and ERS chemistry grid state.
```bash
cd apps/world-server
pnpm run dev
```

**C. The WebGPU Frontend (Next.js)**
This service delivers the photorealistic browser experience.
```bash
cd apps/web
pnpm run dev
```
Access the application at `http://localhost:3000`.

### 5. Using the Application

1. **Onboarding:** Navigate to the onboarding flow (`/config`) to select your planet's seed, size, and initial AI agent population size.
2. **God-View Mode (`/observer`):** Fly around the procedurally generated spherical world, inspect geological strata via the `ChemInspector`, and click on agents to view their `AgentMindPanel` and `ReasoningStream` (which streams OpenRouter LLM thoughts in real-time).
3. **Avatar Mode (`/participant`):** Spawn a human avatar into the simulation and communicate with AI agents via the chat interface. Your avatar possesses its own inventory and can manually trigger ERS chemistry functions (e.g., smelting iron or starting a fire).

## 🌍 World & Agent Mechanics

- **Mass Conservation:** The ERS engine enforces strict thermodynamic mass conservation. An agent cannot "create" a steel sword; they must physically mine 2kg of `Fe2O3` (Hematite), gather carbon, construct a bloomery, and pass the required activation energy threshold.
- **Agent Individuality:** Even though you may only have one free OpenRouter LLM enabled, the `Adaptive Model Router (AMR)` will instantiate 1,000 agents that feel completely distinct by dynamically weaving their isolated semantic memory (`pgvector`) and recent episodic logs into the prompt.
- **Emergent Society:** Agents will automatically use the `A2AProtocol` to negotiate resource trades, form alliances, and build physical structures based on their shared or divergent goals.