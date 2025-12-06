# Suppress warnings before any imports
import warnings
import logging
import os

warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*non-text parts.*")
logging.getLogger("spoon_ai").setLevel(logging.ERROR)
logging.getLogger("google").setLevel(logging.ERROR)
os.environ["GRPC_VERBOSITY"] = "ERROR"

import asyncio
from spoon_ai.agents.toolcall import ToolCallAgent
from spoon_ai.chat import ChatBot
from spoon_ai.tools import ToolManager
from spoon_ai.tools.base import BaseTool


# Define a custom tool
class GreetingTool(BaseTool):
    name: str = "greeting"
    description: str = "Generate personalized greetings"
    parameters: dict = {
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Person's name"}},
        "required": ["name"],
    }

    async def execute(self, name: str) -> str:
        return f"Hello {name}! Welcome to SpoonOS! 🚀"


# Create your agent
class MyFirstAgent(ToolCallAgent):
    name: str = "my_first_agent"
    description: str = "A friendly assistant with greeting capabilities"

    system_prompt: str = """
    You are a helpful AI assistant built with SpoonOS framework.
    You can greet users and help with various tasks.
    """

    avaliable_tools: ToolManager = ToolManager([GreetingTool()])


async def main():
    # Initialize agent with LLM
    agent = MyFirstAgent(
        llm=ChatBot(
            llm_provider="gemini",
            model_name="gemini-2.5-flash",
        )
    )

    # Run the agent
    response = await agent.run("Please greet me, my name is Alice")
    return response


if __name__ == "__main__":
    result = asyncio.run(main())
