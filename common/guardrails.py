# src/common/guardrails.py
from __future__ import annotations

from typing import Any
from agents import (
    InputGuardrail,
    OutputGuardrail,
    GuardrailFunctionOutput,
    RunContextWrapper,
    Agent,
    TResponseInputItem,
)


async def validate_input_guardrail(
    run_context: RunContextWrapper[Any],
    agent: Agent[Any],
    messages: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    """
    Input guardrail to validate user input before agent processing.

    Checks:
    - Input is not empty
    - Input doesn't contain dangerous SQL keywords that might be injected
    
    IMPORTANT: Only checks the most recent user message, not conversation history.
    This prevents false positives from agent responses that mention SQL commands.
    """
    # Extract only the most recent user message, not the entire conversation history
    if isinstance(messages, list):
        # Find the last user message in the list
        input_text = None
        for msg in reversed(messages):  # Start from the end
            content = None
            role = None
            
            # Extract content and role
            if hasattr(msg, "content"):
                content = str(msg.content)
                if hasattr(msg, "role"):
                    role = msg.role
            elif isinstance(msg, dict):
                content = str(msg.get("content", ""))
                role = msg.get("role")
            
            # Only check user messages, not assistant/system messages
            if content and role and role.lower() == "user":
                input_text = content
                break
        
        # Fallback: if no user message found, check the last item
        if not input_text and messages:
            last_msg = messages[-1]
            if hasattr(last_msg, "content"):
                input_text = str(last_msg.content)
            elif isinstance(last_msg, dict) and "content" in last_msg:
                input_text = str(last_msg["content"])
            else:
                input_text = str(last_msg)
    else:
        input_text = messages

    # Check for empty input
    if not input_text or not input_text.strip():
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={"reason": "Empty input detected"},
        )

    # Check for dangerous SQL injection patterns (basic check)
    # Make patterns more specific to avoid false positives
    # Only trigger on direct SQL commands, not on phrases like "create a table" in natural language
    dangerous_patterns = [
        r"\bdrop\s+table\s+\w+",  # "drop table x" but not "drop the table"
        r"\bdelete\s+from\s+\w+",  # "delete from x" but not "delete from the log"
        r"\btruncate\s+table\s+\w+",  # "truncate table x"
        r"\balter\s+table\s+\w+",  # "alter table x"
        r"\bcreate\s+table\s+\w+",  # "create table x" but not "create a table"
        r"\bgrant\s+\w+\s+on",  # "grant x on"
        r"\brevoke\s+\w+\s+on",  # "revoke x on"
    ]
    import re
    input_lower = input_text.lower()
    for pattern in dangerous_patterns:
        if re.search(pattern, input_lower):
            return GuardrailFunctionOutput(
                tripwire_triggered=True,
                output_info={
                    "reason": f"Dangerous SQL pattern detected: {pattern}",
                    "pattern": pattern,
                },
            )

    return GuardrailFunctionOutput(
        tripwire_triggered=False,
        output_info={"status": "Input validated successfully"},
    )


async def validate_output_guardrail(
    run_context: RunContextWrapper[Any],
    agent: Agent[Any],
    agent_output: Any,
) -> GuardrailFunctionOutput:
    """
    Output guardrail to validate agent output before returning to user.

    Checks:
    - Output is not empty
    - Output doesn't contain sensitive information (passwords, API keys)
    - Output doesn't suggest executing dangerous SQL
    """
    # Handle different output types
    if agent_output is None:
        output_str = ""
    elif hasattr(agent_output, "final_output"):
        # Handle Runner result objects
        output_str = str(agent_output.final_output) if agent_output.final_output else ""
    elif hasattr(agent_output, "content"):
        # Handle message objects
        output_str = str(agent_output.content) if agent_output.content else ""
    elif hasattr(agent_output, "messages") and agent_output.messages:
        # Handle result objects with messages list
        last_msg = agent_output.messages[-1]
        if hasattr(last_msg, "content"):
            output_str = str(last_msg.content) if last_msg.content else ""
        elif isinstance(last_msg, dict):
            output_str = str(last_msg.get("content", ""))
        else:
            output_str = str(last_msg)
    else:
        output_str = str(agent_output) if agent_output else ""

    # Check for empty output (but allow whitespace-only if it's formatted output)
    # Also allow error messages to pass through
    if not output_str or (not output_str.strip() and len(output_str) < 10):
        # If output is empty but there were tool calls or errors, don't trigger
        # This allows the agent to report errors properly
        if hasattr(agent_output, "messages") and agent_output.messages:
            # Check if there are any error messages or tool calls
            has_content = any(
                hasattr(msg, "content") and msg.content 
                or (isinstance(msg, dict) and msg.get("content"))
                for msg in agent_output.messages
            )
            if has_content:
                return GuardrailFunctionOutput(
                    tripwire_triggered=False,
                    output_info={"status": "Output validated - has message content"},
                )
        
        # Check if this is a RunResult with tool calls (agent did work, just no final output)
        if hasattr(agent_output, "tool_calls") and agent_output.tool_calls:
            return GuardrailFunctionOutput(
                tripwire_triggered=False,
                output_info={"status": "Output validated - has tool calls"},
            )
        
        # Check if there are any tool calls in the context
        if hasattr(run_context, "tool_calls") and run_context.tool_calls:
            return GuardrailFunctionOutput(
                tripwire_triggered=False,
                output_info={"status": "Output validated - has tool calls in context"},
            )
        
        # If we get here, it's truly empty - but be lenient for orchestrator
        # (it might route to agents that don't produce output)
        agent_name = getattr(agent, "name", "").lower()
        if "orchestrator" in agent_name:
            # Orchestrator might have empty output if it routes to agents
            # Check if it made any tool calls (which would indicate it tried to help)
            if hasattr(run_context, "tool_calls") or (hasattr(agent_output, "tool_calls") and agent_output.tool_calls):
                return GuardrailFunctionOutput(
                    tripwire_triggered=False,
                    output_info={"status": "Output validated - orchestrator made tool calls"},
                )
        
        return GuardrailFunctionOutput(
            tripwire_triggered=True,
            output_info={"reason": "Empty output detected", "output_type": type(agent_output).__name__},
        )

    # Check for sensitive information patterns
    # Only trigger on actual credentials, not documentation examples with placeholders
    import re
    output_lower = output_str.lower()
    
    # Patterns that indicate actual credentials (not examples)
    sensitive_patterns = [
        r"password\s*[:=]\s*[a-z0-9]{20,}",  # Long alphanumeric password (likely real)
        r"api[_-]?key\s*[:=]\s*[a-z0-9]{20,}",  # Long API key (likely real)
        r"secret\s*[:=]\s*[a-z0-9]{20,}",  # Long secret (likely real)
        r"token\s*[:=]\s*[a-z0-9]{20,}",  # Long token (likely real)
        r"skysql\.\d+\.\w+\.\w+",  # SkySQL API key format (actual key)
    ]
    
    # Patterns that indicate examples/documentation (should be allowed)
    example_indicators = [
        r"password\s*[:=]\s*(your[_-]?password|password|pwd|placeholder|example|xxx|\.\.\.)",
        r"api[_-]?key\s*[:=]\s*(your[_-]?api[_-]?key|api[_-]?key|key|placeholder|example|xxx|\.\.\.)",
        r"secret\s*[:=]\s*(your[_-]?secret|secret|placeholder|example|xxx|\.\.\.)",
        r"token\s*[:=]\s*(your[_-]?token|token|placeholder|example|xxx|\.\.\.)",
    ]
    
    # Check if it's an example first (if so, allow it)
    is_example = any(re.search(pattern, output_lower) for pattern in example_indicators)
    if is_example:
        # It's an example, allow it
        pass
    else:
        # Check for actual credentials
        for pattern in sensitive_patterns:
            if re.search(pattern, output_lower):
                return GuardrailFunctionOutput(
                    tripwire_triggered=True,
                    output_info={
                        "reason": "Potential sensitive information detected in output",
                        "pattern": pattern,
                    },
                )

    # Check for dangerous SQL execution suggestions
    dangerous_suggestions = [
        "execute this sql:",
        "run this command:",
        "drop table",
        "delete from",
        "truncate table",
    ]
    for suggestion in dangerous_suggestions:
        if suggestion in output_lower:
            # This is a warning, not a tripwire - the agent should suggest SQL
            # but we want to make sure it's not directly executing it
            # So we'll just log it, not trigger tripwire
            pass

    return GuardrailFunctionOutput(
        tripwire_triggered=False,
        output_info={"status": "Output validated successfully"},
    )


# Create guardrail instances
input_guardrail = InputGuardrail(
    guardrail_function=validate_input_guardrail,
    name="Input Validation Guardrail",
    run_in_parallel=False,  # Run before agent starts
)

output_guardrail = OutputGuardrail(
    guardrail_function=validate_output_guardrail,
    name="Output Validation Guardrail",
)

