"""FX conversion tool for converting fiat to GAS."""

import os
import httpx
from spoon_ai.tools.base import BaseTool


class FXConversionTool(BaseTool):
    """Converts fiat currency amounts to Neo X GAS."""

    name: str = "convert_fiat_to_gas"
    description: str = (
        "Converts a fiat currency amount (GBP, EUR, USD, CHF) to Neo X GAS. "
        "Use this when the user specifies an amount in fiat like '200 pounds' or '50 euros'."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "amount": {
                "type": "number",
                "description": "The amount in fiat currency",
            },
            "currency": {
                "type": "string",
                "enum": ["GBP", "EUR", "USD", "CHF"],
                "description": "The fiat currency code (GBP, EUR, USD, or CHF)",
            },
        },
        "required": ["amount", "currency"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")

    async def execute(self, amount: float, currency: str) -> str:
        """Convert fiat amount to GAS.

        Args:
            amount: The fiat amount
            currency: The currency code (GBP, EUR, USD, CHF)

        Returns:
            JSON string with conversion result
        """
        currency = currency.upper()
        if currency not in ["GBP", "EUR", "USD", "CHF"]:
            return f'{{"error": "Unsupported currency: {currency}. Use GBP, EUR, USD, or CHF."}}'

        if amount <= 0:
            return '{"error": "Amount must be positive"}'

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.backend_url}/api/v1/rates/fiat-to-gas",
                    params={"fiat": currency, "amount": amount},
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return (
                        f'{{"fiat_amount": {data.get("fiat_amount", amount)}, '
                        f'"fiat_currency": "{data.get("fiat_currency", currency)}", '
                        f'"gas_amount": "{data.get("gas_amount", "0")}", '
                        f'"fx_rate": {data.get("fx_rate", 0)}, '
                        f'"gas_price_usd": {data.get("gas_price_usd", 0)}}}'
                    )
                else:
                    return f'{{"error": "Conversion failed: {response.status_code}"}}'

            except httpx.TimeoutException:
                return '{"error": "Conversion service timed out"}'
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'
