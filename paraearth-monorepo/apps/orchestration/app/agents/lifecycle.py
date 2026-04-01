import uuid
from typing import Dict, Any
from core.types import AgentCognitiveState, Agent

class BirthProtocol:
    def __init__(self):
        pass

    def generate_name(self) -> str:
        return "Tharavel"

    def generate_personality(self) -> Dict[str, float]:
        return {
            "honesty_humility": 0.5,
            "emotionality": 0.5,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "conscientiousness": 0.5,
            "openness": 0.5
        }

    def initialize_agent(self, role: str) -> Agent:
        return Agent(
            agent_id=str(uuid.uuid4()),
            name=self.generate_name(),
            model_id="anthropic/claude-3-haiku",
            system_prompt="You are a new agent.",
            cognitive_state=AgentCognitiveState.ACTIVE
        )