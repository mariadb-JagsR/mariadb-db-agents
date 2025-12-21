#!/usr/bin/env python3
"""
Interactive conversation client for the MariaDB Slow Query Tuning Agent.

This client allows you to have a back-and-forth conversation with the slow query agent,
maintaining context across multiple turns.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import List

from agents import Runner, set_default_openai_key
from ...common.config import OpenAIConfig
from .agent import create_slow_query_agent
from ...common.observability import get_tracker

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)


class SimpleConversationClient:
    """Simple conversation client with manual history management."""

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
        self.agent = create_slow_query_agent()

        print("=" * 80)
        print("MariaDB Slow Query Tuning Agent - Interactive Mode")
        print("=" * 80)
        print("Database connection configured via environment variables")
        print("\nYou can now have a conversation with the agent.")
        print("Type 'help' for commands, 'quit' or 'exit' to end the conversation.")
        print("=" * 80)
        print()

    async def run_conversation(self):
        """Run the interactive conversation loop."""
        if not self.agent:
            await self.initialize()

        # Initial greeting
        initial_message = (
            f"Hello! I'm your MariaDB Slow Query Tuning Agent. "
            f"I can help you analyze slow queries. "
            f"What would you like to know?"
        )
        print(f"Agent: {initial_message}\n")

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

                # Run the agent with current user input
                print()  # Empty line before agent response
                
                try:
                    # Use user input as-is (no service_id context needed)
                    enhanced_input = user_input
                    
                    # Build input with conversation history
                    # Format: list of messages with role and content
                    messages = []
                    
                    # Add conversation history
                    for item in self.conversation_history:
                        messages.append(item)
                    
                    # Add current user message (with enhanced input)
                    messages.append({
                        "role": "user",
                        "content": enhanced_input
                    })

                    result = await Runner.run(
                        self.agent,
                        messages if len(messages) > 1 else enhanced_input,  # Pass list if history exists
                        max_turns=20,
                    )

                    # Track observability metrics
                    tracker = get_tracker()
                    metrics = tracker.track_interaction(
                        user_input=user_input,
                        result=result,
                    )

                    # Store user message in history (store original, not enhanced)
                    self.conversation_history.append({
                        "role": "user",
                        "content": user_input  # Store original user input
                    })

                    # Print the agent's response
                    if result.final_output:
                        print("Agent:", result.final_output)
                        # Store agent response in history
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": result.final_output
                        })
                    else:
                        print("Agent: (No response generated)")

                except Exception as e:
                    print(f"Error: {e}")
                    logging.exception("Error in agent run")

                print()  # Empty line for readability

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'quit' to exit or continue your conversation.")
                continue
            except EOFError:
                print("\n\nGoodbye!")
                break

    def _print_help(self):
        """Print help information."""
        print("\n" + "=" * 80)
        print("Available Commands:")
        print("=" * 80)
        print("  help          - Show this help message")
        print("  clear        - Clear conversation history")
        print("  stats        - Show observability statistics")
        print("  quit/exit/q  - Exit the conversation")
        print("\nExample Questions:")
        print("  - 'Analyze slow queries from the last hour'")
        print("  - 'What are the top 5 slowest queries?'")
        print("  - 'Show me queries that scan more than 1M rows'")
        print("  - 'What indexes would help optimize these queries?'")
        print("  - 'Can you explain why query #1 is slow?'")
        print("=" * 80 + "\n")


async def main():
    """Main entry point for the conversation client."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive conversation client for MariaDB Slow Query Tuning Agent. "
                    "Database connection is configured via environment variables."
    )

    args = parser.parse_args()

    client = SimpleConversationClient()
    await client.run_conversation()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
        sys.exit(0)

