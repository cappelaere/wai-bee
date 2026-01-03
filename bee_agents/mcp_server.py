"""MCP server entrypoint for running wai-bee as a Model Context Protocol server.

This module defines a FastMCP server that exposes a subset of the existing
API functionality (notably the reviewer scoring tools) over the MCP
HTTP streaming transport.

When the environment variable API_SERVER_MODE is set to "mcp", the main
API entrypoint will start this MCP server on the same host/port that the
FastAPI HTTP server normally uses.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

from .api_utils import get_data_service
from .review_service import (
    generate_final_reviews_csv,
    get_reviewer_initials,
    is_reviewer,
    list_reviews_for_reviewer,
    save_review,
)
from .auth import get_user_info, has_scholarship_access

logger = logging.getLogger(__name__)


# Create a single MCP server instance for the process.
mcp = FastMCP(name="wai-bee-mcp")


@mcp.tool
def submit_review_tool(
    scholarship: str,
    wai_number: str,
    username: str,
    score: int,
    comments: Optional[str] = None,
) -> Dict[str, Any]:
    """Submit or update a review for a specific applicant (MCP tool).

    This mirrors the behaviour of the HTTP POST /reviews endpoint but
    uses a simple username string for authentication/authorization,
    assuming the MCP host is already trusted.
    """
    if not is_reviewer(username):
        raise ValueError(f"User '{username}' is not configured as a reviewer")

    if not has_scholarship_access(username, scholarship):
        raise ValueError(
            f"User '{username}' does not have access to scholarship '{scholarship}'"
        )

    initials = get_reviewer_initials(username)
    if not initials:
        raise ValueError(f"Reviewer initials not configured for user '{username}'")

    try:
        review_data = save_review(
            scholarship=scholarship,
            wai_number=wai_number,
            reviewer_username=username,
            reviewer_initials=initials,
            score=score,
            comments=comments,
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception(
            "MCP: Failed to save review for %s/%s by %s", scholarship, wai_number, username
        )
        raise

    return review_data


@mcp.tool
def list_my_reviews_tool(
    username: str,
    scholarship: Optional[str] = None,
) -> Dict[str, Any]:
    """List all reviews submitted by the given reviewer (MCP tool).

    Mirrors GET /reviews/me. The caller passes the reviewer username
    directly; the tool resolves initials and permissions via user config.
    """
    if not is_reviewer(username):
        raise ValueError(f"User '{username}' is not configured as a reviewer")

    initials = get_reviewer_initials(username)
    if not initials:
        raise ValueError(f"Reviewer initials not configured for user '{username}'")

    if scholarship and not has_scholarship_access(username, scholarship):
        raise ValueError(
            f"User '{username}' does not have access to scholarship '{scholarship}'"
        )

    try:
        reviews = list_reviews_for_reviewer(
            reviewer_username=username,
            reviewer_initials=initials,
            scholarship=scholarship,
        )
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("MCP: Failed to list reviews for %s", username)
        raise

    return {
        "reviewer_username": username,
        "reviewer_initials": initials,
        "reviews": reviews,
    }


@mcp.tool
def final_reviews_summary_tool(
    scholarship: str,
) -> Dict[str, Any]:
    """Generate a final reviews summary for a scholarship (MCP tool).

    Mirrors the behaviour of the HTTP POST /reviews/final_csv endpoint,
    but returns only the JSON summary (not a CSV download URL).
    """
    try:
        csv_path, row_count, rows = generate_final_reviews_csv(scholarship)
    except ValueError as e:
        # No reviews found, propagate a clear error
        raise ValueError(str(e))
    except Exception as e:  # pragma: no cover - defensive logging
        logger.exception("MCP: Failed to generate final reviews CSV for %s", scholarship)
        raise

    return {
        "scholarship": scholarship,
        "csv_file": str(csv_path),
        "applicant_count": row_count,
        "applicants": rows,
    }


# ---------------------------------------------------------------------------
# Score and statistics tools (mirror /score, /top_scores, /statistics)
# ---------------------------------------------------------------------------


@mcp.tool
def get_score_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """Get score for a specific application (MCP tool).

    Mirrors the behaviour of GET /score.
    """
    data_service = get_data_service(scholarship)

    all_scores = data_service.get_all_scores()
    score = next((s for s in all_scores if s.get("wai_number") == wai_number), None)
    if not score:
        raise ValueError(f"Score for application {wai_number} not found")

    return score


@mcp.tool
def get_top_scores_tool(
    scholarship: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """Get top scoring applications (MCP tool).

    Mirrors the behaviour of GET /top_scores.
    """
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    data_service = get_data_service(scholarship)

    top_scores = data_service.get_top_scores(limit)
    all_scores = data_service.get_all_scores()
    total_applications = len(all_scores)

    return {
        "scholarship": scholarship,
        "total_applications": total_applications,
        "top_scores": top_scores,
    }


@mcp.tool
def get_statistics_tool(
    scholarship: str,
) -> Dict[str, Any]:
    """Get aggregated statistics for all applications (MCP tool).

    Mirrors the behaviour of GET /statistics.
    """
    data_service = get_data_service(scholarship)

    stats = data_service.get_statistics()
    if not stats:
        raise ValueError(f"No statistics available for {scholarship}")

    stats = dict(stats)
    stats["scholarship"] = scholarship
    return stats


# ---------------------------------------------------------------------------
# Analysis tools (mirror /application, /academic, /essay, /recommendation)
# ---------------------------------------------------------------------------


@mcp.tool
def get_application_analysis_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """Get detailed application analysis (MCP tool)."""
    data_service = get_data_service(scholarship)
    analysis = data_service.load_application_analysis(wai_number)
    if not analysis:
        raise ValueError(f"Application {wai_number} not found")
    return analysis


@mcp.tool
def get_academic_analysis_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """Get academic analysis for an application (MCP tool)."""
    data_service = get_data_service(scholarship)
    analysis = data_service.load_resume_analysis(wai_number)
    if not analysis:
        raise ValueError(f"Academic analysis for {wai_number} not found")
    return analysis


@mcp.tool
def get_combined_essay_analysis_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """Get combined essay analysis for an application (MCP tool)."""
    data_service = get_data_service(scholarship)
    combined = data_service.load_combined_essay_analysis(wai_number)
    if not combined:
        raise ValueError(f"No essay analyses found for {wai_number}")
    return combined


@mcp.tool
def get_single_essay_analysis_tool(
    scholarship: str,
    wai_number: str,
    essay_number: int,
) -> Dict[str, Any]:
    """Get analysis for a specific essay (MCP tool)."""
    if essay_number not in (1, 2):
        raise ValueError("essay_number must be 1 or 2")

    data_service = get_data_service(scholarship)
    analysis = data_service.load_essay_analysis(wai_number, essay_number)
    if not analysis:
        raise ValueError(f"Essay {essay_number} analysis for {wai_number} not found")
    return analysis


@mcp.tool
def get_combined_recommendation_analysis_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """Get combined recommendation analysis for an application (MCP tool)."""
    data_service = get_data_service(scholarship)
    combined = data_service.load_combined_recommendation_analysis(wai_number)
    if not combined:
        raise ValueError(f"No recommendation analyses found for {wai_number}")
    return combined


@mcp.tool
def get_single_recommendation_analysis_tool(
    scholarship: str,
    wai_number: str,
    rec_number: int,
) -> Dict[str, Any]:
    """Get analysis for a specific recommendation (MCP tool)."""
    if rec_number not in (1, 2):
        raise ValueError("rec_number must be 1 or 2")

    data_service = get_data_service(scholarship)
    analysis = data_service.load_recommendation_analysis(wai_number, rec_number)
    if not analysis:
        raise ValueError(
            f"Recommendation {rec_number} analysis for {wai_number} not found"
        )
    return analysis


# ---------------------------------------------------------------------------
# Criteria tools (mirror /criteria and /criteria/by-type)
# ---------------------------------------------------------------------------


@mcp.tool
def list_criteria_tool(
    scholarship: str,
) -> Dict[str, Any]:
    """List all available evaluation criteria files for a scholarship (MCP tool)."""
    # Validate scholarship exists
    get_data_service(scholarship)

    criteria_dir = Path("data") / scholarship / "criteria"
    if not criteria_dir.exists():
        raise ValueError(f"No criteria found for scholarship: {scholarship}")

    criteria_files: List[Dict[str, Any]] = []
    for file_path in sorted(criteria_dir.glob("*.txt")):
        criteria_name = file_path.stem
        criteria_files.append(
            {
                "name": criteria_name,
                "filename": file_path.name,
            }
        )

    return {
        "scholarship": scholarship,
        "criteria_count": len(criteria_files),
        "criteria": criteria_files,
    }


@mcp.tool
def get_criteria_by_type_tool(
    criteria_type: str,
    scholarship: str,
) -> Dict[str, Any]:
    """Get full evaluation criteria text for a specific criteria type (MCP tool)."""
    # Validate scholarship
    get_data_service(scholarship)

    valid_types = ["application", "academic", "essay", "recommendation", "social"]
    if criteria_type not in valid_types:
        raise ValueError(
            f"Invalid criteria type '{criteria_type}'. "
            f"Must be one of: {', '.join(valid_types)}."
        )

    filename = f"{criteria_type}_criteria.txt"
    criteria_path = Path("data") / scholarship / "criteria" / filename
    if not criteria_path.exists():
        raise ValueError(
            f"{criteria_type.title()} criteria not found for scholarship {scholarship}"
        )

    content = criteria_path.read_text(encoding="utf-8")
    line_count = len(content.splitlines())
    return {
        "scholarship": scholarship,
        "criteria_type": criteria_type,
        "filename": filename,
        "content": content,
        "line_count": line_count,
    }


# ---------------------------------------------------------------------------
# Attachment tools (mirror /attachments and /attachments/text)
# ---------------------------------------------------------------------------


@mcp.tool
def list_attachments_tool(
    scholarship: str,
    wai_number: str,
) -> Dict[str, Any]:
    """List all attachment files for an application (MCP tool)."""
    data_service = get_data_service(scholarship)
    result = data_service.list_attachments(wai_number)

    files = result.get("files") or []
    if not files:
        raise ValueError(f"No attachments found for {wai_number}")

    return {
        "wai_number": wai_number,
        "count": len(files),
        "files": files,
        "processing_summary": result.get("processing_summary"),
    }


@mcp.tool
def get_text_attachment_tool(
    scholarship: str,
    wai_number: str,
    filename: str,
) -> Dict[str, Any]:
    """Get the raw text content of a processed attachment (MCP tool).

    Mirrors the filesystem access pattern of GET /attachments/text, but
    returns structured data instead of HTML.
    """
    # Validate scholarship exists (for consistency)
    get_data_service(scholarship)

    file_path = Path("outputs") / scholarship / wai_number / "attachments" / filename
    if not file_path.exists() or file_path.suffix.lower() != ".txt":
        raise ValueError(f"Text file {filename} not found for {wai_number}")

    content = file_path.read_text(encoding="utf-8")
    file_size = file_path.stat().st_size

    return {
        "scholarship": scholarship,
        "wai_number": wai_number,
        "filename": filename,
        "size_bytes": file_size,
        "content": content,
    }


# ---------------------------------------------------------------------------
# Configuration tools (mirror /agents/by-name)
# ---------------------------------------------------------------------------


@mcp.tool
def get_agent_config_tool(
    agent_name: str,
    scholarship: str,
) -> Dict[str, Any]:
    """Get configuration for a specific agent (MCP tool).

    Mirrors the behaviour of GET /agents/by-name.
    """
    from .api_utils import get_data_service  # local import to avoid cycles
    import json

    data_service = get_data_service(scholarship)
    agents_file = Path("data") / data_service.scholarship_name / "agents.json"
    if not agents_file.exists():
        raise ValueError(
            f"Agent configuration not found for {data_service.scholarship_name}"
        )

    config = json.loads(agents_file.read_text(encoding="utf-8"))
    agent = None
    for a in config.get("agents", []):
        if a.get("name") == agent_name:
            agent = a
            break

    if not agent:
        raise ValueError(
            f"Agent '{agent_name}' not found in configuration for {data_service.scholarship_name}"
        )

    return {
        "scholarship": data_service.scholarship_name,
        "agent": agent,
    }


def run_mcp_http_server(host: str, port: int) -> None:
    """Run the FastMCP server using the HTTP streaming transport.

    The server will listen on the same host/port that the HTTP API would
    normally use, exposing the tools defined above at the /mcp endpoint.
    """
    logger.info(
        "Starting MCP server (HTTP streaming) on %s:%s at path /mcp",
        host,
        port,
    )

    # `transport="http"` selects the Streamable HTTP transport.
    mcp.run(
        transport="http",
        host=host,
        port=port,
        path="/mcp",
    )


