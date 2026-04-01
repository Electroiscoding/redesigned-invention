import asyncio
import json

class Chunk:
    def __init__(self, ctype, content):
        self.type = ctype
        if ctype == "tool_call":
            self.tool_call = content
        elif ctype == "message":
            self.message = content
        elif ctype == "reasoning":
            self.text = content

class OpenRouterClient:
    def __init__(self, api_key: str):
        self.api_key = api_key

    async def stream_completion(self, model: str, messages: list, tools: list, max_tokens: int):
        # SSE Streaming & API handler stub
        yield Chunk("reasoning", "Thinking...")
        yield Chunk("tool_call", {"name": "observe_environment", "arguments": {}})
        yield Chunk("message", "I am looking around.")