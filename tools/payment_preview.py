"""Payment preview tool for creating payment previews."""

import os
import json
import httpx
from spoon_ai.tools.base import BaseTool


class PaymentPreviewTool(BaseTool):
    """Creates a payment preview for user confirmation."""

    name: str = "create_payment_preview"
    description: str = (
        "Creates a payment preview that shows the user exactly what will be sent. "
        "Use this after resolving the recipient tag and converting the fiat amount to GAS. "
        "The preview includes fee estimates and requires voice confirmation before execution."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The sender's user UUID",
            },
            "to_address": {
                "type": "string",
                "description": "The recipient's Neo X address",
            },
            "to_tag": {
                "type": "string",
                "description": "The recipient's @tag for display purposes",
            },
            "amount_gas": {
                "type": "string",
                "description": "The amount of GAS to send",
            },
            "fiat_amount": {
                "type": "number",
                "description": "The original fiat amount for display",
            },
            "fiat_currency": {
                "type": "string",
                "description": "The fiat currency code (GBP, EUR, USD, CHF)",
            },
        },
        "required": ["user_id", "to_address", "to_tag", "amount_gas", "fiat_amount", "fiat_currency"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")

    async def execute(
        self,
        user_id: str,
        to_address: str,
        to_tag: str,
        amount_gas: str,
        fiat_amount: float,
        fiat_currency: str,
    ) -> str:
        """Create a payment preview.

        Args:
            user_id: The sender's UUID
            to_address: Recipient's Neo X address
            to_tag: Recipient's @tag
            amount_gas: Amount of GAS to send
            fiat_amount: Original fiat amount
            fiat_currency: Original fiat currency

        Returns:
            JSON string with preview details or error
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.backend_url}/api/v1/payments/preview",
                    headers={"X-User-Id": user_id},
                    json={
                        "to_address": to_address,
                        "to_tag": to_tag,
                        "amount_gas": amount_gas,
                        "fiat_amount": fiat_amount,
                        "fiat_currency": fiat_currency.upper(),
                    },
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return json.dumps({
                        "preview_id": data.get("preview_id"),
                        "from_address": data.get("from_address"),
                        "to_address": data.get("to_address"),
                        "to_tag": to_tag,
                        "amount_gas": data.get("amount_gas"),
                        "fiat_amount": fiat_amount,
                        "fiat_currency": fiat_currency.upper(),
                        "estimated_fee": data.get("estimated_fee", "0.001"),
                        "total_gas": data.get("total_gas"),
                        "status": "awaiting_confirmation",
                        "confirmation_message": (
                            f"You're about to send {fiat_amount} {fiat_currency.upper()} "
                            f"(approximately {data.get('amount_gas')} GAS) to {to_tag}. "
                            f"Please confirm by saying 'yes' or 'confirm'."
                        ),
                    })
                elif response.status_code == 400:
                    error_data = response.json()
                    return json.dumps({"error": error_data.get("message", "Invalid payment request")})
                elif response.status_code == 403:
                    return '{"error": "Insufficient balance for this payment"}'
                else:
                    return f'{{"error": "Failed to create preview: {response.status_code}"}}'

            except httpx.TimeoutException:
                return '{"error": "Payment preview timed out"}'
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'
