class A2AProtocol:
    def format_message(self, sender_id: str, recipient_id: str, content: str) -> dict:
        # W3C Agent-to-Agent structured messaging
        return {
            "a2a_version": "1.2",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": "PROPOSAL",
            "natural_language": content
        }