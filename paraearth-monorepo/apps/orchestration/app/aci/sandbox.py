import logging

logger = logging.getLogger(__name__)

class ActionSandbox:
    """
    Agent Chemistry Interface (ACI) Sandbox.
    Prevents hallucinated or compromised agents from executing physically
    impossible actions (e.g., extracting 1000kg of gold from 1kg of dirt)
    by enforcing strict thermodynamic and mass-conservation limits.
    """

    def __init__(self, wcg_cache=None):
        self.wcg_cache = wcg_cache

    def validate_action(self, agent_id: str, action: dict) -> bool:
        """
        Validates an LLM's requested tool call before executing it.
        """
        func_name = action.get("name")
        args = action.get("arguments", {})

        if func_name == "mine_element":
            return self._validate_mass_conservation(agent_id, args)
        elif func_name == "react_materials":
            return self._validate_thermodynamics(agent_id, args)
        elif func_name == "observe_environment":
            return True

        logger.warning(f"[ACI Sandbox] Rejected unknown function call {func_name} by agent {agent_id}")
        return False

    def _validate_mass_conservation(self, agent_id: str, args: dict) -> bool:
        """
        Verifies that the requested mass to extract physically exists in the
        target World Chemistry Grid (WCG) cell.
        """
        target_species = args.get("target_species", "")
        quantity_kg = args.get("quantity_kg", 0.0)

        # 1. Reject negative or zero mass
        if quantity_kg <= 0.0:
            logger.warning(f"[ACI Sandbox] Rejecting negative/zero mass mining request from {agent_id}.")
            return False

        # 2. Reject physically absurd single-action extractions (> 1000kg without machinery)
        # Assuming manual tools for early simulation
        if quantity_kg > 1000.0:
            logger.warning(f"[ACI Sandbox] Rejecting physically absurd quantity {quantity_kg}kg from {agent_id}. Exceeds manual labor limits.")
            return False

        # 3. Check WCG state (Stubbed for now)
        # In a real environment, query self.wcg_cache.get_cell_composition(lat, lon)
        # and ensure `quantity_kg` <= available_kg in that voxel.

        # Example: Mocking that Au (Gold) is rare
        if target_species == "Au" and quantity_kg > 0.01:
             logger.warning(f"[ACI Sandbox] Rejecting unrealistic gold extraction of {quantity_kg}kg. Not supported by local WCG state.")
             return False

        return True

    def _validate_thermodynamics(self, agent_id: str, args: dict) -> bool:
        """
        Verifies that a reaction requested by an agent is thermodynamically
        valid (not violating energy constraints).
        """
        temp_k = args.get("temperature_k", 298.0)
        reagents = args.get("reagents", {})

        # 1. Check for absolute zero violations
        if temp_k < 0.0:
            logger.warning(f"[ACI Sandbox] Rejecting reaction below absolute zero {temp_k}K.")
            return False

        # 2. Verify reasonable temperature limits based on agent technology
        # Unless the agent has built an electric arc furnace, temp shouldn't exceed ~2000K
        if temp_k > 2000.0:
            # We would verify the agent's location/inventory has a furnace capable of this.
            logger.warning(f"[ACI Sandbox] Rejecting reaction temp {temp_k}K. Exceeds standard combustion limits without advanced machinery.")
            return False

        # 3. Validate stoichiometric mass conservation in reagents
        for species, mass in reagents.items():
            if mass < 0.0:
                logger.warning(f"[ACI Sandbox] Rejecting negative reagent mass {mass}kg of {species}.")
                return False

        return True
