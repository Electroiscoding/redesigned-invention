import logging
import re
from typing import Set

logger = logging.getLogger(__name__)

class LinguisticsTracker:
    """
    Emergent Linguistics Tracker.
    Parses LLM agent communications to detect out-of-vocabulary neologisms.
    Over time, tracks the spread of these novel terms across communities to
    document emergent dialects/vocabularies.
    """
    def __init__(self, base_vocabulary: Set[str] = None):
        # A small stub representing known English/ParaEarth words
        self.base_vocabulary = base_vocabulary or {"the", "a", "is", "rock", "stone", "iron", "copper", "fire", "water", "I", "you", "we", "build", "mine"}
        self.neologisms = {} # term -> { "coiner": agent_id, "adopters": set() }

    def track_neologisms(self, text: str, agent_id: str):
        """
        Extract alphabetic words from raw text, check against the base vocabulary,
        and log the introduction or adoption of novel terms.
        """
        # Simple tokenization (lowercase, strip punctuation)
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())

        for w in words:
            if w not in self.base_vocabulary:
                if w not in self.neologisms:
                    # New coined term
                    self.neologisms[w] = {
                        "coiner": agent_id,
                        "adopters": {agent_id}
                    }
                    logger.info(f"Agent {agent_id} coined new term: '{w}'")
                else:
                    # Term adoption by another agent
                    if agent_id not in self.neologisms[w]["adopters"]:
                        self.neologisms[w]["adopters"].add(agent_id)
                        logger.info(f"Agent {agent_id} adopted neologism: '{w}'")

    def get_emergent_dialect(self, threshold: int = 5) -> list:
        """
        Returns a list of neologisms that have reached a critical mass of adopters,
        meaning they've officially entered the local community's dialect.
        """
        return [term for term, data in self.neologisms.items() if len(data["adopters"]) >= threshold]
