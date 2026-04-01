import uuid
import random
from typing import Dict
from core.types import AgentCognitiveState, Agent

class BirthProtocol:
    """
    Birth Protocol for AI Agents.
    Responsible for generating distinct personalities and roles, which is critical
    when using the same free-tier LLM for multiple agents across the simulation.
    """

    def __init__(self):
        self.vocational_roles = [
            "Geologist", "Chemist", "Architect", "Agronomist",
            "Merchant", "Philosopher", "Healer", "Engineer"
        ]

    def generate_name(self) -> str:
        # Simplified procedural name generation
        prefixes = ["Tha", "Mos", "Je", "Orr", "Sel", "Ca"]
        suffixes = ["ravel", "sik", "dunne", "avi", "phen", "rutho"]
        return random.choice(prefixes) + random.choice(suffixes)

    def generate_personality(self) -> Dict[str, float]:
        """
        Generates a HEXACO personality vector (Honesty-Humility, Emotionality,
        eXtraversion, Agreeableness, Conscientiousness, Openness).
        Values are drawn from a normal distribution around 0.5 with a clamp to [0.0, 1.0].
        """
        def get_trait() -> float:
            return max(0.0, min(1.0, random.gauss(0.5, 0.15)))

        return {
            "honesty_humility": get_trait(),
            "emotionality": get_trait(),
            "extraversion": get_trait(),
            "agreeableness": get_trait(),
            "conscientiousness": get_trait(),
            "openness": get_trait()
        }

    def generate_system_prompt(self, role: str, personality: Dict[str, float]) -> str:
        return (
            f"You are an autonomous AI inhabitant of a parallel Earth. "
            f"Your vocational role is {role}. "
            f"Your personality traits are: {personality}. "
            "You must act according to your role and personality."
        )

    def initialize_agent(self) -> Agent:
        role = random.choice(self.vocational_roles)
        personality = self.generate_personality()
        sys_prompt = self.generate_system_prompt(role, personality)

        return Agent(
            agent_id=str(uuid.uuid4()),
            name=self.generate_name(),
            model_id="nvidia/nemotron-nano-12b-v2-vl:free", # default assignment
            system_prompt=sys_prompt,
            cognitive_state=AgentCognitiveState.ACTIVE
        )
