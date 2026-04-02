import asyncio
import sys
import os

# Ensure the root apps/orchestration is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../apps/orchestration')))

from app.memory.semantic import SemanticMemoryStore
from app.memory.episodic import EpisodicMemoryStore
from app.llm.context_assembler import ContextWindowAssembler
from core.types import Agent, AgentCognitiveState
import logging

logging.basicConfig(level=logging.INFO)

async def main():
    print("Testing ParaEarth Memory Pipeline...")

    # Mock DB Pool
    db_pool = None

    # Initialize components
    semantic_store = SemanticMemoryStore(db_pool)
    episodic_store = EpisodicMemoryStore(db_pool)
    assembler = ContextWindowAssembler(db_pool)

    # Create dummy agent
    agent = Agent(
        agent_id="agent-001",
        name="Tharavel",
        model_id="nemotron-nano-12b-v2-vl:free",
        system_prompt="You are a Geologist with high conscientiousness.",
        cognitive_state=AgentCognitiveState.ACTIVE,
        emotional_state={"stress": 0.1, "curiosity": 0.8},
        goal_stack=["Find Copper", "Build Furnace"],
        inventory={"Fe2O3": 10.0, "C": 5.0}
    )

    # 1. Test Semantic Memory insertion/query
    print("\n--- Testing Semantic Memory (MIP) ---")
    await semantic_store.store(agent.agent_id, "Copper (Cu) is often found near volcanic boundaries.")
    results = await semantic_store.query(agent.agent_id, "Where can I find copper?", top_k=1)
    print(f"Query Results: {results}")

    # 2. Test Episodic Memory Record
    print("\n--- Testing Episodic Compression ---")
    class DummyPerception:
        def __init__(self):
            self.visible_agents = 0
            self.anomaly = False
            self.terrain = "Rocky basalt"

    perception = DummyPerception()
    await episodic_store.record(agent.agent_id, perception, [], [], "Thinking about mining.")
    recent = await episodic_store.get_recent(agent.agent_id)
    print(f"Recent Episode: {recent[0] if recent else 'None'}")

    # 3. Test Context Window Assembly
    print("\n--- Testing Context Assembler ---")
    incoming_messages = [{"sender_id": "agent-002", "content": "Hello Tharavel, I found some iron ore!"}]

    context_window = await assembler.assemble(agent, perception, incoming_messages)

    print("\nGenerated Context Window:")
    print("System Prompt:", context_window.system_prompt)
    print("\nMessages Payload:")
    for msg in context_window.messages:
        print(f"[{msg['role'].upper()}]: {msg['content']}")

    print("\nAvailable Tools Schema:")
    print([t["function"]["name"] for t in context_window.available_tools])

if __name__ == "__main__":
    asyncio.run(main())
