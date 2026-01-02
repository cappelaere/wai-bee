#!/usr/bin/env python3

"""
validate_config.py

Validate a scholarship config.yml against:
1) Structural JSON Schema
2) Cross-field governance rules

USAGE:
    python validate_config.py data/<scholarship-id>

EXIT CODES:
    0 - Validation successful
    1 - Validation failed
"""

import sys
import yaml
import json
from pathlib import Path
from jsonschema import validate, ValidationError

from cross_field_rules import validate_cross_field_constraints


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_config.py <scholarship-folder>")
        sys.exit(1)

    scholarship_dir = Path(sys.argv[1]).resolve()
    # scripts/ is one level below repo root
    repo_root = Path(__file__).resolve().parent.parent

    config_path = scholarship_dir / "config.yml"
    schema_path = repo_root / "schemas" / "config.schema.json"

    # ------------------------------------------------------------
    # Basic path validation
    # ------------------------------------------------------------
    if not scholarship_dir.exists():
        print(f"❌ Scholarship folder not found: {scholarship_dir}")
        sys.exit(1)

    if not config_path.exists():
        print(f"❌ config.yml not found at {config_path}")
        sys.exit(1)

    if not schema_path.exists():
        print(f"❌ config.schema.json not found at {schema_path}")
        sys.exit(1)

    try:
        # --------------------------------------------------------
        # Load inputs
        # --------------------------------------------------------
        with open(config_path) as f:
            config = yaml.safe_load(f)

        with open(schema_path) as f:
            schema = json.load(f)

        # --------------------------------------------------------
        # 1. Structural schema validation
        # --------------------------------------------------------
        validate(instance=config, schema=schema)

        # --------------------------------------------------------
        # 2. Cross-field governance validation
        # --------------------------------------------------------
        validate_cross_field_constraints(config)

        print(f"✅ {scholarship_dir.name}: config.yml is valid and governance-compliant")

    except ValidationError as e:
        print("❌ Schema validation failed:")
        print(e.message)
        sys.exit(1)

    except ValueError as e:
        # Raised explicitly by cross_field_rules.py
        print("❌ Cross-field governance validation failed:")
        print(str(e))
        sys.exit(1)

    except Exception as e:
        print("❌ Unexpected validation error:")
        print(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()