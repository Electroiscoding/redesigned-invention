import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SocialMemoryGraph:
    """
    Social Memory Graph.
    Tracks relationships, trust levels, and interaction counts between agents.
    Maintained as edges in PostgreSQL or a dedicated graph DB in production.
    """
    def __init__(self, db_pool=None):
        self.pool = db_pool
        # In-memory stub for testing
        self._graph = {}

    async def get_relationship(self, agent_id: str, other_agent_id: str) -> Dict[str, Any]:
        """
        Retrieves the social edge between two agents.
        Returns neutral default if no relationship exists.
        """
        edge_key = f"{agent_id}->{other_agent_id}"

        if edge_key in self._graph:
            return self._graph[edge_key]

        return {
            "trust_level": 0.5,
            "relationship_type": "NEUTRAL",
            "interaction_count": 0,
            "sentiment": 0.0
        }

    async def update_relationship(self, agent_id: str, other_agent_id: str, interaction_summary: str, sentiment_delta: float = 0.0):
        """
        Updates the social graph edge after an interaction.
        """
        edge_key = f"{agent_id}->{other_agent_id}"

        # Upsert logic
        if edge_key not in self._graph:
            self._graph[edge_key] = {
                "trust_level": 0.5,
                "relationship_type": "ACQUAINTANCE",
                "interaction_count": 1,
                "sentiment": sentiment_delta
            }
        else:
            rel = self._graph[edge_key]
            rel["interaction_count"] += 1
            rel["sentiment"] = max(-1.0, min(1.0, rel["sentiment"] + sentiment_delta))

            # Simple threshold logic for relationship evolution
            if rel["sentiment"] > 0.6 and rel["interaction_count"] > 10:
                rel["relationship_type"] = "FRIEND/COLLABORATOR"
                rel["trust_level"] = min(1.0, rel["trust_level"] + 0.1)
            elif rel["sentiment"] < -0.4:
                rel["relationship_type"] = "RIVAL/HOSTILE"
                rel["trust_level"] = max(0.0, rel["trust_level"] - 0.2)

        logger.info(f"Updated relationship {edge_key}: {self._graph[edge_key]}")
