"""Shared helpers for schema-driven LLM JSON extraction + repair.

Scoring agents follow the same pattern:
1) Call LLM with an analysis prompt that includes an output contract (JSON schema)
2) Extract JSON from the LLM response
3) Validate + auto-fix locally
4) If still invalid, call LLM with a repair prompt template that includes:
   - {{INVALID_JSON_OUTPUT}}
   - {{VALIDATION_ERRORS}}
   - {{<AGENT>_SCHEMA}} already injected by prompt_loader

This module centralizes the repair step so agents behave consistently.
"""

from __future__ import annotations

import json
import logging
from typing import Optional, Any, Sequence

from litellm import completion

from utils.schema_validator import extract_json_from_text, validate_and_fix_iterative

logger = logging.getLogger(__name__)


def llm_repair_json(
    *,
    repair_template: str,
    invalid_json: Any,
    validation_errors: Sequence[str],
    model: str,
    system_prompt: Optional[str] = None,
    max_tokens: int = 3000,
) -> Optional[dict]:
    """Ask the LLM to repair JSON output given a repair prompt template.

    Args:
        repair_template: Prompt text containing {{INVALID_JSON_OUTPUT}} and {{VALIDATION_ERRORS}}.
        invalid_json: The JSON object (or fallback object) to embed in the template.
        validation_errors: List of schema validation errors.
        model: LLM model identifier.
        system_prompt: Optional system prompt to include.
        max_tokens: Max tokens for the repair response.

    Returns:
        Repaired JSON dict if extraction succeeded, else None.
    """
    prompt = (
        repair_template
        .replace("{{INVALID_JSON_OUTPUT}}", json.dumps(invalid_json, indent=2, ensure_ascii=False))
        .replace("{{VALIDATION_ERRORS}}", "\n".join(validation_errors))
    )

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    resp = completion(
        model=model,
        messages=messages,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    repaired_text = resp.choices[0].message.content or ""
    return extract_json_from_text(repaired_text)


def validate_and_repair_once(
    *,
    data: dict,
    schema: dict,
    repair_template: Optional[str],
    model: str,
    system_prompt: Optional[str] = None,
    local_fix_attempts: int = 3,
    repair_max_tokens: int = 3000,
) -> tuple[bool, dict, list[str]]:
    """Validate+autofix, then optionally do a single LLM repair pass.

    Returns:
        (is_valid, fixed_data, errors)
    """
    is_valid, fixed, errors = validate_and_fix_iterative(data, schema, max_attempts=local_fix_attempts)
    if is_valid:
        return True, fixed, []

    if not repair_template:
        return False, fixed, errors

    repaired = llm_repair_json(
        repair_template=repair_template,
        invalid_json=data,
        validation_errors=errors,
        model=model,
        system_prompt=system_prompt,
        max_tokens=repair_max_tokens,
    )

    if repaired is None:
        return False, fixed, errors

    is_valid2, fixed2, errors2 = validate_and_fix_iterative(repaired, schema, max_attempts=local_fix_attempts)
    if is_valid2:
        return True, fixed2, []

    return False, fixed2, errors2


