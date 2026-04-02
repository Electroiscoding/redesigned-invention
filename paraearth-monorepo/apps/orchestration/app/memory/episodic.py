import logging
from datetime import datetime, timezone
import json
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class EpisodicMemoryStore:
    """
    Episodic Memory Compression system.
    Caches the immediate time-ordered log of experiences (perception, action, communication),
    and systematically compresses older memory blocks via a cheap LLM call to maintain an
    efficient context window (Ebbinghaus forgetting curve simulation).
    """
    def __init__(self, db_pool=None, openrouter_client=None):
        self.pool = db_pool
        self.openrouter = openrouter_client

    async def record(self, agent_id: str, perception: Any, actions: List[Dict], results: List[Dict], reasoning_trace: str) -> bool:
        """
        Record a full perception-action cycle as a discrete, raw episodic memory.
        """
        content = json.dumps({
            "perception": perception.__dict__ if hasattr(perception, "__dict__") else str(perception),
            "actions": actions,
            "results": results,
            "reasoning": reasoning_trace
        })

        timestamp = datetime.now(timezone.utc)

        query = """
            INSERT INTO agent_episodic_memory (agent_id, timestamp, event_type, content, retention_score, summary_level)
            VALUES ($1, $2, 'ACTION', $3, 1.0, 0)
        """

        try:
            # await self.pool.execute(query, agent_id, timestamp, content)
            logger.debug(f"Recorded raw episode for agent {agent_id}.")
            return True
        except Exception as e:
            logger.error(f"Error recording episodic memory: {e}")
            return False

    async def get_recent(self, agent_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the N most recent unsummarized episodic memories.
        """
        query = """
            SELECT timestamp, content
            FROM agent_episodic_memory
            WHERE agent_id = $1 AND summary_level = 0
            ORDER BY timestamp DESC
            LIMIT $2;
        """

        try:
            # records = await self.pool.fetch(query, agent_id, limit)
            # return [dict(r) for r in records]

            # Returning mock recent records
            return [
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "content": '{"perception": {"visible_agents": 1}, "actions": [], "results": []}'
                }
            ]
        except Exception as e:
            logger.error(f"Error retrieving recent episodes: {e}")
            return []

    async def summarize_batch(self, agent_id: str, records: List[Dict[str, Any]]) -> str:
        """
        Compresses a batch of 100 raw cycles into a single narrative day summary
        using a tier-3 OpenRouter model (e.g. Llama 3.1 8B).
        """
        if not self.openrouter:
            return "Simulated summary of 100 cycles: Mined iron, negotiated with Mossik, slept."

        system_prompt = "You are a cognitive compression engine. Summarize the following timeline of events for an agent concisely."
        user_prompt = f"Agent {agent_id} Events:\n"
        for rec in records:
            user_prompt += f"- {rec['timestamp']}: {rec['content']}\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            summary = ""
            async for chunk in self.openrouter.stream_completion(
                model="meta-llama/llama-3.1-8b-instruct",
                messages=messages,
                tools=[],
                max_tokens=150
            ):
                if chunk.type == "message":
                    summary += chunk.message.get("content", "")

            logger.info(f"Compressed {len(records)} episodes into: {summary}")
            return summary
        except Exception as e:
            logger.error(f"Error summarizing episodes: {e}")
            return ""

    async def consolidate_memory(self, agent_id: str):
        """
        Background task: Triggered when agent enters RESTING state.
        Fetches the oldest unsummarized records, summarizes them, writes the summary
        back with summary_level=1, and deletes the raw logs.
        """
        # 1. Fetch 100 oldest summary_level=0 records
        # 2. Call summarize_batch
        # 3. Write new summary_level=1 record
        # 4. Delete the 100 summary_level=0 records
        pass