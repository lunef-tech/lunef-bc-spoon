"""Video generation tool with x402 payment integration."""

import os
import json
import httpx
from spoon_ai.tools.base import BaseTool


class VideoGenerationTool(BaseTool):
    """Generates AI videos with x402 machine-to-machine payment."""

    name: str = "generate_video"
    description: str = (
        "Generates an AI video based on a text prompt. "
        "This uses x402 protocol for machine-to-machine payment (USDC on Base Sepolia). "
        "The user will be charged in GAS, and the backend handles the x402 payment automatically."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "user_id": {
                "type": "string",
                "description": "The user's UUID for billing",
            },
            "prompt": {
                "type": "string",
                "description": "The text prompt describing the video to generate",
            },
            "duration_seconds": {
                "type": "integer",
                "description": "Video duration in seconds (5-30)",
                "minimum": 5,
                "maximum": 30,
            },
            "style": {
                "type": "string",
                "enum": ["cinematic", "anime", "realistic", "artistic", "cartoon"],
                "description": "The visual style for the video",
            },
        },
        "required": ["user_id", "prompt"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")
        # x402 facilitator for machine-to-machine payments
        self.x402_facilitator = os.getenv(
            "X402_FACILITATOR_URL", "https://x402.org/facilitator"
        )
        # Video generation API (could be Runway, Pika, etc.)
        self.video_api_url = os.getenv(
            "VIDEO_API_URL", "https://api.example.com/video"
        )
        # Cost per second of video in USDC (for x402 payment)
        self.cost_per_second_usdc = float(os.getenv("VIDEO_COST_PER_SECOND", "0.10"))

    async def execute(
        self,
        user_id: str,
        prompt: str,
        duration_seconds: int = 10,
        style: str = "cinematic",
    ) -> str:
        """Generate an AI video.

        This tool:
        1. Checks user's GAS balance
        2. Calculates cost in GAS equivalent
        3. Creates a content purchase record
        4. Initiates x402 payment to video API
        5. Returns video URL on success

        Args:
            user_id: User's UUID
            prompt: Video description
            duration_seconds: Video length (5-30 seconds)
            style: Visual style

        Returns:
            JSON string with video URL or error
        """
        # Validate duration
        duration_seconds = max(5, min(30, duration_seconds))

        # Calculate total cost in USDC
        total_cost_usdc = self.cost_per_second_usdc * duration_seconds

        async with httpx.AsyncClient() as client:
            try:
                # Step 1: Request video generation with x402 payment
                # The backend handles the x402 payment negotiation
                response = await client.post(
                    f"{self.backend_url}/api/v1/content/video/generate",
                    headers={"X-User-Id": user_id},
                    json={
                        "prompt": prompt,
                        "duration_seconds": duration_seconds,
                        "style": style,
                        "estimated_cost_usdc": total_cost_usdc,
                    },
                    timeout=120.0,  # Video generation can take time
                )

                if response.status_code == 200:
                    data = response.json()
                    return json.dumps({
                        "success": True,
                        "video_url": data.get("video_url"),
                        "thumbnail_url": data.get("thumbnail_url"),
                        "duration_seconds": duration_seconds,
                        "style": style,
                        "cost_gas": data.get("cost_gas"),
                        "cost_usdc": total_cost_usdc,
                        "purchase_id": data.get("purchase_id"),
                        "status": "ready",
                        "message": (
                            f"Video generated successfully! "
                            f"Duration: {duration_seconds}s, Style: {style}. "
                            f"Cost: {data.get('cost_gas', '?')} GAS."
                        ),
                    })
                elif response.status_code == 402:
                    # x402 Payment Required - should not normally happen as backend handles it
                    return json.dumps({
                        "error": "Payment required",
                        "cost_usdc": total_cost_usdc,
                        "message": "Video generation requires payment. Please ensure you have sufficient balance.",
                    })
                elif response.status_code == 403:
                    return '{"error": "Insufficient GAS balance for video generation"}'
                elif response.status_code == 429:
                    return '{"error": "Rate limited. Please try again in a few minutes."}'
                else:
                    return f'{{"error": "Video generation failed: {response.status_code}"}}'

            except httpx.TimeoutException:
                return json.dumps({
                    "status": "processing",
                    "message": (
                        "Video generation is taking longer than expected. "
                        "It will be ready soon - check your content library."
                    ),
                })
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'

    async def _initiate_x402_payment(
        self,
        client: httpx.AsyncClient,
        amount_usdc: float,
        recipient: str,
    ) -> dict:
        """Initiate x402 payment flow.

        This is called by the backend, not directly by this tool.
        Included here for documentation purposes.

        The x402 flow:
        1. Client sends request to API
        2. API returns 402 with payment details in header
        3. Client creates payment authorization
        4. Client retries request with payment proof
        5. API verifies payment and processes request

        Args:
            client: HTTP client
            amount_usdc: Amount in USDC
            recipient: Recipient address

        Returns:
            Payment result dictionary
        """
        # This would be implemented in the backend
        # The x402 protocol handles EIP-3009 authorization
        pass
