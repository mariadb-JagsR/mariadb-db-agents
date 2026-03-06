from __future__ import annotations

import re


def _strip_markdown(text: str) -> str:
    clean = text.strip()
    clean = re.sub(r"^\s*#+\s*", "", clean)
    clean = re.sub(r"[*`]+", "", clean)
    clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip(" :-")


def extract_next_steps(markdown: str) -> list[str]:
    """
    Best-effort extraction of action items from free-form markdown/text.
    """
    lines = markdown.splitlines()
    capture = False
    results: list[str] = []

    for raw in lines:
        line = raw.strip()
        normalized = _strip_markdown(line)
        lower = normalized.lower()
        if (
            lower.startswith("next steps")
            or lower.startswith("recommended actions")
            or lower.startswith("recommendations")
            or lower.startswith("action items")
        ):
            capture = True
            continue
        if capture and line.startswith("#"):
            break
        if capture:
            match = re.match(r"^[-*]\s+(.+)$", line) or re.match(r"^\d+\.\s+(.+)$", line)
            if match:
                item = _strip_markdown(match.group(1))
                if item:
                    results.append(item)
            elif line and not line.startswith("```"):
                # Single-line continuation / fallback.
                if results:
                    results[-1] = f"{results[-1]} {_strip_markdown(line)}".strip()

    return results[:10]

