"""Reviewer scoring endpoints.

These endpoints allow authenticated reviewers to submit 1–10 scores for
specific applicants and list their own reviews. Reviews are stored as JSON
files under:

    outputs/{Scholarship}/reviews/{initials}/{wai_number}.json
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Form, Request
from fastapi.responses import FileResponse

from ..auth import (
    verify_token_with_context,
    get_user_info,
    has_scholarship_access,
)
from ..models import ReviewCreateRequest, ReviewResponse, ReviewListResponse
from ..review_service import (
    is_reviewer,
    get_reviewer_initials,
    save_review,
    list_reviews_for_reviewer,
    generate_final_reviews_csv,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Reviews"])


def _get_public_base_url(_: Request) -> str:
    """Return the public API base URL from the environment.

    Uses the API_SERVER_URL environment variable, which should be a fully
    qualified base URL such as:

        https://wai.example.com/api
    """
    base = os.getenv("API_SERVER_URL", "").strip()
    return base.rstrip("/")


def _extract_token_from_authorization_header(authorization: Optional[str]) -> Optional[str]:
    """Extract bearer token from Authorization header if present."""
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    # Fallback: treat entire header as token
    return authorization.strip() or None


async def get_current_reviewer(
    authorization: Optional[str] = Header(
        None,
        description="Bearer authentication token issued by chat auth service",
    ),
    token_query: Optional[str] = Query(
        None,
        description="Optional authentication token passed as a query parameter "
        "(used when the client cannot set Authorization headers).",
    ),
) -> dict:
    """Dependency that returns the current reviewer context.

    Requires a valid token and a user marked with `reviewer: true`
    in config/users.json. Also attaches reviewer initials.
    """
    # Prefer Authorization header; fall back to explicit token query parameter.
    token = _extract_token_from_authorization_header(authorization) or (token_query or "").strip()

    # Debug logging to help trace 401 issues (without leaking full tokens)
    if not token:
        logger.warning("get_current_reviewer: missing token (no Authorization header and no token query param)")
    else:
        logger.debug("get_current_reviewer: received token prefix=%s...", token[:8])

    token_data = verify_token_with_context(token)
    if not token_data:
        logger.warning("get_current_reviewer: token verification failed")
        raise HTTPException(status_code=401, detail="Invalid or missing authentication token")

    username = token_data.get("username")
    if not username:
        raise HTTPException(status_code=401, detail="Token missing username context")

    if not is_reviewer(username):
        raise HTTPException(status_code=403, detail="User is not authorized as a reviewer")

    initials = get_reviewer_initials(username)
    if not initials:
        raise HTTPException(status_code=400, detail="Reviewer initials not configured for user")

    user_info = get_user_info(username) or {}

    return {
        "username": username,
        "initials": initials,
        "role": token_data.get("role"),
        "scholarships": token_data.get("scholarships") or user_info.get("scholarships", []),
        "permissions": token_data.get("permissions") or user_info.get("permissions", []),
    }


@router.post(
    "/reviews",
    response_model=ReviewResponse,
    operation_id="submit_review",
)
async def submit_review(
    scholarship: str = Query(..., description="Scholarship identifier (e.g., 'Delaney_Wings')"),
    wai_number: str = Query(..., description="WAI application number"),
    score: int = Form(..., description="Reviewer score from 1 (lowest) to 10 (highest)"),
    comments: Optional[str] = Form(None, description="Optional free-text review comments"),
    reviewer: dict = Depends(get_current_reviewer),
):
    """Submit or update a review for a specific applicant.

    The caller must be an authenticated reviewer with access to the
    specified scholarship. Scholarship and WAI number are provided as
    query parameters. Subsequent calls for the same (reviewer, WAI)
    will overwrite the existing review file, preserving the original
    `created_at` timestamp.
    """
    username = reviewer["username"]
    initials = reviewer["initials"]

    if not has_scholarship_access(username, scholarship):
        raise HTTPException(
            status_code=403,
            detail=f"User '{username}' does not have access to scholarship '{scholarship}'",
        )

    # Optionally, verify the applicant directory exists under outputs
    applicant_dir = (
        (  # lazy import to avoid circular
            __import__("pathlib").Path("outputs") / scholarship / wai_number
        )
    )
    if not applicant_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Applicant {wai_number} not found for scholarship {scholarship}",
        )

    try:
        review_data = save_review(
            scholarship=scholarship,
            wai_number=wai_number,
            reviewer_username=username,
            reviewer_initials=initials,
            score=score,
            comments=comments,
        )
    except Exception as e:
        logger.exception(
            "Failed to save review for %s/%s by %s", scholarship, wai_number, username
        )
        raise HTTPException(status_code=500, detail=f"Failed to save review: {e}")

    return ReviewResponse(**review_data)


@router.get(
    "/reviews/me",
    response_model=ReviewListResponse,
    operation_id="list_my_reviews",
)
async def list_my_reviews(
    scholarship: Optional[str] = Query(
        None,
        description="Optional scholarship filter (e.g., 'Delaney_Wings')",
    ),
    reviewer: dict = Depends(get_current_reviewer),
):
    """List all reviews submitted by the current reviewer.

    If a scholarship is provided, only reviews for that scholarship are returned.
    Otherwise, reviews are returned for all scholarships the reviewer has access to.
    """
    username = reviewer["username"]
    initials = reviewer["initials"]

    if scholarship and not has_scholarship_access(username, scholarship):
        raise HTTPException(
            status_code=403,
            detail=f"User '{username}' does not have access to scholarship '{scholarship}'",
        )

    try:
        reviews = list_reviews_for_reviewer(
            reviewer_username=username,
            reviewer_initials=initials,
            scholarship=scholarship,
        )
    except Exception as e:
        logger.exception("Failed to list reviews for %s", username)
        raise HTTPException(status_code=500, detail=f"Failed to list reviews: {e}")

    return ReviewListResponse(
        reviewer_username=username,
        reviewer_initials=initials,
        reviews=reviews,
    )


@router.post(
    "/reviews/final_csv",
    operation_id="generate_final_reviews_csv",
    tags=["Reviews"],
)
async def generate_final_reviews_csv_endpoint(
    scholarship: str = Query(..., description="Scholarship identifier (e.g., 'Delaney_Wings')"),
    reviewer: dict = Depends(get_current_reviewer),
    request: Request = None,
):
    """Generate a CSV summarizing all reviewer scores for a scholarship.

    The CSV is written to:

        outputs/{Scholarship}/reviews/final_reviews_summary.csv

    Rows are sorted by `total_score` (sum of all reviewer scores) descending.
    """
    username = reviewer["username"]

    if not has_scholarship_access(username, scholarship):
        raise HTTPException(
            status_code=403,
            detail=f"User '{username}' does not have access to scholarship '{scholarship}'",
        )

    try:
        csv_path, row_count, rows = generate_final_reviews_csv(scholarship)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate final reviews CSV for %s", scholarship)
        raise HTTPException(status_code=500, detail=f"Failed to generate final reviews CSV: {e}")

    csv_download_url = None
    if request is not None:
        base_url = _get_public_base_url(request)
        csv_download_url = f"{base_url}/reviews/final_csv_file?scholarship={scholarship}"

    response_payload = {
        "scholarship": scholarship,
        "csv_file": str(csv_path),
        "applicant_count": row_count,
        "applicants": rows,
    }

    # Include a direct HTTP link to download the CSV when we have a request context
    if csv_download_url:
        response_payload["csv_download_url"] = csv_download_url

    return response_payload


@router.get(
    "/reviews/final_csv_file",
    operation_id="download_final_reviews_csv",
    tags=["Reviews"],
)
async def download_final_reviews_csv(
    scholarship: str = Query(..., description="Scholarship identifier (e.g., 'Delaney_Wings')"),
):
    """Download the final reviews CSV file for a scholarship.

    This endpoint returns the generated CSV as a file response so clients
    can download it directly (e.g., from a browser or via curl).
    """
    try:
        csv_path, _, _ = generate_final_reviews_csv(scholarship)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception("Failed to generate final reviews CSV for %s", scholarship)
        raise HTTPException(status_code=500, detail=f"Failed to generate final reviews CSV: {e}")

    return FileResponse(
        path=csv_path,
        media_type="text/csv",
        filename=f"{scholarship}_final_reviews_summary.csv",
    )


