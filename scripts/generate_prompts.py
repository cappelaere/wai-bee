#!/usr/bin/env python3

"""
generate_prompts.py

Generate analysis and repair prompts for each enabled *scoring* artifact
from a validated scholarship config.yml.

This generator emits LLM-ready prompts:
- "evaluation assistant" role framing
- strict "JSON only" output contract
- schema placeholder tokens like {{RESUME_SCHEMA}} (to be injected at runtime)

USAGE:
    python scripts/generate_prompts.py data/<scholarship-id>

OUTPUT:
    data/<scholarship-id>/prompts/
        <artifact>_analysis.txt
        <artifact>_repair.txt
"""

from __future__ import annotations

import sys
import json
from pathlib import Path

import yaml
from jsonschema import validate

from cross_field_rules import validate_cross_field_constraints


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_yaml(path: Path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_json(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text.strip() + "\n")


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def validate_config(cfg, schema):
    validate(instance=cfg, schema=schema)
    validate_cross_field_constraints(cfg)


# ------------------------------------------------------------
# Shared Prompt Blocks (Authoritative)
# ------------------------------------------------------------

SCORING_RULES = """## Scoring Rules

- Scores must be integers from **0 to 10**
- Use the full range when justified
- If evidence is weak, missing, or unclear, assign a **lower score**
- Do **not** penalize for formatting or writing style
- Do **not** reward prestige alone (titles, organizations, or institutions)
"""

SELF_CHECK_BLOCK = """## Self-Check Requirement (Mandatory)

Before returning your response:

1. Validate that the output matches the schema exactly
2. Confirm:
   - All required facets are present
   - Facet names match exactly
   - Scores are integers within the allowed range
   - No extra fields are included
3. If the output does not conform, **repair it silently**
4. Return **only** the final valid JSON
"""

REPAIR_TEMPLATE = """You previously generated JSON that does **not** conform to the required output schema
for a **{ARTIFACT_TITLE} analysis**.

Your task is to **repair the JSON** so that it conforms **exactly**
to the authoritative schema provided below.

---

## Repair Rules (Follow Exactly)

- Do **not** re-analyze the artifact
- Do **not** add or remove facets
- Do **not** rename facet names
- Do **not** change scores, rationales, or evidence **unless required**
- Do **not** add commentary or formatting outside JSON
- Return **JSON only**

---

## Invalid JSON Output

```json
{{INVALID_JSON_OUTPUT}}
```

---

## Validation Errors

{{VALIDATION_ERRORS}}

---

## Required Output Schema (Authoritative)

```json
{SCHEMA_TOKEN}
```

---

Return **only** valid JSON.
"""


# ------------------------------------------------------------
# Prompt Generation
# ------------------------------------------------------------

def _scholarship_display_name(meta: dict) -> str:
    org = (meta.get("organization") or "").strip()
    program = (meta.get("program") or "").strip()
    cycle_year = meta.get("cycle_year")

    base = " ".join([p for p in [org, program] if p]).strip() or "Scholarship"
    if cycle_year:
        return f"{base} ({cycle_year})"
    return base


def generate_analysis_prompt(artifact_name: str, artifact_cfg: dict, scholarship_meta: dict) -> str:
    artifact_title = artifact_name.replace("_", " ").title()
    purpose = (artifact_cfg.get("purpose") or "").replace("_", " ").strip()
    facets_cfg = artifact_cfg.get("facets") or []

    facets_lines: list[str] = []
    for i, facet in enumerate(facets_cfg, start=1):
        name = (facet.get("name") or "").strip()
        desc = (facet.get("description") or "").strip()
        evidence = facet.get("evidence_expected") or []

        block: list[str] = [f"{i}. **{name}**", desc]
        if evidence:
            block.append("")
            block.append("   Evidence expected:")
            for e in evidence:
                block.append(f"   - {e}")

        facets_lines.append("\n".join([line for line in block if line]))

    facets_block = "\n\n".join(facets_lines)
    schema_placeholder = f"{{{{{artifact_name.upper()}_SCHEMA}}}}"
    scholarship_name = _scholarship_display_name(scholarship_meta)

    return f"""You are an **evaluation assistant** supporting the **{scholarship_name}** review process.

Your task is to analyze a **{artifact_title}** and score it **only** according to the defined evaluation facets below.

You must follow the scoring rules and output contract exactly.

---

## Artifact Being Evaluated

**Artifact:** {artifact_title}
**Purpose:** {purpose}

---

## Evaluation Facets (Score Each 0–10)

Evaluate the {artifact_title.lower()} using **only these facets**:

{facets_block}

Do **not** infer attributes that are not supported by the provided content.

---

{SCORING_RULES}

---

## Evidence & Rationale Requirements

For **each facet**, provide:

- A **score**
- A concise **rationale**
- Specific **evidence cited directly from the {artifact_title.lower()}**

Evidence must reference the provided content explicitly.

---

## Output Contract (Required)

You must return **valid JSON only**, conforming **exactly** to the schema below.

```json
{schema_placeholder}
```

---

{SELF_CHECK_BLOCK}

Return **JSON only**.
"""


def generate_repair_prompt(artifact_name: str) -> str:
    # Use simple string replacement (not .format) so we preserve double-brace
    # placeholders like {{INVALID_JSON_OUTPUT}} and {{VALIDATION_ERRORS}}.
    return (
        REPAIR_TEMPLATE
        .replace("{ARTIFACT_TITLE}", artifact_name.replace("_", " ").title())
        .replace("{SCHEMA_TOKEN}", f"{{{{{artifact_name.upper()}_SCHEMA}}}}")
    )


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_prompts.py <scholarship-folder>")
        sys.exit(1)

    scholarship_dir = Path(sys.argv[1]).resolve()
    repo_root = Path(__file__).resolve().parent.parent

    config_path = scholarship_dir / "config.yml"
    schema_path = repo_root / "schemas" / "config.schema.json"
    prompts_dir = scholarship_dir / "prompts"

    if not config_path.exists():
        print(f"❌ config.yml not found at {config_path}")
        sys.exit(1)

    if not schema_path.exists():
        print(f"❌ config.schema.json not found at {schema_path}")
        sys.exit(1)

    try:
        cfg = load_yaml(config_path)
        schema = load_json(schema_path)
        validate_config(cfg, schema)
    except Exception as e:
        print("❌ Configuration validation failed:")
        print(str(e))
        sys.exit(1)

    metadata = (cfg.get("scholarship") or {}).get("metadata", {})

    generated = 0
    for artifact_name, artifact_cfg in (cfg.get("artifacts") or {}).items():
        if not artifact_cfg.get("enabled", False):
            continue

        # Skip preprocessing / non-scoring artifacts (no facets)
        if not artifact_cfg.get("facets"):
            continue

        analysis_prompt = generate_analysis_prompt(artifact_name, artifact_cfg, metadata)
        repair_prompt = generate_repair_prompt(artifact_name)

        write_text(prompts_dir / f"{artifact_name}_analysis.txt", analysis_prompt)
        write_text(prompts_dir / f"{artifact_name}_repair.txt", repair_prompt)
        generated += 2

    print(f"✅ Prompts generated in {prompts_dir} for {scholarship_dir.name} ({generated} files)")


if __name__ == "__main__":
    main()


