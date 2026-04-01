from enum import Enum

class AgentCognitiveState(Enum):
    ACTIVE = "active"
    DELIBERATING = "deliberating"
    COMMUNICATING = "communicating"
    RESTING = "resting"
    EMERGENCY = "emergency"

class StateMachine:
    def transition(self, current_state: AgentCognitiveState, event: str) -> AgentCognitiveState:
        # Stub logic
        return AgentCognitiveState.ACTIVE