"""Utilities for storing and retrieving reviewer scores.

Reviews are stored as JSON files under:

    outputs/{Scholarship}/reviews/{initials}/{wai_number}.json

Each file contains a single review for a given reviewer (identified by initials)
and WAI application number.

This module also provides helpers to aggregate all reviews for a scholarship
and generate CSV summaries.
"""

import csv
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .auth import get_user_info, get_user_scholarships

logger = logging.getLogger(__name__)


def _get_reviews_base_dir() -> Path:
    """Return the base outputs directory for reviews."""
    return Path("outputs")


def get_reviewer_initials(username: str) -> Optional[str]:
    """Get reviewer initials from user configuration."""
    user_info = get_user_info(username)
    if not user_info:
        return None
    return user_info.get("initials")


def is_reviewer(username: str) -> bool:
    """Return True if the user is marked as a reviewer in config."""
    user_info = get_user_info(username)
    if not user_info:
        return False
    return bool(user_info.get("reviewer", False))


def get_review_file_path(
    scholarship: str,
    reviewer_initials: str,
    wai_number: str,
) -> Path:
    """Build the path to the review JSON file."""
    base_dir = _get_reviews_base_dir()
    return base_dir / scholarship / "reviews" / reviewer_initials / f"{wai_number}.json"


def save_review(
    scholarship: str,
    wai_number: str,
    reviewer_username: str,
    reviewer_initials: str,
    score: int,
    comments: Optional[str] = None,
) -> Dict[str, Any]:
    """Create or update a review JSON file for the given reviewer and WAI.

    If the file already exists, preserves the original created_at timestamp and
    updates score/comments and updated_at. Otherwise, creates a new file.
    """
    review_path = get_review_file_path(scholarship, reviewer_initials, wai_number)
    review_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.utcnow().isoformat() + "Z"
    data: Dict[str, Any] = {
        "scholarship": scholarship,
        "wai_number": wai_number,
        "reviewer_username": reviewer_username,
        "reviewer_initials": reviewer_initials,
        "score": score,
        "comments": comments,
        "created_at": now,
        "updated_at": now,
    }

    if review_path.exists():
        try:
            with review_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            # Preserve original created_at if present
            if "created_at" in existing:
                data["created_at"] = existing["created_at"]
        except Exception as e:
            logger.warning(f"Failed to load existing review at {review_path}: {e}")

    try:
        with review_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(
            "Saved review for %s/%s by %s (%s) to %s",
            scholarship,
            wai_number,
            reviewer_username,
            reviewer_initials,
            review_path,
        )
    except Exception as e:
        logger.error(f"Failed to save review at {review_path}: {e}")
        raise

    return data


def list_reviews_for_reviewer(
    reviewer_username: str,
    reviewer_initials: str,
    scholarship: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all reviews for a given reviewer (optionally filtered by scholarship)."""
    base_dir = _get_reviews_base_dir()

    scholarships_to_check: List[str]
    if scholarship:
        scholarships_to_check = [scholarship]
    else:
        scholarships_to_check = get_user_scholarships(reviewer_username) or []

    reviews: List[Dict[str, Any]] = []

    for schol in scholarships_to_check:
        reviews_dir = base_dir / schol / "reviews" / reviewer_initials
        if not reviews_dir.exists():
            continue

        for file_path in reviews_dir.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Ensure scholarship is set correctly even if file was modified manually
                data.setdefault("scholarship", schol)
                reviews.append(data)
            except Exception as e:
                logger.warning(f"Failed to load review file {file_path}: {e}")

    # Sort reviews by updated_at descending if present
    reviews.sort(key=lambda r: r.get("updated_at", ""), reverse=True)
    return reviews


def load_all_reviews_for_scholarship(scholarship: str) -> List[Dict[str, Any]]:
    """Load all review JSON records for a given scholarship."""
    base_dir = _get_reviews_base_dir()
    reviews_root = base_dir / scholarship / "reviews"
    results: List[Dict[str, Any]] = []

    if not reviews_root.exists():
        logger.info("No reviews directory found for scholarship %s", scholarship)
        return results

    for reviewer_dir in reviews_root.iterdir():
        if not reviewer_dir.is_dir():
            continue
        for file_path in reviewer_dir.glob("*.json"):
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                # Ensure required fields are present
                if "wai_number" not in data:
                    logger.warning("Skipping review without wai_number: %s", file_path)
                    continue
                if "score" not in data:
                    logger.warning("Skipping review without score: %s", file_path)
                    continue
                # Backfill scholarship from path if missing
                data.setdefault("scholarship", scholarship)
                results.append(data)
            except Exception as e:
                logger.warning("Failed to load review file %s: %s", file_path, e)

    logger.info("Loaded %d reviews for scholarship %s", len(results), scholarship)
    return results


def generate_aggregate_reviews(
    scholarship: str,
    base_output_dir: Path | None = None,
) -> Tuple[Path, int, List[Dict[str, Any]]]:
    """Generate an aggregate summarizing all reviews for a scholarship.

    A CSV will also be written to:

        outputs/{Scholarship}/reviews/final_reviews_summary.csv

    The CSV includes, per applicant (WAI number):
      - wai_number
      - num_reviews
      - total_score (sum of all reviewer scores)
      - one column per reviewer (score_<initials>) containing that reviewer's score
    """
    if base_output_dir is None:
        base_output_dir = _get_reviews_base_dir() / scholarship

    all_reviews = load_all_reviews_for_scholarship(scholarship)
    if not all_reviews:
        raise ValueError(f"No reviews found for scholarship {scholarship}")

    # Aggregate scores per applicant and per reviewer
    applicant_map: Dict[str, Dict[str, Any]] = {}
    all_reviewer_initials: set[str] = set()

    for r in all_reviews:
        wai = str(r.get("wai_number"))
        try:
            score = int(r.get("score"))
        except Exception:
            logger.warning("Non-integer score in review for %s: %r", wai, r.get("score"))
            continue

        initials = r.get("reviewer_initials") or r.get("reviewer_username") or "unknown"
        initials = str(initials)
        all_reviewer_initials.add(initials)

        if wai not in applicant_map:
            applicant_map[wai] = {
                "wai_number": wai,
                "scores_by_reviewer": {},
            }

        applicant_map[wai]["scores_by_reviewer"][initials] = score

    # Build flattened rows and compute totals
    rows: List[Dict[str, Any]] = []
    for wai, data in applicant_map.items():
        scores_by_reviewer: Dict[str, int] = data.get("scores_by_reviewer", {})
        if not scores_by_reviewer:
            continue

        row: Dict[str, Any] = {
            "wai_number": wai,
            "num_reviews": len(scores_by_reviewer),
            "total_score": sum(scores_by_reviewer.values()),
        }

        for initials in all_reviewer_initials:
            key = f"score_{initials}"
            row[key] = scores_by_reviewer.get(initials)

        rows.append(row)

    # Sort by total_score descending, then by wai_number for stability
    rows.sort(key=lambda r: (r["total_score"], r["wai_number"]), reverse=True)

    reviews_dir = base_output_dir / "reviews"
    reviews_dir.mkdir(parents=True, exist_ok=True)
    csv_path = reviews_dir / "final_reviews_summary.csv"

    # Deterministic column order: base columns + per-reviewer score columns
    reviewer_columns = [f"score_{initials}" for initials in sorted(all_reviewer_initials)]
    fieldnames = ["wai_number", "num_reviews", "total_score"] + reviewer_columns

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    logger.info(
        "Generated final reviews CSV for %s at %s (rows=%d)",
        scholarship,
        csv_path,
        len(rows),
    )

    # Return the path, row count, and the in-memory rows for callers that
    # want to return JSON as well as CSV.
    return csv_path, len(rows), rows


