"""Generic schema-driven scoring runner.

This runner executes the scholarship scoring agents (application, resume, essay,
recommendation) purely from generated scholarship artifacts:

- WAI-general-2025/config/<scholarship>/agents.json
- WAI-general-2025/config/<scholarship>/prompts/*.txt
- WAI-general-2025/config/<scholarship>/schemas_generated/*.schema.json

It intentionally does NOT handle preprocessing (attachment) agents.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from litellm import completion

from models.application_data import ApplicationData
from utils.attachment_finder import find_input_files_for_agent
from utils.llm_config import configure_litellm
from utils.llm_repair import llm_repair_json, validate_and_repair_once
from utils.prompt_loader import load_analysis_prompt, load_repair_prompt, load_schema_path
from utils.schema_validator import extract_json_from_text, load_schema

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScoringResult:
    agent: str
    success: bool
    output_path: Optional[Path] = None
    error: Optional[str] = None


class ScoringRunner:
    """Run all scoring agents for a scholarship in a config-driven way."""

    def __init__(self, scholarship_folder: Path, outputs_dir: Path = Path("outputs")):
        configure_litellm()
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        self.outputs_dir = outputs_dir

        agents_file = scholarship_folder / "agents.json"
        if not agents_file.exists():
            raise FileNotFoundError(f"agents.json not found: {agents_file}")

        try:
            self._agents_cfg = json.loads(agents_file.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"Failed to parse {agents_file}: {e}") from e

        self.scoring_agents: list[str] = list(self._agents_cfg.get("scoring_agents") or [])
        if not self.scoring_agents:
            raise ValueError(f"No scoring_agents configured in {agents_file}")

    def run_for_wai(
        self,
        wai_number: str,
        model: str,
        fallback_model: Optional[str] = None,
        max_retries: int = 3,
    ) -> dict[str, ScoringResult]:
        """Run all configured scoring agents for a single applicant."""
        return self.run_agents_for_wai(
            wai_number=wai_number,
            agents=self.scoring_agents,
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
        )

    def run_agent_for_wai(
        self,
        *,
        wai_number: str,
        agent: str,
        model: str,
        fallback_model: Optional[str] = None,
        max_retries: int = 3,
    ) -> ScoringResult:
        """Run a single scoring agent for a single applicant."""
        if agent not in self.scoring_agents:
            return ScoringResult(
                agent=agent,
                success=False,
                error=f"agent '{agent}' is not a configured scoring agent: {self.scoring_agents}",
            )
        return self._run_single_agent_for_wai(
            agent_name=agent,
            wai_number=wai_number,
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
        )

    def run_agents_for_wai(
        self,
        *,
        wai_number: str,
        agents: list[str],
        model: str,
        fallback_model: Optional[str] = None,
        max_retries: int = 3,
    ) -> dict[str, ScoringResult]:
        """Run an explicit subset of scoring agents for a single applicant."""
        results: dict[str, ScoringResult] = {}
        for agent_name in agents:
            results[agent_name] = self.run_agent_for_wai(
                wai_number=wai_number,
                agent=agent_name,
                model=model,
                fallback_model=fallback_model,
                max_retries=max_retries,
            )
        return results

    def _run_single_agent_for_wai(
        self,
        *,
        agent_name: str,
        wai_number: str,
        model: str,
        fallback_model: Optional[str],
        max_retries: int,
    ) -> ScoringResult:
        try:
            analysis_prompt = load_analysis_prompt(self.scholarship_folder, agent_name)
            if not analysis_prompt:
                return ScoringResult(agent=agent_name, success=False, error="analysis_prompt not found")

            repair_template = load_repair_prompt(self.scholarship_folder, agent_name)

            schema_path = load_schema_path(self.scholarship_folder, agent_name)
            if not schema_path:
                return ScoringResult(agent=agent_name, success=False, error="schema path not configured")
            if not schema_path.exists():
                return ScoringResult(agent=agent_name, success=False, error=f"schema file not found: {schema_path}")
            schema = load_schema(schema_path)

            artifact_text = self._build_artifact_text(agent_name, wai_number)
            if artifact_text is None:
                return ScoringResult(agent=agent_name, success=False, error="artifact content not found")

            user_prompt = f"{analysis_prompt}\n\n---\n\n## Artifact Content\n\n{artifact_text}"

            last_errors: list[str] = []
            for attempt in range(1, max_retries + 1):
                current_model = model if attempt == 1 else (fallback_model or model)
                logger.info(f"[{wai_number}] {agent_name}: attempt {attempt}/{max_retries} ({current_model})")

                resp = completion(
                    model=current_model,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=0.1,
                )
                response_text = resp.choices[0].message.content or ""

                extracted = extract_json_from_text(response_text)

                if extracted is None:
                    # If we have a repair template, attempt one repair pass using raw response
                    if repair_template:
                        repaired = llm_repair_json(
                            repair_template=repair_template,
                            invalid_json={"raw_response": response_text},
                            validation_errors=["root: Could not extract valid JSON from LLM response"],
                            model=current_model,
                            system_prompt=None,
                            max_tokens=3000,
                        )
                        if repaired is not None:
                            is_valid, fixed, errors = validate_and_repair_once(
                                data=repaired,
                                schema=schema,
                                repair_template=None,
                                model=current_model,
                                system_prompt=None,
                                local_fix_attempts=3,
                                repair_max_tokens=3000,
                            )
                            if is_valid:
                                out_path = self._write_agent_output(agent_name, wai_number, fixed)
                                return ScoringResult(agent=agent_name, success=True, output_path=out_path)
                            last_errors = errors
                    else:
                        last_errors = ["root: Could not extract valid JSON from LLM response"]
                    continue

                is_valid, fixed, errors = validate_and_repair_once(
                    data=extracted,
                    schema=schema,
                    repair_template=repair_template,
                    model=current_model,
                    system_prompt=None,
                    local_fix_attempts=3,
                    repair_max_tokens=3000,
                )
                if is_valid:
                    out_path = self._write_agent_output(agent_name, wai_number, fixed)
                    return ScoringResult(agent=agent_name, success=True, output_path=out_path)

                last_errors = errors

            return ScoringResult(
                agent=agent_name,
                success=False,
                error=f"failed after {max_retries} attempts: {last_errors[:5]}",
            )

        except Exception as e:
            logger.exception(f"[{wai_number}] {agent_name}: unexpected error")
            return ScoringResult(agent=agent_name, success=False, error=str(e))

    def _build_artifact_text(self, agent_name: str, wai_number: str) -> Optional[str]:
        """Build the raw content that will be appended to the analysis prompt."""
        if agent_name == "application":
            app_data_path = self.outputs_dir / self.scholarship_name / wai_number / "application_data.json"
            if not app_data_path.exists():
                return None
            app_obj = ApplicationData(**json.loads(app_data_path.read_text(encoding="utf-8")))

            attachment_files = [
                f.get("name")
                for f in (app_obj.attachment_files_checked or [])
                if isinstance(f, dict) and f.get("valid", False) and f.get("name")
            ]
            attachment_list = "\n".join(f"- {name}" for name in attachment_files) if attachment_files else "- None"
            state_display = app_obj.state if app_obj.state else "N/A (non-US applicant)"

            return (
                "APPLICATION DATA (extracted):\n"
                f"- wai_number: {app_obj.wai_number}\n"
                f"- name: {app_obj.name}\n"
                f"- city: {app_obj.city}\n"
                f"- state: {state_display}\n"
                f"- country: {app_obj.country}\n\n"
                "ATTACHMENT FILES CHECKED (valid only):\n"
                f"{attachment_list}\n"
            )

        # For text artifacts, use config-driven attachment files (outputs/<scholarship>/<wai>/attachments/*.txt)
        files = find_input_files_for_agent(self.scholarship_folder, agent_name, wai_number, self.outputs_dir)
        if not files:
            return None

        parts: list[str] = []
        for idx, p in enumerate(files, start=1):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except Exception:
                logger.exception(f"Failed reading artifact file: {p}")
                text = ""

            parts.append(f"--- File {idx}: {p.name} ---\n{text}\n")

        return "\n".join(parts).strip()

    def _compute_overall_score(self, payload: dict) -> int:
        """Compute overall score as sum of all facet scores.
        
        Args:
            payload: The analysis payload with facets.
            
        Returns:
            Sum of all facet scores, or 0 if no facets.
        """
        facets = payload.get("facets", [])
        if not facets:
            return 0
        
        total = 0
        for facet in facets:
            if isinstance(facet, dict) and "score" in facet:
                try:
                    total += int(facet["score"])
                except (ValueError, TypeError):
                    pass
        return total

    def _get_agent_weight(self, agent_name: str) -> float:
        """Get the weight for an agent from the config.
        
        Args:
            agent_name: Name of the agent.
            
        Returns:
            Weight as a float (0.0-1.0), or 0.0 if not found.
        """
        for agent in self._agents_cfg.get("agents", []):
            if agent.get("name") == agent_name:
                weight = agent.get("weight")
                if weight is not None:
                    return float(weight)
        return 0.0

    def _write_agent_output(self, agent_name: str, wai_number: str, payload: dict) -> Path:
        """Write agent output to the canonical outputs/<scholarship>/<wai>/ file path.

        We intentionally keep these paths stable for API/score loaders.
        Automatically computes and adds overall_score and weighted_score.
        """
        wai_dir = self.outputs_dir / self.scholarship_name / wai_number
        wai_dir.mkdir(parents=True, exist_ok=True)

        # Compute overall_score (sum of facets)
        overall_score = self._compute_overall_score(payload)
        payload["overall_score"] = overall_score
        
        # Compute weighted_score (overall_score × agent weight)
        weight = self._get_agent_weight(agent_name)
        payload["weight"] = weight
        payload["weighted_score"] = round(overall_score * weight, 2)

        filename = {
            "application": "application_analysis.json",
            "resume": "resume_analysis.json",
            "essay": "essay_analysis.json",
            "recommendation": "recommendation_analysis.json",
        }.get(agent_name, f"{agent_name}_analysis.json")

        out_path = wai_dir / filename
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return out_path


