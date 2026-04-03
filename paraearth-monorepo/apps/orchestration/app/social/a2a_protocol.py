import logging
import json
import re
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class A2AProtocol:
    """
    Agent-to-Agent (A2A) Protocol Adaptor.
    Formats explicit structured messages from agents into the W3C A2A standard,
    and attempts to extract implicit proposals/structures from incoming natural language
    if the sending agent failed to strictly adhere to the JSON schema.
    """
    def format_message(
        self,
        sender_id: str,
        recipient_id: str,
        content: str,
        urgency: str = "NORMAL",
        structured_content: Optional[Dict[str, Any]] = None
    ) -> dict:
        """
        Builds the standard ParaEarth adaptation of the W3C A2A W3C protocol.
        """
        # Attempt to auto-infer proposals from natural language if structured wasn't explicitly provided
        if not structured_content:
            structured_content = self._infer_structured_content(content)

        return {
            "a2a_version": "1.2",
            "sender_id": sender_id,
            "recipient_id": recipient_id,
            "message_type": "PROPOSAL" if structured_content else "CHAT",
            "urgency": urgency,
            "natural_language": content,
            "structured_content": structured_content
        }

    def parse_incoming_message(self, message_payload: dict) -> dict:
        """
        Validates and parses an incoming A2A message before injecting it into
        the Context Window of the receiving agent.
        """
        if message_payload.get("a2a_version") != "1.2":
            logger.warning("Incoming message missing a2a_version 1.2 flag. Attempting to parse anyway.")

        return message_payload

    def _infer_structured_content(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Fallback heuristic inference for extracting structured logic from freeform text.
        (In production, we might run this through a tiny fast LLM pass, but for
        performance we use basic regex pattern matching first).
        """
        trade_pattern = re.compile(r"trade.*?(\d+\.?\d*)\s*(kg|units)?\s*of\s*([a-zA-Z0-9]+).*?for.*?(\d+\.?\d*)\s*(kg|units)?\s*of\s*([a-zA-Z0-9]+)", re.IGNORECASE)

        match = trade_pattern.search(text)
        if match:
            # Group 1: offer qty, Group 3: offer material
            # Group 4: request qty, Group 6: request material
            try:
                offer_qty = float(match.group(1))
                offer_mat = match.group(3).upper()
                req_qty = float(match.group(4))
                req_mat = match.group(6).upper()

                logger.info(f"[A2A Protocol] Inferred trade logic from text: {offer_qty}{offer_mat} for {req_qty}{req_mat}")

                return {
                    "proposal_type": "RESOURCE_TRADE",
                    "offered": { offer_mat: offer_qty },
                    "requested": { req_mat: req_qty }
                }
            except Exception as e:
                logger.debug(f"[A2A Protocol] Failed to parse matched trade numbers: {e}")
                return None

        # More heuristics could be added (e.g. coordinates/locations mapping)
        return None
