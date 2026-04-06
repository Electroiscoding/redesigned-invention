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
        """
        Determines the optimal model for an agent inference based on cognitive load.
        """
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

    def handle_api_failure(self, failed_model: str, error_code: int) -> str:
        """
        Fallback logic handler. If an OpenRouter request times out or returns a rate limit
        error (e.g. HTTP 429), this function immediately reroutes the agent to a smaller,
        more permissive free model to maintain the simulation's tick continuity.
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.warning(f"Model {failed_model} failed with code {error_code}. Falling back.")

        # If the failure is a strict rate limit or overload, drop down the ladder
        if error_code in [429, 502, 503, 504]:
            if "gemini" in failed_model:
                return "meta-llama/llama-3.3-70b-instruct:free"
            elif "llama" in failed_model:
                return "nvidia/nemotron-nano-12b-v2-vl:free"

        # Absolute basement fallback to prevent crashes
        return "nvidia/nemotron-nano-12b-v2-vl:free"
