#!/usr/bin/env python3

"""
generate_all.py

End-to-end generator for a scholarship configuration.

This script orchestrates:
1) Validation
2) Artifact generation
3) Prompt generation
4) Document generation

USAGE:
    python scripts/generate_all.py data/<scholarship-id>
"""

import sys
from pathlib import Path
import subprocess


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def run_step(description: str, command: list):
    print(f"\n▶ {description}")
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"❌ Failed: {description}")
        sys.exit(result.returncode)
    print(f"✅ Completed: {description}")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/generate_all.py <scholarship-folder>")
        sys.exit(1)

    scholarship_dir = Path(sys.argv[1]).resolve()

    if not scholarship_dir.exists():
        print(f"❌ Scholarship folder not found: {scholarship_dir}")
        sys.exit(1)

    scripts_dir = Path(__file__).resolve().parent

    validate_cmd = ["python", str(scripts_dir / "validate_config.py"), str(scholarship_dir)]
    artifacts_cmd = ["python", str(scripts_dir / "generate_artifacts.py"), str(scholarship_dir)]
    prompts_cmd = ["python", str(scripts_dir / "generate_prompts.py"), str(scholarship_dir)]
    docs_cmd = ["python", str(scripts_dir / "generate_documents.py"), str(scholarship_dir)]

    print(f"\n🚀 Generating all artifacts for: {scholarship_dir.name}")

    run_step("Validating configuration", validate_cmd)
    run_step("Generating machine artifacts", artifacts_cmd)
    run_step("Generating LLM prompts", prompts_cmd)
    run_step("Generating human-readable documents", docs_cmd)

    print(f"\n🎉 All generation steps completed successfully for {scholarship_dir.name}")


if __name__ == "__main__":
    main()
