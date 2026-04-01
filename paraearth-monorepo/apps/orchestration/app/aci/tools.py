class AgentChemistryInterface:
    def __init__(self, sandbox):
        self.sandbox = sandbox

    async def execute(self, agent, tool_call: dict) -> dict:
        # Execute functions: mine_element, react_materials
        if not self.sandbox.validate_action(agent.agent_id, tool_call):
            return {"status": "error", "message": "Action blocked by sandbox."}
        return {"status": "success", "message": "Action executed."}