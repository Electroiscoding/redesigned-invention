import asyncio
import logging
import json
from typing import List, Dict, Any

from app.memory.semantic import SemanticMemoryStore
from app.memory.episodic import EpisodicMemoryStore
from app.memory.procedural import ProceduralMemoryStore
from app.memory.social_graph import SocialMemoryGraph
from core.types import Agent

logger = logging.getLogger(__name__)

class ContextWindow:
    def __init__(self, system_prompt: str, messages: List[Dict[str, str]], tools: List[Dict]):
        self.system_prompt = system_prompt
        self.messages = messages
        self.available_tools = tools

    def to_messages(self) -> List[Dict[str, str]]:
        return [{"role": "system", "content": self.system_prompt}] + self.messages

class ContextWindowAssembler:
    """
    Memory Assembly Engine (MAE).
    Balances completeness with context window token budgets by integrating
    multiple independent memory stores via priority weighting.
    """
    def __init__(self, db_pool=None):
        self.semantic = SemanticMemoryStore(db_pool)
        self.episodic = EpisodicMemoryStore(db_pool)
        self.procedural = ProceduralMemoryStore()
        self.social = SocialMemoryGraph()

    async def assemble(self, agent: Agent, perception: Any, incoming_messages: List[Any]) -> ContextWindow:
        logger.info(f"Assembling context window for {agent.name} ({agent.agent_id})...")

        # 1. Current Perception (Always Included)
        perception_dict = perception.__dict__ if hasattr(perception, "__dict__") else str(perception)
        perception_text = f"[Current Perception]: {json.dumps(perception_dict)}"

        # 2. Recent Episodic Memories (Short-term context)
        recent_episodes = await self.episodic.get_recent(agent.agent_id, 5)
        episode_summary = f"[Recent Episodes]: {json.dumps([ep['content'] for ep in recent_episodes])}"

        # 3. Semantic Memory Retrieval (Long-term knowledge)
        # Create a search query vector based on the immediate situation + incoming messages
        incoming_texts = [msg.get("content", "") if isinstance(msg, dict) else str(msg) for msg in incoming_messages]
        query_string = perception_text + " ".join(incoming_texts)

        relevant_knowledge = await self.semantic.query(agent.agent_id, query_string, top_k=3)
        knowledge_summary = "[Relevant Knowledge]: " + "\n".join(
            [f"- {k['content']} (Similarity: {k['similarity']:.2f})" for k in relevant_knowledge]
        )

        # 4. Social Context
        # Theory of Mind approximation for interlocutors
        social_contexts = []
        for msg in incoming_messages:
            sender_id = msg.get("sender_id") if isinstance(msg, dict) else None
            if sender_id:
                rel = await self.social.get_relationship(agent.agent_id, sender_id)
                social_contexts.append(f"Relationship with {sender_id}: {rel['relationship_type']} (Trust: {rel['trust_level']})")
        social_summary = "[Social Relationships]:\n" + "\n".join(social_contexts) if social_contexts else ""

        # Assemble the internal monologue block (what the LLM 'sees' as its current state)
        internal_monologue = (
            f"You are currently experiencing the following:\n"
            f"{perception_text}\n"
            f"{episode_summary}\n"
            f"{knowledge_summary}\n"
            f"{social_summary}\n"
            f"[Emotional State]: {agent.emotional_state}\n"
            f"[Current Goals]: {agent.goal_stack}\n"
            f"[Inventory]: {agent.inventory}\n"
            f"Think step-by-step using your reasoning trace before executing a tool call."
        )

        # Combine into a single final user message
        messages = [
            {"role": "user", "content": internal_monologue}
        ]

        # Add incoming messages directly into the chat history
        for msg in incoming_messages:
            if isinstance(msg, dict) and "content" in msg:
                messages.append({"role": "user", "content": f"Message from {msg.get('sender_id', 'Unknown')}: {msg['content']}"})

        # Define ACI tool schema
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "mine_element",
                    "description": "Extract an element from the current location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_species": {"type": "string"},
                            "quantity_kg": {"type": "number"}
                        },
                        "required": ["target_species", "quantity_kg"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "react_materials",
                    "description": "Attempt to trigger a thermodynamic reaction between inventory materials.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reagents": {
                                "type": "object",
                                "additionalProperties": {"type": "number"},
                                "description": "Mapping of species to kg amount."
                            },
                            "temperature_k": {"type": "number"}
                        },
                        "required": ["reagents", "temperature_k"]
                    }
                }
            }
        ]

        return ContextWindow(agent.system_prompt, messages, tools)
