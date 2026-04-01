class ContextWindow:
    def __init__(self, system_prompt, messages, tools):
        self.system_prompt = system_prompt
        self.messages = messages
        self.available_tools = tools

    def to_messages(self):
        return [{"role": "system", "content": self.system_prompt}] + self.messages

class ContextWindowAssembler:
    async def assemble(self, agent, perception, incoming_messages) -> ContextWindow:
        # Context Window compression engine
        return ContextWindow(agent.system_prompt, [], [])