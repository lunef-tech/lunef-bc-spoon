"""Payment execute tool for executing confirmed payments."""

import os
import json
import httpx
from spoon_ai.tools.base import BaseTool


class PaymentExecuteTool(BaseTool):
    """Executes a confirmed payment on Neo X."""

    name: str = "execute_payment"
    description: str = (
        "Executes a payment after the user has confirmed it. "
        "Only use this after receiving explicit confirmation from the user. "
        "The payment will be broadcast to the Neo X blockchain."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The sender's user UUID",
            },
            "preview_id": {
                "type": "string",
                "description": "The payment preview ID from create_payment_preview",
            },
        },
        "required": ["user_id", "preview_id"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")

    async def execute(self, user_id: str, preview_id: str) -> str:
        """Execute a confirmed payment.

        Args:
            user_id: The sender's UUID
            preview_id: The payment preview ID

        Returns:
            JSON string with transaction result
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.backend_url}/api/v1/payments/{preview_id}/execute",
                    headers={"X-User-Id": user_id},
                    timeout=60.0,  # Longer timeout for blockchain transactions
                )

                if response.status_code == 200:
                    data = response.json()
                    return json.dumps({
                        "success": True,
                        "tx_hash": data.get("tx_hash"),
                        "explorer_url": data.get("explorer_url"),
                        "amount_gas": data.get("amount_gas"),
                        "to_tag": data.get("to_tag"),
                        "status": data.get("status", "confirmed"),
                        "confirmation_message": (
                            f"Payment sent successfully! {data.get('amount_gas')} GAS "
                            f"has been sent to {data.get('to_tag')}. "
                            f"Transaction: {data.get('tx_hash')[:16]}..."
                        ),
                    })
                elif response.status_code == 404:
                    return '{"error": "Payment preview expired or not found. Please start a new payment."}'
                elif response.status_code == 403:
                    return '{"error": "Insufficient balance or payment not confirmed"}'
                elif response.status_code == 409:
                    return '{"error": "Payment already executed"}'
                else:
                    return f'{{"error": "Payment failed: {response.status_code}"}}'

            except httpx.TimeoutException:
                return json.dumps({
                    "warning": "Transaction may still be processing",
                    "message": "The payment was submitted but confirmation timed out. Please check your transaction history.",
                })
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'
