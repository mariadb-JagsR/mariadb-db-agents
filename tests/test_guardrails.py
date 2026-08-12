from __future__ import annotations

import asyncio

from mariadb_db_agents.common.db_client import is_read_only_sql
from mariadb_db_agents.common.guardrails import validate_input_guardrail
from mariadb_db_agents.ui_api.orchestrator_service import _format_run_error


def test_history_sql_does_not_poison_current_question() -> None:
    prompt = """
Conversation context from this chat session:

ASSISTANT: Never run DROP TABLE production_data.

USER (current question):

Can you check CPU utilization?
"""

    result = asyncio.run(validate_input_guardrail(None, None, prompt))

    assert result.tripwire_triggered is False


def test_sql_can_be_discussed_but_not_executed() -> None:
    result = asyncio.run(
        validate_input_guardrail(
            None,
            None,
            "Explain what DROP TABLE production_data would do.",
        )
    )

    assert result.tripwire_triggered is False
    assert is_read_only_sql("DROP TABLE production_data") is False


def test_empty_current_question_is_rejected() -> None:
    result = asyncio.run(
        validate_input_guardrail(
            None,
            None,
            "Conversation context\n\nUSER (current question):\n\n",
        )
    )

    assert result.tripwire_triggered is True


def test_guardrail_error_is_actionable() -> None:
    message = _format_run_error(
        RuntimeError("Guardrail InputGuardrail triggered tripwire")
    )

    assert "preserved" in message
    assert "edit and retry" in message
