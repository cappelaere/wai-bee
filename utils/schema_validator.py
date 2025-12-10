"""Utility for JSON schema validation and auto-fixing.

This module provides functions to validate JSON data against schemas and
attempt automatic fixes for common validation errors.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional, Any
from jsonschema import validate, ValidationError, Draft7Validator

logger = logging.getLogger()


def load_schema(schema_path: Path) -> dict:
    """Load JSON schema from file.
    
    Args:
        schema_path: Path to the JSON schema file.
    
    Returns:
        Schema as a dictionary.
    
    Raises:
        FileNotFoundError: If schema file doesn't exist.
        json.JSONDecodeError: If schema file is not valid JSON.
    
    Example:
        >>> schema_path = Path("schemas/recommendation_agent_schema.json")
        >>> schema = load_schema(schema_path)
        >>> print(schema["title"])
        Recommendation Agent Output Schema
    """
    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        logger.debug(f"Loaded schema from: {schema_path}")
        return schema
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file: {str(e)}")
        raise


def validate_json(data: dict, schema: dict) -> tuple[bool, list[str]]:
    """Validate JSON data against schema.
    
    Args:
        data: JSON data to validate.
        schema: JSON schema to validate against.
    
    Returns:
        Tuple of (is_valid, list_of_error_messages).
    
    Example:
        >>> schema = load_schema(Path("schemas/recommendation_agent_schema.json"))
        >>> data = {"summary": "Good", "profile_features": {...}, "scores": {...}}
        >>> is_valid, errors = validate_json(data, schema)
        >>> print(is_valid)
        True
    """
    validator = Draft7Validator(schema)
    errors = []
    
    for error in validator.iter_errors(data):
        error_path = ".".join(str(p) for p in error.path) if error.path else "root"
        error_msg = f"{error_path}: {error.message}"
        errors.append(error_msg)
        logger.debug(f"Validation error: {error_msg}")
    
    is_valid = len(errors) == 0
    if is_valid:
        logger.debug("JSON validation successful")
    else:
        logger.warning(f"JSON validation failed with {len(errors)} errors")
    
    return is_valid, errors


def auto_fix_json(data: dict, schema: dict, errors: list[str]) -> tuple[bool, dict]:
    """Attempt to auto-fix common JSON schema violations.
    
    Common fixes:
    - Add missing required fields with default values
    - Convert types (string to number, etc.)
    - Fix enum values to closest match
    - Ensure arrays are arrays, objects are objects
    - Remove extra fields not in schema
    
    Args:
        data: JSON data with validation errors.
        schema: JSON schema to validate against.
        errors: List of validation error messages.
    
    Returns:
        Tuple of (was_fixed, fixed_data).
        If fixes were applied, was_fixed is True.
    
    Example:
        >>> data = {"summary": "Good"}  # Missing required fields
        >>> schema = load_schema(Path("schemas/recommendation_agent_schema.json"))
        >>> _, errors = validate_json(data, schema)
        >>> was_fixed, fixed_data = auto_fix_json(data, schema, errors)
        >>> print(was_fixed)
        True
    """
    fixed_data = data.copy()
    fixes_applied = False
    
    # Fix 1: Add missing required fields
    if "required" in schema:
        for required_field in schema["required"]:
            if required_field not in fixed_data:
                default_value = _get_default_value_for_field(schema, required_field)
                fixed_data[required_field] = default_value
                fixes_applied = True
                logger.debug(f"Added missing required field: {required_field}")
    
    # Fix 2: Fix nested objects
    if "properties" in schema:
        for field_name, field_schema in schema["properties"].items():
            if field_name in fixed_data:
                if field_schema.get("type") == "object":
                    # Recursively fix nested objects
                    nested_fixed, nested_data = auto_fix_json(
                        fixed_data[field_name] if isinstance(fixed_data[field_name], dict) else {},
                        field_schema,
                        []
                    )
                    if nested_fixed:
                        fixed_data[field_name] = nested_data
                        fixes_applied = True
                
                elif field_schema.get("type") == "array":
                    # Ensure arrays are arrays
                    if not isinstance(fixed_data[field_name], list):
                        fixed_data[field_name] = []
                        fixes_applied = True
                        logger.debug(f"Converted {field_name} to array")
                
                # Fix enum values
                if "enum" in field_schema:
                    if fixed_data[field_name] not in field_schema["enum"]:
                        # Try to find closest match
                        closest = _find_closest_enum_value(
                            fixed_data[field_name],
                            field_schema["enum"]
                        )
                        if closest:
                            fixed_data[field_name] = closest
                            fixes_applied = True
                            logger.debug(f"Fixed enum value for {field_name}: {closest}")
    
    return fixes_applied, fixed_data


def _get_default_value_for_field(schema: dict, field_name: str) -> Any:
    """Get appropriate default value for a missing field.
    
    Args:
        schema: JSON schema.
        field_name: Name of the field.
    
    Returns:
        Default value based on field type.
    """
    if "properties" not in schema or field_name not in schema["properties"]:
        return None
    
    field_schema = schema["properties"][field_name]
    field_type = field_schema.get("type")
    
    if field_type == "string":
        return "Unknown"
    elif field_type == "integer" or field_type == "number":
        return 0
    elif field_type == "boolean":
        return False
    elif field_type == "array":
        return []
    elif field_type == "object":
        # Recursively create default object
        default_obj = {}
        if "properties" in field_schema:
            for nested_field in field_schema.get("required", []):
                default_obj[nested_field] = _get_default_value_for_field(field_schema, nested_field)
        return default_obj
    elif isinstance(field_type, list):
        # Handle union types like ["integer", "number"]
        if "string" in field_type:
            return "Unknown"
        elif "integer" in field_type or "number" in field_type:
            return 0
        elif "array" in field_type:
            return []
        elif "object" in field_type:
            return {}
    
    return None


def _find_closest_enum_value(value: str, enum_values: list[str]) -> Optional[str]:
    """Find closest matching enum value.
    
    Args:
        value: Current value.
        enum_values: List of valid enum values.
    
    Returns:
        Closest matching enum value, or None if no good match.
    """
    if not isinstance(value, str):
        return enum_values[0] if enum_values else None
    
    value_lower = value.lower().replace("_", " ").replace("-", " ")
    
    # Try exact match (case-insensitive)
    for enum_val in enum_values:
        if enum_val.lower() == value_lower:
            return enum_val
    
    # Try partial match
    for enum_val in enum_values:
        enum_lower = enum_val.lower().replace("_", " ").replace("-", " ")
        if value_lower in enum_lower or enum_lower in value_lower:
            return enum_val
    
    # Return first enum value as fallback
    return enum_values[0] if enum_values else None


def extract_json_from_text(text: str) -> Optional[dict]:
    """Extract JSON from LLM response that may contain markdown or extra text.
    
    Handles common LLM response formats:
    - JSON wrapped in ```json ... ```
    - JSON with explanatory text before/after
    - Multiple JSON objects (returns first valid one)
    
    Args:
        text: Text that may contain JSON.
    
    Returns:
        Extracted JSON as dict, or None if no valid JSON found.
    
    Example:
        >>> text = "Here's the analysis:\\n```json\\n{\"summary\": \"Good\"}\\n```"
        >>> data = extract_json_from_text(text)
        >>> print(data["summary"])
        Good
    """
    # Try to extract JSON from markdown code blocks
    json_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON object in text
    brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(brace_pattern, text, re.DOTALL)
    
    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue
    
    # Try parsing the entire text as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Could not extract valid JSON from text")
        return None


def validate_and_fix_iterative(
    data: dict,
    schema: dict,
    max_attempts: int = 3
) -> tuple[bool, dict, list[str]]:
    """Validate JSON and iteratively attempt fixes.
    
    Args:
        data: JSON data to validate.
        schema: JSON schema to validate against.
        max_attempts: Maximum number of fix attempts.
    
    Returns:
        Tuple of (is_valid, final_data, error_messages).
    
    Example:
        >>> data = {"summary": "Good"}  # Missing fields
        >>> schema = load_schema(Path("schemas/recommendation_agent_schema.json"))
        >>> is_valid, fixed_data, errors = validate_and_fix_iterative(data, schema)
        >>> print(is_valid)
        True
    """
    current_data = data
    
    for attempt in range(max_attempts):
        is_valid, errors = validate_json(current_data, schema)
        
        if is_valid:
            logger.info(f"JSON validation successful after {attempt} fix attempts")
            return True, current_data, []
        
        logger.debug(f"Fix attempt {attempt + 1}/{max_attempts}")
        was_fixed, current_data = auto_fix_json(current_data, schema, errors)
        
        if not was_fixed:
            logger.warning("No fixes could be applied")
            break
    
    # Final validation
    is_valid, errors = validate_json(current_data, schema)
    return is_valid, current_data, errors


# Made with Bob