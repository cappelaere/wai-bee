#!/usr/bin/env python3

"""
generate_artifacts.py

Generate all derived scholarship artifacts from a validated config.yml.

USAGE:
    python generate_artifacts.py data/<scholarship-id>

BEHAVIOR:
    - ALWAYS validates config.yml first
    - Fails fast on validation errors
    - Generates deterministic artifacts only
"""

import sys
import yaml
import json
from pathlib import Path
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

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(text.strip() + "\n")

# ------------------------------------------------------------
# Validation
# ------------------------------------------------------------

def validate_config(config, schema):
    # 1. Structural validation
    validate(instance=config, schema=schema)

    # 2. Cross-field governance rules
    validate_cross_field_constraints(config)

# ------------------------------------------------------------
# Artifact Generators
# ------------------------------------------------------------

def generate_scholarship_json(config):
    return {
        "scholarship_id": config["scholarship"]["id"],
        "version": config["scholarship"]["version"],
        "status": config["scholarship"]["status"],
        "intent": config["scholarship"]["intent"],
        "eligibility": config["scholarship"]["eligibility"],
        "submission_requirements": config["scholarship"]["submission_requirements"],
        "artifacts": config["artifacts"],
        "scoring": config["scoring"],
        "aggregation": config["aggregation"]
    }

def generate_output_schema(artifact_name, artifact_cfg, scoring):
    facets = [f["name"] for f in artifact_cfg["facets"]]

    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": f"{artifact_name.capitalize()}AnalysisOutputSchema",
        "type": "object",
        "required": ["artifact_type", "facets", "overall_notes"],
        "properties": {
            "artifact_type": {
                "type": "string",
                "enum": [artifact_name]
            },
            "facets": {
                "type": "array",
                "minItems": len(facets),
                "maxItems": len(facets),
                "items": {
                    "type": "object",
                    "required": ["name", "score", "rationale", "evidence"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "enum": facets
                        },
                        "score": {
                            "type": "integer",
                            "minimum": scoring["scale"]["min"],
                            "maximum": scoring["scale"]["max"]
                        },
                        "rationale": { "type": "string" },
                        "evidence": { "type": "string" }
                    },
                    "additionalProperties": False
                }
            },
            "overall_notes": { "type": "string" }
        },
        "additionalProperties": False
    }

def generate_agent_def(artifact_name, artifact_cfg, weights, scholarship_dir):
    """Generate a full agent definition compatible with legacy code.
    
    Args:
        artifact_name: Name of the artifact (e.g., "application", "essay")
        artifact_cfg: Artifact configuration from config.yml
        weights: Aggregation weights dict from config.yml
        scholarship_dir: Path to scholarship directory for criteria paths
    
    Returns:
        Complete agent definition dict
    """
    # Generate display name from artifact name
    display_name = artifact_name.replace('_', ' ').title() + " Agent"
    
    # Get description from purpose and make it readable
    purpose = artifact_cfg.get("purpose", "")
    if purpose:
        # Convert snake_case to readable sentence
        description = f"Evaluates {purpose.replace('_', ' ')}"
    else:
        description = f"Analyzes {artifact_name} artifacts"
    
    # Extract facet names as evaluates list
    evaluates = [f["name"] for f in artifact_cfg.get("facets", [])]
    
    # Get weight from aggregation weights (None if not a scoring agent)
    weight = weights.get(artifact_name)
    
    # Get input files from config
    input_files = artifact_cfg.get("input_files", [])
    
    # Check if this is a preprocessing agent (no facets = no scoring)
    is_preprocessing = len(evaluates) == 0

    agent_def = {
        "name": artifact_name,
        "display_name": display_name,
        "description": description,
        "weight": weight,
        "enabled": artifact_cfg.get("enabled", True),
        "required": False,
        "input_files": input_files,
        "evaluates": evaluates
    }
    
    # Only add prompt/schema paths for scoring agents
    if not is_preprocessing:
        agent_def["analysis_prompt"] = f"prompts/{artifact_name}_analysis.txt"
        agent_def["repair_prompt"] = f"prompts/{artifact_name}_repair.txt"
        agent_def["schema"] = f"schemas_generated/{artifact_name}_analysis.schema.json"
        agent_def["output_directory"] = f"outputs/{artifact_name}"
        agent_def["output_file"] = f"{{id}}_{artifact_name}_analysis.json"
    else:
        # Preprocessing agent - outputs attachments
        agent_def["output_directory"] = "outputs/attachments"
        agent_def["output_file"] = "{id}_{index}.txt"
    
    return agent_def


def generate_analysis_prompt(artifact_name, artifact_cfg, scoring, scholarship):
    """Generate a detailed analysis prompt from facet definitions.
    
    Args:
        artifact_name: Name of the artifact (e.g., "application", "essay")
        artifact_cfg: Artifact configuration from config.yml
        scoring: Scoring configuration from config.yml
        scholarship: Scholarship configuration from config.yml
    
    Returns:
        Complete analysis prompt text
    """
    facets = artifact_cfg.get("facets", [])
    purpose = artifact_cfg.get("purpose", "").replace("_", " ")
    scale = scoring.get("scale", {"min": 0, "max": 10})
    semantics = scoring.get("semantics", {})
    missing = scoring.get("missing_evidence", {})
    
    scholarship_name = scholarship.get("metadata", {}).get("program", scholarship.get("id", ""))
    excellence = scholarship.get("intent", {}).get("definition_of_excellence", "")
    
    lines = [
        f"# {artifact_name.replace('_', ' ').title()} Analysis Evaluation Criteria",
        "",
        f"## Scholarship: {scholarship_name}",
        "",
        f"## Purpose: {purpose}",
        "",
    ]
    
    if excellence:
        lines.extend([
            "## Definition of Excellence",
            excellence.strip(),
            "",
        ])
    
    lines.extend([
        "## Scoring Scale",
        f"Score range: {scale['min']} to {scale['max']}",
        "",
        f"- {scale['min']}: {semantics.get('score_0', 'No evidence')}",
        f"- {(scale['min'] + scale['max']) // 2}: {semantics.get('score_5', 'Adequate evidence')}",
        f"- {scale['max']}: {semantics.get('score_10', 'Exceptional evidence')}",
        "",
    ])
    
    if missing:
        lines.extend([
            "## Missing Evidence Policy",
            f"- Maximum score when evidence is missing: {missing.get('max_score', 3)}",
            f"- Note required: {missing.get('note_required', True)}",
            "",
        ])
    
    lines.extend([
        "## Facets to Evaluate",
        "",
    ])
    
    for i, facet in enumerate(facets, 1):
        name = facet.get("name", "")
        desc = facet.get("description", "").strip()
        evidence = facet.get("evidence_expected", [])
        
        lines.append(f"### {i}. {name}")
        lines.append("")
        lines.append(desc)
        lines.append("")
        
        if evidence:
            lines.append("**Evidence Expected:**")
            for e in evidence:
                lines.append(f"- {e}")
            lines.append("")
    
    lines.extend([
        "## Output Format",
        "",
        "For each facet, provide:",
        "1. **score**: Integer score within the defined scale",
        "2. **rationale**: Brief explanation of the score",
        "3. **evidence**: Specific quotes or references from the document",
        "",
        "Also provide overall_notes summarizing the evaluation.",
    ])
    
    return "\n".join(lines)


def generate_repair_prompt(artifact_name, facets):
    """Generate a repair prompt for fixing invalid JSON output.
    
    Args:
        artifact_name: Name of the artifact
        facets: List of facet definitions
    
    Returns:
        Repair prompt text
    """
    facet_names = [f["name"] for f in facets]
    
    lines = [
        f"# Repair Instructions for {artifact_name.replace('_', ' ').title()} Analysis",
        "",
        "The previous output was invalid JSON. Please fix the output to match the required schema.",
        "",
        "## Required Structure",
        "",
        "```json",
        "{",
        f'  "artifact_type": "{artifact_name}",',
        '  "facets": [',
    ]
    
    for i, name in enumerate(facet_names):
        comma = "," if i < len(facet_names) - 1 else ""
        lines.extend([
            '    {',
            f'      "name": "{name}",',
            '      "score": <integer 0-10>,',
            '      "rationale": "<explanation>",',
            '      "evidence": "<quotes from document>"',
            f'    }}{comma}',
        ])
    
    lines.extend([
        '  ],',
        '  "overall_notes": "<summary>"',
        '}',
        '```',
        "",
        "## Common Fixes",
        "- Ensure all facet names match exactly as shown above",
        "- Ensure scores are integers, not strings",
        "- Ensure all required fields are present",
        "- Remove any trailing commas before closing brackets",
    ])
    
    return "\n".join(lines)


def generate_agents_json(config, scholarship_dir):
    """Generate complete agents.json compatible with legacy code.
    
    Args:
        config: Full config.yml contents
        scholarship_dir: Path to scholarship directory
    
    Returns:
        Complete agents.json structure
    """
    weights = config.get("aggregation", {}).get("weights", {})
    artifacts = config.get("artifacts", {})
    
    agents = []
    scoring_agents = []
    
    for artifact_name, artifact_cfg in artifacts.items():
        if not artifact_cfg.get("enabled", False):
            continue
        
        agent = generate_agent_def(artifact_name, artifact_cfg, weights, scholarship_dir)
        agents.append(agent)
        
        # Track scoring agents (those with weights)
        if artifact_name in weights:
            scoring_agents.append(artifact_name)
    
    total_weight = sum(weights.get(a, 0) for a in scoring_agents)
    
    return {
        "scholarship_name": config["scholarship"]["id"],
        "description": f"Agent configuration for {config['scholarship'].get('metadata', {}).get('program', config['scholarship']['id'])}",
        "version": config["scholarship"].get("version", "1.0.0"),
        "agents": agents,
        "scoring_agents": scoring_agents,
        "total_weight": round(total_weight, 2),
        "notes": [
            "Generated from config.yml - do not edit manually",
            "All scoring agents contribute to final weighted score",
            "Each agent produces facet scores on the configured scale",
            "Final score = sum(agent_score * weight) for all scoring agents"
        ]
    }

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python generate_artifacts.py <scholarship-folder>")
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
        # Load
        config = load_yaml(config_path)
        schema = load_json(schema_path)

        # Validate (MANDATORY)
        validate_config(config, schema)

        print("✅ Configuration validated successfully")

    except ValidationError as e:
        print("❌ Configuration validation failed:")
        print(e.message)
        sys.exit(1)

    except Exception as e:
        print("❌ Validation error:")
        print(str(e))
        sys.exit(1)

    # --------------------------------------------------------
    # Generation
    # --------------------------------------------------------

    scholarship_json_path = scholarship_dir / "scholarship.json"
    schemas_dir = scholarship_dir / "schemas_generated"
    agents_path = scholarship_dir / "agents.json"

    # Generate scholarship.json
    write_json(scholarship_json_path, generate_scholarship_json(config))

    # Generate per-artifact schemas (prompts are generated separately via scripts/generate_prompts.py)
    for artifact_name, artifact_cfg in config["artifacts"].items():
        if not artifact_cfg.get("enabled", False):
            continue

        facets = artifact_cfg.get("facets", [])
        
        # Skip schema/prompt generation for preprocessing agents (no facets)
        if not facets:
            continue

        # Generate output schema for this artifact
        schema_out = generate_output_schema(
            artifact_name,
            artifact_cfg,
            config["scoring"]
        )
        write_json(
            schemas_dir / f"{artifact_name}_analysis.schema.json",
            schema_out
        )

    # Generate complete agents.json (legacy-compatible)
    agents_json = generate_agents_json(config, scholarship_dir)
    write_json(agents_path, agents_json)

    print(f"✅ Artifacts generated for {scholarship_dir.name}")
    print(f"   - scholarship.json")
    print(f"   - agents.json ({len(agents_json['agents'])} agents, {len(agents_json['scoring_agents'])} scoring)")
    print(f"   - {len(list(schemas_dir.glob('*.json')))} output schemas")
    print(f"   - prompts are generated separately (run scripts/generate_prompts.py)")

if __name__ == "__main__":
    main()
