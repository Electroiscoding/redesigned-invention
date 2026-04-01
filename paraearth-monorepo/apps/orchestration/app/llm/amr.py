class AdaptiveModelRouter:
    def __init__(self, budget_tracker=None):
        self.budget_tracker = budget_tracker

    def select_model(self, preferred_model: str, cognitive_state, task_complexity: float) -> str:
        # Cost optimization stub
        if cognitive_state.value == "deliberating" or task_complexity > 0.7:
            return "anthropic/claude-3-5-sonnet"
        elif cognitive_state.value == "resting" or task_complexity < 0.2:
            return "meta-llama/llama-3.1-8b-instruct"
        else:
            return "meta-llama/llama-3.1-70b-instruct"