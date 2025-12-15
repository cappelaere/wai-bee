#!/usr/bin/env python
"""
Generate scholarship runtime artifacts from canonical config.

This script reads a canonical config file:
    data/<Scholarship>/config.yml

and regenerates:
    - data/<Scholarship>/scholarship.json
    - data/<Scholarship>/agents.json
    - data/<Scholarship>/criteria/*.txt
    - optional weights snapshot: data/<Scholarship>/weights.json

Existing runtime code (criteria_loader, agents_config, score_calculator)
continues to read these generated files.
"""

import json
import sys
from pathlib import Path

import yaml  # type: ignore


def load_config(scholarship_folder: Path) -> dict:
    config_path = scholarship_folder / "config.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def generate_scholarship_json(scholarship_folder: Path, config: dict) -> None:
    """Generate scholarship.json from config.scholarship."""
    sch = config.get("scholarship", {})
    out = {
        "name": sch.get("name"),
        "folder": sch.get("id"),
        "description": sch.get("description"),
        "award_amount": sch.get("award_amount"),
        "award_period": sch.get("award_period"),
        "eligibility": sch.get("eligibility", {}),
        "application_requirements": sch.get("application_requirements", []),
        "selection_criteria": sch.get("selection_criteria_summary", []),
        "contact": sch.get("contact", {}),
        "deadline": sch.get("deadlines", {}).get("apply_by"),
        "notification_date": sch.get("deadlines", {}).get("notify_by"),
        "year": sch.get("year"),
    }
    write_json(scholarship_folder / "scholarship.json", out)


def generate_agents_json(scholarship_folder: Path, config: dict) -> None:
    """Generate agents.json from config.agents + scoring."""
    agents_cfg = config.get("agents", {})
    scoring_cfg = config.get("scoring", {})
    scoring_agents = scoring_cfg.get("scoring_agents", [])

    agents_list = []
    for name, agent in agents_cfg.items():
        agent_entry = {
            "name": name,
            "display_name": agent.get("display_name", name.title()),
            "description": agent.get("description", ""),
            "input_files": agent.get("input_files", []),
            "output_directory": agent.get("output_directory"),
            "output_file": agent.get("output_file"),
            "schema": agent.get("schema"),
            "criteria": None,
            "evaluates": agent.get("evaluates", []),
            "weight": agent.get("weight"),
            "enabled": agent.get("enabled", True),
            "required": agent.get("required", False),
        }

        criteria_ref = agent.get("criteria_ref")
        if criteria_ref:
            agent_entry["criteria"] = str(
                scholarship_folder / "criteria" / f"{criteria_ref}_criteria.txt"
            )

        agents_list.append(agent_entry)

    weights_total = sum(
        (a.get("weight") or 0.0) for a in agents_cfg.values() if a.get("weight") is not None
    )

    out = {
        "scholarship_name": config.get("scholarship", {}).get("id"),
        "description": f"Agent configuration for {config.get('scholarship', {}).get('name', '')}",
        "version": "1.0.0",
        "agents": agents_list,
        "scoring_agents": scoring_agents,
        "total_weight": round(weights_total, 2),
        "notes": [
            "Attachment agent must run first to prepare text files for other agents",
            "All scoring agents contribute to final weighted score",
            "Weights are managed via canonical config.yml",
            "Each agent produces an overall_score (0-100)",
            "Final score = sum(agent_score * weight) for all scoring agents",
        ],
    }
    write_json(scholarship_folder / "agents.json", out)


def generate_criteria_files(scholarship_folder: Path, config: dict) -> None:
    """Generate criteria/*.txt from config.criteria_text."""
    crit_root = scholarship_folder / "criteria"
    crit_root.mkdir(parents=True, exist_ok=True)

    criteria_text = config.get("criteria_text", {})
    for key, text in criteria_text.items():
        path = crit_root / f"{key}_criteria.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.rstrip() + "\n")


def generate_weights_json(scholarship_folder: Path, config: dict) -> None:
    """Optional weights snapshot file for tooling."""
    agents_cfg = config.get("agents", {})
    weights = {}
    for name, agent in agents_cfg.items():
        weight = agent.get("weight")
        if weight is not None:
            weights[name] = {
                "weight": weight,
                "description": agent.get("description", ""),
            }
    total = sum(w["weight"] for w in weights.values())
    out = {
        "scholarship_name": config.get("scholarship", {}).get("id"),
        "description": "Weights extracted from canonical config.yml",
        "weights": weights,
        "total_weight": round(total, 2),
    }
    write_json(scholarship_folder / "weights.json", out)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: generate_scholarship_artifacts.py <ScholarshipName>")
        print("Example: generate_scholarship_artifacts.py Delaney_Wings")
        return 1

    scholarship_name = argv[1]
    root = Path(__file__).resolve().parents[1]
    scholarship_folder = root / "data" / scholarship_name

    if not scholarship_folder.exists():
        print(f"Scholarship folder not found: {scholarship_folder}")
        return 1

    config = load_config(scholarship_folder)

    generate_scholarship_json(scholarship_folder, config)
    generate_agents_json(scholarship_folder, config)
    generate_criteria_files(scholarship_folder, config)
    generate_weights_json(scholarship_folder, config)

    print(f"Generated artifacts for scholarship: {scholarship_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))


