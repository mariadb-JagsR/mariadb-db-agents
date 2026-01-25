#!/usr/bin/env python3
"""
Interactive conversation client for the MariaDB DBA Orchestrator Agent.

This client allows you to have a back-and-forth conversation with the orchestrator,
maintaining context across multiple turns.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import List, Optional

from agents import Runner, set_default_openai_key
from ..common.config import OpenAIConfig
from .agent import create_orchestrator_agent
from ..common.observability import get_tracker

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


class OrchestratorConversationClient:
    """Conversation client for the orchestrator with manual history management."""

    def __init__(self):
        """Initialize the conversation client.
        
        Database connection is configured via environment variables.
        """
        self.agent = None
        self.conversation_history: List[dict] = []

    async def initialize(self):
        """Initialize the agent."""
        # Set OpenAI API key
        cfg = OpenAIConfig.from_env()
        set_default_openai_key(cfg.api_key)

        # Create the agent
        self.agent = create_orchestrator_agent()

        print("=" * 80)
        print("MariaDB DBA Orchestrator - Interactive Mode")
        print("=" * 80)
        print("Database connection configured via environment variables")
        print("\nI can help you with database management tasks:")
        print("  - Analyze slow queries (historical performance)")
        print("  - Analyze running queries (current state)")
        print("  - Health checks and incident triage")
        print("  - And more!")
        print("\nType 'help' for commands, 'quit' or 'exit' to end the conversation.")
        print("=" * 80)
        print()

    async def run_conversation(self, initial_query: Optional[str] = None):
        """Run the interactive conversation loop.

        Args:
            initial_query: Optional initial user message to process before entering the
                interactive loop.
        """
        if not self.agent:
            await self.initialize()

        # Initial greeting
        initial_message = (
            "Hello! I'm your MariaDB DBA Orchestrator. "
            "I can help you manage and analyze your database. "
            "What would you like to know?"
        )
        print(f"Orchestrator: {initial_message}\n")

        if initial_query is not None:
            user_input = initial_query.strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye! Ending conversation.")
                return
            if user_input:
                print(f"You: {user_input}\n")
                await self._run_agent(user_input)

        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! Ending conversation.")
                    break

                if user_input.lower() == 'help':
                    self._print_help()
                    continue

                if user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    print("Conversation history cleared.\n")
                    continue

                if user_input.lower() == 'stats':
                    tracker = get_tracker()
                    tracker.print_summary()
                    continue

                await self._run_agent(user_input)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except EOFError:
                print("\n\nGoodbye!")
                break

    def _print_help(self):
        """Print help information."""
        print("\n" + "=" * 80)
        print("Available Commands:")
        print("=" * 80)
        print("  help              - Show this help message")
        print("  clear             - Clear conversation history")
        print("  stats             - Show observability statistics (token usage, round trips)")
        print("  quit / exit / q   - End the conversation")
        print("\nYou can ask me questions like:")
        print("  - 'Is my database healthy?'")
        print("  - 'Analyze slow queries from the last hour'")
        print("  - 'What queries are running right now?'")
        print("  - 'Why is my database slow?'")
        print("  - 'Check everything'")
        print("=" * 80 + "\n")


    async def _run_agent(self, user_input: str) -> None:
        """Run the agent with current user input and update history."""
        print()  # Empty line before agent response

        try:
            # Build input with conversation history
            # Format: list of messages with role and content
            messages = []

            # Add conversation history
            for item in self.conversation_history:
                messages.append(item)

            # Add current user message
            messages.append({
                "role": "user",
                "content": user_input
            })

            result = await Runner.run(
                self.agent,
                messages if len(messages) > 1 else user_input,  # Pass list if history exists
                max_turns=30,
            )

            # Track observability metrics (mark as orchestrator to aggregate sub-agent metrics)
            tracker = get_tracker()
            tracker.track_interaction(
                user_input=user_input,
                result=result,
                is_orchestrator=True,
            )

            # Store user message in history
            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            # Print the agent's response
            if result.final_output:
                print("Orchestrator:", result.final_output)
                # Store agent response in history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": result.final_output
                })
            else:
                print("Orchestrator: (No response generated)")

            print()  # Empty line after response

        except Exception as e:
            print(f"Error: {e}")
            logging.error(f"Error in conversation: {e}", exc_info=True)


async def main(initial_query: Optional[str] = None) -> int:
    """Main entry point for the conversation client.

    Args:
        initial_query: Optional initial user query to send as the first conversation
            message before entering interactive loop.
    """
    client = OrchestratorConversationClient()
    await client.run_conversation(initial_query)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

