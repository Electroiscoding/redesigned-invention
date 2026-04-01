import json

class ToolCallParser:
    def parse(self, tool_call_json: str) -> dict:
        # JSON tool-call validation
        try:
            return json.loads(tool_call_json)
        except json.JSONDecodeError:
            return {}