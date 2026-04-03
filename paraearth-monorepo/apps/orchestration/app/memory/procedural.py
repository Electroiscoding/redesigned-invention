import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ProceduralMemoryStore:
    """
    Procedural Memory Store.
    Maintains and retrieves JSON-structured 'Skill Trees' and procedures.
    Unlike Semantic Memory (which is associative facts), Procedural Memory
    is strict 'how-to' knowledge retrieved explicitly based on the agent's current task.
    """
    def __init__(self, db_pool=None):
        self.pool = db_pool
        # Mock database of fundamental skill trees known natively by the system
        # These are usually tied to the agent's initial vocational role or
        # discovered through the `breakthrough` event system over long simulations.
        self._global_skill_registry = {
            "smelt_iron": {
                "name": "how_to_smelt_iron",
                "prerequisites": {"Fe2O3": 5.0, "C": 2.0},
                "minimum_temperature_k": 1400.0,
                "tool_sequence": [
                    {"step": 1, "action": "construct_bloomery", "materials": ["Clay", "Stone"]},
                    {"step": 2, "action": "ignite_fuel", "materials": ["C", "O2"]},
                    {"step": 3, "action": "react_materials", "reagents": {"Fe2O3": 5.0, "C": 2.0}},
                    {"step": 4, "action": "extract_bloom", "result": "Fe"}
                ]
            },
            "build_shelter": {
                "name": "how_to_build_stone_shelter",
                "prerequisites": {"Stone": 50.0, "Clay": 10.0},
                "minimum_temperature_k": 0.0,
                "tool_sequence": [
                    {"step": 1, "action": "lay_foundation", "materials": ["Stone"]},
                    {"step": 2, "action": "mix_mortar", "materials": ["Clay", "H2O"]},
                    {"step": 3, "action": "stack_walls", "materials": ["Stone", "Mortar"]}
                ]
            }
        }

        # Maps agent_id -> set of unlocked skill keys
        self._agent_unlocks: Dict[str, set] = {}

    async def get_for_task(self, agent_id: str, task_query: str) -> List[Dict[str, Any]]:
        """
        Retrieves known procedural JSON steps related to the agent's current goal.
        """
        # In a real app, we query PostgreSQL for records where agent_id matches
        # and semantic similarity to task_query is high, OR exact tag matches.
        unlocked = self._agent_unlocks.get(agent_id, set())

        results = []
        for skill_key in unlocked:
            # Naive keyword matching for demonstration
            if skill_key.split('_')[1] in task_query.lower() or skill_key in task_query.lower():
                results.append(self._global_skill_registry[skill_key])

        return results

    async def update_skill(self, agent_id: str, skill_key: str, custom_procedure: dict = None):
        """
        Records that an agent has learned a new procedural skill, either by
        unlocking a global skill (e.g. from the Community Knowledge Base) or
        by inventing a completely novel custom sequence via trial and error.
        """
        if agent_id not in self._agent_unlocks:
            self._agent_unlocks[agent_id] = set()

        self._agent_unlocks[agent_id].add(skill_key)

        if custom_procedure:
            # The agent invented a new variation
            self._global_skill_registry[f"{skill_key}_custom_{agent_id}"] = custom_procedure

        logger.info(f"Agent {agent_id} learned procedure: {skill_key}")

    async def initialize_vocational_skills(self, agent_id: str, role: str):
        """
        Grants baseline procedures to newly spawned agents based on role.
        """
        role_map = {
            "Chemist": ["smelt_iron"],
            "Architect": ["build_shelter"],
            "Engineer": ["smelt_iron", "build_shelter"]
        }

        skills = role_map.get(role, [])
        for s in skills:
            await self.update_skill(agent_id, s)
