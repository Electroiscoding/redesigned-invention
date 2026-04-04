import asyncio
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class PerceptionData:
    def __init__(self, visible_agents: int, anomaly: bool, terrain: str = "rocky basalt", weather: str = "clear skies"):
        self.visible_agents = visible_agents
        self.anomaly = anomaly
        self.terrain = terrain
        self.weather = weather

class AgentOrchestrationService:
    """
    Main AI Orchestration Service for ParaEarth.
    Manages the full perception-cognition-action loop for thousands of agents.
    """
    def __init__(self, redis_client, db_session, openrouter_client, amr, aci, context_assembler):
        self.redis = redis_client
        self.db = db_session
        self.openrouter = openrouter_client
        self.amr = amr
        self.aci = aci
        self.context_assembler = context_assembler

    async def run_agent_cycle(self, agent: Any) -> None:
        """
        Execute one full perception-cognition-action cycle for a single agent.
        Runs fully asynchronously, designed to scale via Python asyncio.
        """
        logger.info(f"Starting cycle for agent: {agent.name} ({agent.agent_id})")

        # 1. Gather perception data from the Colyseus world state shard
        perception = await self._perceive(agent)

        # 2. Check for incoming structured/natural-language messages
        messages = await self._check_messages(agent.agent_id)

        # 3. Re-assess cognitive state based on world events (e.g. emergencies)
        agent.cognitive_state = self._assess_cognitive_state(perception, messages, agent)

        # 4. Adaptive Model Routing: Select appropriate free-tier OpenRouter model
        task_complexity = self._estimate_complexity(perception, messages)
        model_id = self.amr.select_model(
            agent.model_id,
            agent.cognitive_state,
            task_complexity=task_complexity
        )

        # 5. Assemble highly-compressed Memory Context Window
        # (Injects HEXACO personality and isolated memories)
        context = await self.context_assembler.assemble(
            agent=agent,
            perception=perception,
            incoming_messages=messages
        )

        # 6. Run Inference via OpenRouter API (Streaming Response)
        tool_calls = []
        outgoing_messages = []
        reasoning_trace = ""

        logger.info(f"[{agent.name}] Routing to {model_id}...")

        async for chunk in self.openrouter.stream_completion(
            model=model_id,
            messages=context.to_messages(),
            tools=context.available_tools,
            max_tokens=1024
        ):
            if chunk.type == "tool_call":
                tool_calls.append(chunk.tool_call)
            elif chunk.type == "message":
                outgoing_messages.append(chunk.message)
            elif chunk.type == "reasoning":
                reasoning_trace += chunk.text

        # 7. Execute validated Tool Calls in the World (ACI Sandbox)
        action_results = []
        for tool_call in tool_calls:
            result = await self.aci.execute(agent, tool_call)
            action_results.append(result)

        # 8. Send Outgoing Inter-Agent Communications
        for msg in outgoing_messages:
            await self._send_message(agent.agent_id, msg)

        # 9. Update Agent Internal State (e.g. inventory from mining)
        await self._update_agent_state(agent, action_results)

        # 10. Record Compression to Episodic Memory
        await self._record_memory(agent, perception, tool_calls, action_results, reasoning_trace)

        logger.info(f"Finished cycle for agent: {agent.name}")

    # --- Sub-routines ---

    async def _perceive(self, agent: Any) -> PerceptionData:
        """
        Gathers raw physical data about the agent's immediate vicinity.
        Queries the Redis 'CellCache' and 'GeographicRoom' representations
        maintained by the Colyseus authoritative world server.
        """
        # Determine current agent grid cell (e.g. S2 cell resolution equivalent)
        # Assuming agent.current_location is a dict with lat/lon/depth
        lat = agent.current_location.get("lat", 0.0)
        lon = agent.current_location.get("lon", 0.0)

        # 1. Fetch Local Weather/World State
        # (Usually published to Redis as 'world_state:shard_id' JSON blob by Colyseus EBM simulation)
        weather_desc = "clear skies"
        try:
            world_state_json = await self.redis.get("world_state:global_01")
            if world_state_json:
                import json
                state_data = json.loads(world_state_json)
                weather_desc = state_data.get("environment", {}).get("weather", "clear skies")
        except Exception as e:
            logger.debug(f"Failed to fetch global weather state: {e}")

        # 2. Fetch WCG Terrain/Chemistry Data
        # Queries the Redis cache bridging the Rust ERS engine
        # e.g., 'chem_cell:45:110:0:global_01'
        terrain_desc = "rocky basalt"
        try:
            # Simplified localized grid stringifier
            x, y, z = int(lat), int(lon), int(agent.current_location.get("depth", 0.0))
            cell_key = f"chem_cell:{x}:{y}:{z}:global_01"
            cell_json = await self.redis.get(cell_key)
            if cell_json:
                import json
                cell_data = json.loads(cell_json)
                comp = cell_data.get("composition", {})
                dominant_elements = sorted(comp.items(), key=lambda item: item[1], reverse=True)[:3]
                terrain_desc = f"{cell_data.get('phase_state', 'Solid')} terrain rich in {[e[0] for e in dominant_elements]}"
        except Exception as e:
            logger.debug(f"Failed to fetch localized chemistry cell state: {e}")

        # 3. Discover Nearby Agents (Spatial Query / Area of Interest)
        # Simplified: Assuming Colyseus pushes a set of nearby agents per shard
        visible_agents = 0
        try:
            agents_set = await self.redis.smembers("active_agents:global_01")
            # If spatial logic existed here, we would measure distance between vectors.
            # Assuming everyone in shard is visible for demo
            visible_agents = max(0, len(agents_set) - 1)
        except Exception as e:
            pass

        return PerceptionData(
            visible_agents=visible_agents,
            anomaly=False,
            terrain=terrain_desc,
            weather=weather_desc
        )

    async def _check_messages(self, agent_id: str) -> list:
        # Reads from agent-messages:{agent_id} Redis stream
        return []

    def _assess_cognitive_state(self, perception: PerceptionData, messages: list, agent: Any) -> Any:
        return agent.cognitive_state

    def _estimate_complexity(self, perception: PerceptionData, messages: list) -> float:
        complexity = len(messages) * 0.1
        complexity += perception.visible_agents * 0.05
        complexity += 0.3 if perception.anomaly else 0.0
        return min(1.0, complexity)

    async def _send_message(self, agent_id: str, msg: Any):
        pass

    async def _update_agent_state(self, agent: Any, action_results: list):
        """
        Parses successful action returns and persists state changes
        (e.g., updating agent inventory after a `mine` or `react` call).
        """
        for result in action_results:
            if result.get("status") == "success":
                logger.debug(f"[{agent.name}] Action success: {result.get('message')}")

                # We could run deeper validation/DB sync here.
                # The agent's active memory dictionary was already mutated in `tools.py`
                # by reference, so we primarily use this block to push the entire JSON
                # state blob down to Redis for caching.

                # e.g., await self.redis.set(f"agent_state:{agent.agent_id}", agent.json())
            elif result.get("status") == "error":
                logger.warning(f"[{agent.name}] Action failed: {result.get('message')}")

    async def _record_memory(self, agent, perception, actions, results, reasoning):
        """
        Commits the completed cycle's perception, actions, and internal monologue
        into the persistent episodic memory store for later retrieval and compression.
        """
        try:
            success = await self.context_assembler.episodic.record(
                agent_id=agent.agent_id,
                perception=perception,
                actions=actions,
                results=results,
                reasoning_trace=reasoning
            )
            if success:
                logger.debug(f"[{agent.name}] Episodic memory cycle recorded.")
            else:
                logger.error(f"[{agent.name}] Failed to record episodic memory cycle.")
        except AttributeError:
            # Fallback if self.context_assembler.episodic isn't tightly bound yet
            logger.warning(f"[{agent.name}] Episodic store not bound to ContextAssembler. Skipping memory recording.")
