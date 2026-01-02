#!/usr/bin/env python3
"""
Simulate reviewer scores for current applicants in a scholarship.

This script:
  - Loads reviewers from config/users.json (where "reviewer": true)
  - Identifies current applicants from outputs/{scholarship}/*
  - Uses the API's /reviews endpoint to submit scores for each reviewer/applicant

It runs the API app in-process via FastAPI's TestClient, so it does not require
the Docker containers to be running. Reviews are written under:

  outputs/{scholarship}/reviews/{initials}/{wai_number}.json

Usage (from project root):

  source venv/bin/activate
  python examples/simulate_reviewer_scores.py <scholarship>

Examples:
  python examples/simulate_reviewer_scores.py Delaney_Wings
  python examples/simulate_reviewer_scores.py Evans_Wings
"""

import json
import os
import random
import sys
from pathlib import Path
from typing import List, Dict

from fastapi.testclient import TestClient

# Ensure project root is on sys.path and is the working directory
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
os.chdir(ROOT_DIR)

from bee_agents.api import app  # noqa: E402
from bee_agents.auth import create_token_with_context, load_user_config  # noqa: E402


def get_reviewer_users_for_scholarship(config: Dict, scholarship: str) -> List[Dict]:
    """Return user entries that are reviewers for the given scholarship."""
    reviewers: List[Dict] = []
    for username, info in config.get("users", {}).items():
        if not info.get("enabled", True):
            continue
        if not info.get("reviewer", False):
            continue

        scholarships = info.get("scholarships", [])
        if "*" in scholarships or scholarship in scholarships:
            reviewers.append({"username": username, **info})
    return reviewers


def get_current_applicants_for_scholarship(scholarship: str) -> List[str]:
    """Return WAI numbers for current applicants with outputs for the scholarship."""
    base_dir = Path("outputs") / scholarship
    if not base_dir.exists():
        return []

    wai_numbers: List[str] = []
    for item in base_dir.iterdir():
        if not item.is_dir():
            continue
        # Reuse the same heuristic as DataService: require application_analysis.json
        if (item / "application_analysis.json").exists():
            wai_numbers.append(item.name)
    wai_numbers.sort()
    return wai_numbers


def simulate_scores(scholarship: str) -> None:
    """Simulate reviewer scores for all applicants in the given scholarship."""
    config = load_user_config()

    reviewers = get_reviewer_users_for_scholarship(config, scholarship)
    if not reviewers:
        print(f"No reviewers configured for {scholarship}")
        return

    wai_numbers = get_current_applicants_for_scholarship(scholarship)
    if not wai_numbers:
        print(f"No current applicants found under outputs/{scholarship}")
        return

    print(f"Found {len(reviewers)} reviewers for {scholarship}: {[r['username'] for r in reviewers]}")
    print(f"Found {len(wai_numbers)} applicants for {scholarship}: {wai_numbers}")

    client = TestClient(app)

    total_submissions = 0

    for reviewer in reviewers:
        username = reviewer["username"]
        initials = reviewer.get("initials", "XX")

        # Create an in-process token so the reviews router can authenticate
        token_data = create_token_with_context(username)
        token = token_data["token"]
        headers = {"Authorization": f"Bearer {token}"}

        print(f"\nSubmitting reviews for reviewer {username} ({initials})...")

        # For test purposes, score all applicants with random scores in 6–10
        for wai in wai_numbers:
            score = random.randint(6, 10)
            comments = f"Simulated review by {initials} with score {score}."

            response = client.post(
                "/reviews",
                params={"scholarship": scholarship, "wai_number": wai},
                data={"score": score, "comments": comments},
                headers=headers,
            )

            if response.status_code != 200:
                print(
                    f"  ❌ Failed to submit review for {wai} as {username}: "
                    f"{response.status_code} {response.text}"
                )
                continue

            data = response.json()
            total_submissions += 1
            print(
                f"  ✓ {username} scored WAI {wai} = {data['score']}/10 "
                f"(stored at outputs/{scholarship}/reviews/{initials}/{wai}.json)"
            )

    print(f"\nCompleted {total_submissions} review submissions for {scholarship}.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examples/simulate_reviewer_scores.py <scholarship>")
        print("Example: python examples/simulate_reviewer_scores.py Evans_Wings")
        sys.exit(1)
    
    scholarship_arg = sys.argv[1]
    simulate_scores(scholarship_arg)


