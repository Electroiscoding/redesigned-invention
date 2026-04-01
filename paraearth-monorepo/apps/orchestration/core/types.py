from pydantic import BaseModel
from typing import Dict, List, Optional
from enum import Enum

class AgentCognitiveState(Enum):
    ACTIVE = "active"
    DELIBERATING = "deliberating"
    COMMUNICATING = "communicating"
    RESTING = "resting"
    EMERGENCY = "emergency"

class Agent(BaseModel):
    agent_id: str
    name: str
    model_id: str
    system_prompt: str
    cognitive_state: AgentCognitiveState

    current_location: Dict[str, float] = {}
    emotional_state: Dict[str, float] = {}
    goal_stack: List[str] = []
    inventory: Dict[str, float] = {}