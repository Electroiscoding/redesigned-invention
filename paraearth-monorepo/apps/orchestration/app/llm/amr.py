class AdaptiveModelRouter:
    """
    Adaptive Model Router for ParaEarth.
    This version is strictly configured to use FREE OpenRouter models to minimize
    API costs. Even though the same underlying model is used across different agents,
    ParaEarth treats them as distinct individuals ("bodies/minds") by injecting
    completely different HEXACO personality vectors, distinct episodic memories,
    and distinct vocational system prompts prior to routing.
    """
    def __init__(self, budget_tracker=None):
        self.budget_tracker = budget_tracker

    def select_model(self, preferred_model: str, cognitive_state, task_complexity: float) -> str:
        # Cost optimization using free models
        # Frontier/Deliberating tasks
        if cognitive_state.value == "deliberating" or task_complexity > 0.7:
            return "google/gemini-2.0-flash-exp:free"

        # Resting/Simple reactive tasks
        elif cognitive_state.value == "resting" or task_complexity < 0.2:
            return "nvidia/nemotron-nano-12b-v2-vl:free"

        # Balanced/Active tasks
        else:
            return "meta-llama/llama-3.3-70b-instruct:free"
