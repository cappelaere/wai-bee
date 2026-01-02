#!/usr/bin/env python3

"""
generate_documents.py

Generate human-readable scholarship documents from config.yml.

USAGE:
    python generate_documents.py data/<scholarship-id>

PRECONDITIONS:
    - config.yml exists
    - config.yml passes schema + cross-field validation

OUTPUT:
    - SCHOLARSHIP_OVERVIEW.md
"""

import sys
import yaml
import json
from pathlib import Path
from datetime import datetime
from jsonschema import validate, ValidationError

from cross_field_rules import validate_cross_field_constraints


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def load_yaml(path: Path):
    with open(path) as f:
        return yaml.safe_load(f)

def load_json(path: Path):
    with open(path) as f:
        return json.load(f)

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(text.strip() + "\n")

def fmt_date(date_str: str):
    try:
        return datetime.fromisoformat(date_str).strftime("%B %d, %Y")
    except Exception:
        return date_str


# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def validate_config(config, schema):
    validate(instance=config, schema=schema)
    validate_cross_field_constraints(config)


# ------------------------------------------------------------
# Rendering Functions
# ------------------------------------------------------------

def render_header(cfg):
    meta = cfg["scholarship"].get("metadata", {})
    return f"""# {meta.get('organization', '')} — {meta.get('program', 'Scholarship')}
**Scholarship Manager Overview**

**Cycle:** {meta.get('cycle_year', '')}  
**Delivery:** {meta.get('delivery_mode', '').replace('_', ' ').title()}  
**Location:** {meta.get('location', '')}  
**Dates:** {meta.get('dates', '')}
"""

def render_program_overview(cfg):
    intent = cfg["scholarship"]["intent"]
    return f"""## Program Overview

{intent["purpose"]}

{intent["definition_of_excellence"]}
"""

def render_target_audience(cfg):
    elig = cfg["scholarship"]["eligibility"]
    ta = cfg["scholarship"]["intent"]["target_audience"]

    return f"""## Who This Scholarship Is For

Applicants must meet **all** of the following criteria:

- Member of {elig["membership"]["organization"]}
  - Join by {fmt_date(elig["membership"]["must_be_member_by"])}
  - Remain a member through {fmt_date(elig["membership"]["must_remain_member_through"])}
- At least {ta["minimum_years_experience"]} years of professional experience
- Career stage: {ta["career_stage"].replace('_', ' ').title()}
- Able to commit to attending the full program
"""

def render_submission_requirements(cfg):
    sub = cfg["scholarship"]["submission_requirements"]

    sections = ["## Required Application Materials"]

    if sub.get("application_form", {}).get("required"):
        sections.append("""### Application Form
- All required fields must be completed
- Includes a statement confirming commitment to course dates
""")

    if sub.get("resume", {}).get("required"):
        sections.append(f"""### Professional Resume
- Maximum {sub["resume"]["max_pages"]} pages
- No photo permitted
- Should reflect leadership roles, progression, and impact
""")

    if sub.get("essay", {}).get("required"):
        sections.append(f"""### Leadership Essay
- Maximum {sub["essay"]["max_words"]} words
- Prompt:
> {sub["essay"]["prompt"]}
""")

    if sub.get("recommendation", {}).get("required"):
        sections.append(f"""### Letter of Recommendation
- {sub["recommendation"]["count"]} letter required
- Maximum {sub["recommendation"].get("max_pages", 1)} page(s)
- Family members are not permitted as recommenders
""")

    return "\n".join(sections)

def render_evaluation_process(cfg):
    artifacts = cfg["artifacts"]
    sections = ["## How Applications Are Evaluated"]

    for name, art in artifacts.items():
        if not art.get("enabled"):
            continue

        title = name.replace("_", " ").title()
        sections.append(f"""### {title}

This component is reviewed to assess:
""")

        for facet in art["facets"]:
            sections.append(f"- **{facet['name']}**: {facet['description']}")

    return "\n".join(sections)

def render_scoring(cfg):
    scoring = cfg["scoring"]
    weights = cfg["aggregation"]["weights"]

    rows = "\n".join(
        f"| {k.replace('_',' ').title()} | {int(v*100)}% |"
        for k, v in weights.items()
    )

    return f"""## Scoring Model (Internal Transparency)

Each component is scored on a **{scoring['scale']['min']}–{scoring['scale']['max']} scale**:

- **Low scores** indicate missing or weak evidence
- **Mid-range scores** indicate adequate evidence
- **High scores** indicate exceptional leadership and impact

### Weighting of Components

| Component | Weight |
|----------|--------|
{rows}
"""

def render_governance(cfg):
    return """## Governance & Oversight

- Evaluation criteria are fixed before the review cycle begins
- Criteria cannot be changed mid-cycle
- AI tools assist with consistency and scale
- **Final decisions are always made by human reviewers**
- All scores and decisions are auditable and traceable
"""

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_documents.py <scholarship-folder>")
        sys.exit(1)

    scholarship_dir = Path(sys.argv[1]).resolve()
    repo_root = Path(__file__).resolve().parent.parent

    config_path = scholarship_dir / "config.yml"
    schema_path = repo_root / "schemas" / "config.schema.json"

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

    document = "\n\n".join([
        render_header(cfg),
        render_program_overview(cfg),
        render_target_audience(cfg),
        render_submission_requirements(cfg),
        render_evaluation_process(cfg),
        render_scoring(cfg),
        render_governance(cfg),
        "\n**End of Scholarship Overview**"
    ])

    output_path = scholarship_dir / "SCHOLARSHIP_OVERVIEW.md"
    write_text(output_path, document)

    print(f"✅ Generated {output_path.name} for {scholarship_dir.name}")


if __name__ == "__main__":
    main()
