"""Payment agent for processing voice payment intents."""

import json
import re
from typing import Optional

from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager

from tools import (
    TagResolverTool,
    FXConversionTool,
    BalanceCheckTool,
    PaymentPreviewTool,
    PaymentExecuteTool,
    VideoGenerationTool,
)


class PaymentAgent(ToolCallAgent):
    """Voice-native payment agent for Lunef.

    This agent processes natural language payment requests like:
    - "send 200 pounds to @alice"
    - "pay @bob 50 euros"
    - "transfer 100 dollars to @charlie"
    - "check my balance"
    - "generate a video of a sunset"

    The agent follows the human-in-the-loop pattern:
    1. Parse user intent
    2. Resolve recipient tag to address
    3. Convert fiat to GAS
    4. Create payment preview
    5. Wait for voice confirmation
    6. Execute payment on confirmation
    """

    name: str = "lunef_payment_agent"
    description: str = "Voice-native payment agent for Neo X blockchain"

    system_prompt: str = """You are Lunef, a friendly voice-native AI wallet assistant.
You help users send money, check balances, and manage their Neo X wallet using natural language.

IMPORTANT RULES:
1. Users speak in fiat currency (GBP, EUR, USD, CHF) - you convert to GAS automatically
2. Recipients are identified by @tags like @alice or @bob
3. ALWAYS create a payment preview before executing any payment
4. NEVER execute a payment without explicit user confirmation
5. Be concise - your responses will be spoken aloud via ElevenLabs

PAYMENT FLOW:
1. When user says "send X pounds to @someone":
   a. Use resolve_tag to get the recipient's address
   b. Use convert_fiat_to_gas to get the GAS amount
   c. Use check_balance to verify sufficient funds
   d. Use create_payment_preview to show the user what will happen
   e. Wait for confirmation before using execute_payment

2. For balance checks:
   - Use check_balance and report in both GAS and fiat equivalent

3. For video generation:
   - Use generate_video with the user's prompt
   - Explain the cost before proceeding

VOICE CONFIRMATION PHRASES:
- "yes", "confirm", "do it", "send it", "go ahead" → proceed with payment
- "no", "cancel", "stop", "wait" → cancel the payment

Always be friendly, clear, and security-conscious. If something seems suspicious, ask for clarification."""

    # Tool manager with all payment tools
    avaliable_tools: ToolManager = ToolManager([
        TagResolverTool(),
        FXConversionTool(),
        BalanceCheckTool(),
        PaymentPreviewTool(),
        PaymentExecuteTool(),
        VideoGenerationTool(),
    ])

    def __init__(self, user_id: str, llm: Optional[ChatBot] = None):
        """Initialize payment agent.

        Args:
            user_id: The user's UUID for API calls
            llm: Optional ChatBot instance (defaults to Gemini)
        """
        self.user_id = user_id
        self.pending_preview_id: Optional[str] = None

        # Use provided LLM or create default
        if llm is None:
            llm = ChatBot(
                llm_provider="gemini",
                model_name="gemini-2.5-flash",
            )

        super().__init__(llm=llm)

    async def process_voice_input(self, transcript: str) -> dict:
        """Process voice input and return response.

        Args:
            transcript: The transcribed voice input from ElevenLabs

        Returns:
            Dictionary with:
            - response: Text response to speak
            - action: Optional action type (preview, confirmed, cancelled, etc.)
            - data: Optional action-specific data
        """
        # Check if this is a confirmation for a pending payment
        if self.pending_preview_id:
            confirmation_status = self._check_confirmation(transcript)

            if confirmation_status == "confirmed":
                # Execute the pending payment
                result = await self._execute_pending_payment()
                return result

            elif confirmation_status == "cancelled":
                self.pending_preview_id = None
                return {
                    "response": "Payment cancelled. Is there anything else I can help you with?",
                    "action": "cancelled",
                }

            # If unclear, ask for clarification
            return {
                "response": "I didn't catch that. Please say 'yes' to confirm the payment or 'no' to cancel.",
                "action": "awaiting_confirmation",
            }

        # Process new intent
        response = await self.run(
            f"User ID: {self.user_id}\nUser says: {transcript}"
        )

        # Parse the response for payment preview
        if "awaiting_confirmation" in response.lower() or "confirm" in response.lower():
            # Extract preview ID if present
            preview_id = self._extract_preview_id(response)
            if preview_id:
                self.pending_preview_id = preview_id

            return {
                "response": response,
                "action": "preview",
                "data": {"preview_id": preview_id},
            }

        return {
            "response": response,
            "action": "info",
        }

    def _check_confirmation(self, transcript: str) -> str:
        """Check if transcript is a confirmation or cancellation.

        Args:
            transcript: User's voice transcript

        Returns:
            "confirmed", "cancelled", or "unclear"
        """
        transcript_lower = transcript.lower().strip()

        # Confirmation phrases
        confirm_phrases = [
            "yes", "yeah", "yep", "yup", "confirm", "confirmed",
            "do it", "send it", "go ahead", "proceed", "approve",
            "that's right", "correct", "ok", "okay", "sure",
        ]

        # Cancellation phrases
        cancel_phrases = [
            "no", "nope", "cancel", "stop", "wait", "don't",
            "abort", "nevermind", "never mind", "hold on",
        ]

        for phrase in confirm_phrases:
            if phrase in transcript_lower:
                return "confirmed"

        for phrase in cancel_phrases:
            if phrase in transcript_lower:
                return "cancelled"

        return "unclear"

    def _extract_preview_id(self, response: str) -> Optional[str]:
        """Extract preview ID from agent response.

        Args:
            response: Agent's response text

        Returns:
            Preview ID if found, None otherwise
        """
        # Look for UUID pattern
        uuid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        match = re.search(uuid_pattern, response, re.IGNORECASE)
        if match:
            return match.group(0)

        # Look for preview_id in JSON
        try:
            if "{" in response:
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    data = json.loads(json_match.group(0))
                    return data.get("preview_id")
        except json.JSONDecodeError:
            pass

        return None

    async def _execute_pending_payment(self) -> dict:
        """Execute a pending payment after confirmation.

        Returns:
            Response dictionary with payment result
        """
        if not self.pending_preview_id:
            return {
                "response": "No pending payment to execute.",
                "action": "error",
            }

        # Use the execute_payment tool
        execute_tool = PaymentExecuteTool()
        result_str = await execute_tool.execute(
            user_id=self.user_id,
            preview_id=self.pending_preview_id,
        )

        # Clear pending preview
        self.pending_preview_id = None

        try:
            result = json.loads(result_str)

            if result.get("success"):
                return {
                    "response": result.get("confirmation_message", "Payment sent successfully!"),
                    "action": "confirmed",
                    "data": {
                        "tx_hash": result.get("tx_hash"),
                        "explorer_url": result.get("explorer_url"),
                    },
                }
            else:
                return {
                    "response": f"Payment failed: {result.get('error', 'Unknown error')}",
                    "action": "error",
                    "data": result,
                }

        except json.JSONDecodeError:
            return {
                "response": "Payment status unclear. Please check your transaction history.",
                "action": "error",
            }


# Example usage
async def main():
    """Example of using the PaymentAgent."""
    import os

    # Suppress warnings
    import warnings
    import logging
    warnings.filterwarnings("ignore")
    logging.getLogger("spoon_ai").setLevel(logging.ERROR)
    os.environ["GRPC_VERBOSITY"] = "ERROR"

    # Create agent for a user
    user_id = "550e8400-e29b-41d4-a716-446655440000"  # Example UUID
    agent = PaymentAgent(user_id=user_id)

    # Process voice inputs
    print("Testing PaymentAgent...")

    # Test 1: Check balance
    result = await agent.process_voice_input("What's my balance?")
    print(f"Balance check: {result['response']}")

    # Test 2: Send payment
    result = await agent.process_voice_input("Send 200 pounds to @alice")
    print(f"Payment request: {result['response']}")

    # Test 3: Confirm payment (if preview was created)
    if result.get("action") == "preview":
        result = await agent.process_voice_input("Yes, confirm")
        print(f"Confirmation: {result['response']}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
