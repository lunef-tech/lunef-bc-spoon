"""Tag resolver tool for resolving @tags to Neo X addresses."""

import os
import httpx
from spoon_ai.tools.base import BaseTool


class TagResolverTool(BaseTool):
    """Resolves a @luneftag to a Neo X wallet address."""

    name: str = "resolve_tag"
    description: str = (
        "Resolves a Lunef tag (like @alice or @bob) to the recipient's Neo X wallet address. "
        "Use this when the user mentions sending money to someone by their @tag."
    )
    parameters: dict = {
        "type": "object",
        "properties": {
            "tag": {
                "type": "string",
                "description": "The Lunef tag to resolve (e.g., '@alice', 'alice', or '@bob')",
            }
        },
        "required": ["tag"],
    }

    def __init__(self):
        super().__init__()
        self.backend_url = os.getenv("LUNEF_BACKEND_URL", "http://localhost:8080")

    async def execute(self, tag: str) -> str:
        """Resolve a tag to a Neo X address.

        Args:
            tag: The Lunef tag (with or without @ prefix)

        Returns:
            JSON string with address or error
        """
        # Normalize tag - remove @ if present
        clean_tag = tag.lstrip("@").lower().strip()

        if not clean_tag:
            return '{"error": "Empty tag provided"}'

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.backend_url}/api/v1/users/tag/{clean_tag}",
                    timeout=10.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return f'{{"tag": "@{clean_tag}", "address": "{data.get("wallet_address", "")}", "display_name": "{data.get("display_name", clean_tag)}"}}'
                elif response.status_code == 404:
                    return f'{{"error": "Tag @{clean_tag} not found. Please check the spelling."}}'
                else:
                    return f'{{"error": "Failed to resolve tag: {response.status_code}"}}'

            except httpx.TimeoutException:
                return '{"error": "Request timed out. Please try again."}'
            except httpx.RequestError as e:
                return f'{{"error": "Network error: {str(e)}"}}'
