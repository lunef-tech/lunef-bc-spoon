"""Balance check tool for querying wallet balances."""

import os
import httpx
from spoon_ai.tools.base import BaseTool


class BalanceCheckTool(BaseTool):
    """Checks the GAS balance of a user's wallet."""

    name: str = "check_balance"
    description: str = (
        "Checks the current GAS balance of the user's Neo X wallet. "
        "Use this when the user asks about their balance or before making a payment to verify funds."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The user's UUID",
            },
        },
        "required": ["user_id"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")

    async def execute(self, user_id: str) -> str:
        """Check user's wallet balance.

        Args:
            user_id: The user's UUID

        Returns:
            JSON string with balance info
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.backend_url}/api/v1/wallets/balance",
                    headers={"X-User-Id": user_id},
                    timeout=15.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return (
                        f'{{"gas_balance": "{data.get("gas_balance", "0")}", '
                        f'"fiat_equivalent": {data.get("fiat_equivalent", 0)}, '
                        f'"fiat_currency": "{data.get("fiat_currency", "USD")}", '
                        f'"address": "{data.get("address", "")}"}}'
                    )
                elif response.status_code == 404:
                    return '{"error": "Wallet not found. Please create a wallet first."}'
                else:
                    return f'{{"error": "Failed to check balance: {response.status_code}"}}'

            except httpx.TimeoutException:
                return '{"error": "Balance check timed out. The blockchain may be slow."}'
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'
