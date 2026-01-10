"""Scholarship Application Processing Workflow.

This workflow orchestrates all agents to process scholarship applications
from start to finish in a coordinated manner.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 2.0.0 - Updated for WAI-general-2025 folder structure
License: MIT
"""

import logging
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from beeai_framework.errors import FrameworkError
from beeai_framework.workflows import Workflow

from agents.attachment_agent.agent import AttachmentAgent
from agents.application_agent.agent import ApplicationAgent
from agents.scoring_runner import ScoringRunner
from agents.summary_agent.agent import SummaryAgent
from utils.preflight_check import run_preflight_check, PreflightResult
from utils.config import config as global_config


class DefaultWorkflowSchema:
    """Default empty schema for workflow when none is provided."""
    pass


@dataclass
class StageResult:
    """Result from a processing stage."""
    stage_name: str
    success: bool
    message: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_seconds: float = 0.0


@dataclass
class ApplicantResult:
    """Complete processing result for an applicant."""
    wai_number: str
    success: bool
    stages: List[StageResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    
    def get_stage_result(self, stage_name: str) -> Optional[StageResult]:
        """Get result for a specific stage."""
        for stage in self.stages:
            if stage.stage_name == stage_name:
                return stage
        return None


class ScholarshipProcessingWorkflow(Workflow):
    """Workflow for processing scholarship applications.
    
    This workflow coordinates multiple specialized agents to process
    scholarship applications through all stages: attachment processing,
    application analysis, recommendation review, academic evaluation,
    essay analysis, and final summary generation.
    
    Inherits from beeai_framework.workflows.Workflow for standardized
    workflow management and error handling.
    
    Folder Structure (WAI-general-2025/):
        - data/{scholarship}/{WAI-ID}/     Application files (PDFs, etc.)
        - config/{scholarship}/            Config files (config.yml, agents.json, prompts/, schemas_generated/)
        - output/{scholarship}/{WAI-ID}/   Processing outputs (analysis JSON files)
        - logs/                            Processing logs
    
    Attributes:
        scholarship_name: Name of the scholarship.
        config_folder: Path to scholarship config folder.
        data_folder: Path to scholarship data folder.
        outputs_dir: Base outputs directory.
        logger: Logger instance.
    """
    
    def __init__(
        self,
        scholarship_folder: Path,
        outputs_dir: Optional[Path] = None,
        schema: Optional[type] = None
    ):
        """Initialize the workflow.
        
        Args:
            scholarship_folder: Path to scholarship config folder (e.g., WAI-general-2025/config/Delaney_Wings).
            outputs_dir: Base outputs directory. If None, uses global_config.OUTPUTS_DIR.
            schema: Optional workflow schema type/class for beeai-framework.
        """
        # Initialize parent Workflow class with schema (use default if not provided)
        super().__init__(schema=schema or DefaultWorkflowSchema)
        
        self.logger = logging.getLogger(__name__)
        
        # The scholarship_folder passed in is the CONFIG folder
        self.config_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        
        # Derive the data folder from global config
        self.data_folder = global_config.get_data_folder(self.scholarship_name)
        
        # Use provided outputs_dir or fall back to global config
        self.outputs_dir = outputs_dir if outputs_dir else global_config.OUTPUTS_DIR
        
        # For backwards compatibility, keep scholarship_folder pointing to config
        self.scholarship_folder = self.config_folder
        
        # Initialize all agents
        self._initialize_agents()
        
        self.logger.info(f"Initialized ScholarshipProcessingWorkflow for {self.scholarship_name}")
        self.logger.info(f"  Config folder: {self.config_folder}")
        self.logger.info(f"  Data folder: {self.data_folder}")
        self.logger.info(f"  Outputs folder: {self.outputs_dir / self.scholarship_name}")
    
    def _initialize_agents(self) -> None:
        """Initialize all processing agents."""
        # Preprocessing agents
        self.attachment_agent = AttachmentAgent()
        self.application_agent = ApplicationAgent(self.config_folder)

        # Scoring runner (application/resume/essay/recommendation)
        # Pass config folder - scoring runner will derive data paths from config
        self.scoring_runner = ScoringRunner(self.config_folder, self.outputs_dir)
        
        # Only SummaryAgent takes outputs_dir and scholarship_folder
        self.summary_agent = SummaryAgent(
            self.outputs_dir,
            self.config_folder
        )
    
    def _run_stage(
        self,
        stage_name: str,
        func,
        *args,
        **kwargs
    ) -> StageResult:
        """Run a processing stage with timing and error handling.
        
        Args:
            stage_name: Name of the stage.
            func: Function to execute.
            *args: Positional arguments for func.
            **kwargs: Keyword arguments for func.
            
        Returns:
            StageResult with execution details.
        """
        import time
        
        self.logger.info(f"Starting stage: {stage_name}")
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            # Treat "no result" or explicit failure booleans as stage failures.
            # Many of our agent entrypoints return Optional[...] or bool.
            if result is None:
                return StageResult(
                    stage_name=stage_name,
                    success=False,
                    message=f"{stage_name} returned no result",
                    error="Stage returned None",
                    duration_seconds=duration,
                )
            if isinstance(result, bool) and result is False:
                return StageResult(
                    stage_name=stage_name,
                    success=False,
                    message=f"{stage_name} reported failure",
                    error="Stage returned False",
                    duration_seconds=duration,
                )
            if isinstance(result, dict) and result.get("success") is False:
                return StageResult(
                    stage_name=stage_name,
                    success=False,
                    message=f"{stage_name} failed",
                    data=result,
                    error=str(result.get("error") or "Stage returned success=false"),
                    duration_seconds=duration,
                )
            
            return StageResult(
                stage_name=stage_name,
                success=True,
                message=f"{stage_name} completed successfully",
                data=result if isinstance(result, dict) else {"result": result},
                duration_seconds=duration
            )
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"{stage_name} failed: {e}")
            
            return StageResult(
                stage_name=stage_name,
                success=False,
                message=f"{stage_name} failed",
                error=str(e),
                duration_seconds=duration
            )
    
    def process_applicant(
        self,
        wai_number: str,
        skip_stages: Optional[List[str]] = None,
        parallel: bool = True,
        model: str = "ollama/llama3.2:3b",
        fallback_model: Optional[str] = "ollama/llama3:latest",
        max_retries: int = 3,
    ) -> ApplicantResult:
        """Process a single applicant through all stages.
        
        The workflow executes in this order:
        1. Application Agent (extracts applicant info)
        2. Attachment Agent (processes and redacts PII)
        3. Parallel: Recommendations, Academic, Essays (run simultaneously after attachments complete)
        4. Summary (runs after all analysis complete)
        
        Args:
            wai_number: WAI application number.
            skip_stages: Optional list of stage names to skip.
            parallel: If True, run analysis stages in parallel (default: True).
            model: Primary LLM model to use (default: 'ollama/llama3.2:3b').
            fallback_model: Optional fallback LLM model (default: 'ollama/llama3:latest').
            max_retries: Maximum retry attempts for LLM calls (default: 3).
            
        Returns:
            ApplicantResult with all stage results.
        """
        import time
        
        self.logger.info("="*60)
        self.logger.info(f"Processing Applicant: {wai_number}")
        self.logger.info("="*60)
        
        skip_stages = skip_stages or []
        start_time = time.time()
        stages = []
        
        # Use data folder for attachment agent (where application files are)
        data_folder_str = str(self.data_folder)

        # Stage 1: Application extraction (must be first to extract applicant info)
        self.logger.info("Stage 1: Application extraction...")
        if "application_extract" not in skip_stages and "application" not in skip_stages:
            stage_result = self._run_stage(
                "application_extract",
                self.application_agent.analyze_application,
                wai_number,
                str(self.outputs_dir),
                model,
                fallback_model,
                max_retries,
            )
            stages.append(stage_result)
            
            # Stop if application stage failed (validation errors, etc.)
            if not stage_result.success:
                self.logger.error(f"Application stage failed for {wai_number}, stopping workflow")
                total_duration = time.time() - start_time
                return ApplicantResult(
                    wai_number=wai_number,
                    success=False,
                    stages=stages,
                    total_duration_seconds=total_duration
                )
        
        # Stage 2: Process attachments (after application analysis)
        self.logger.info("Stage 2: Attachment processing...")
        if "attachments" not in skip_stages:
            stage_result = self._run_stage(
                "attachments",
                self.attachment_agent.process_single_wai,
                wai_number,
                data_folder_str,  # Use data folder for input files
                str(self.outputs_dir),
                model,
                fallback_model,
            )
            stages.append(stage_result)
        
        # Stage 3: Scoring (after attachments complete)
        self.logger.info("Stage 3: Scoring (Application, Resume, Essay, Recommendation)...")
        if "scoring" not in skip_stages:
            stage_result = self._run_stage(
                "scoring",
                self._run_scoring_stage,
                wai_number,
                model,
                fallback_model,
                max_retries,
            )
            stages.append(stage_result)
        
        total_duration = time.time() - start_time
        
        # Check if all stages succeeded
        all_success = all(stage.success for stage in stages)
        
        result = ApplicantResult(
            wai_number=wai_number,
            success=all_success,
            stages=stages,
            total_duration_seconds=total_duration
        )
        
        self.logger.info(f"Applicant {wai_number} processing complete in {total_duration:.2f}s")
        self.logger.info(f"Success: {all_success}")
        
        return result

    def _run_scoring_stage(
        self,
        wai_number: str,
        model: str,
        fallback_model: Optional[str],
        max_retries: int,
    ) -> Dict[str, Any]:
        """Run all scoring agents for a single applicant via ScoringRunner."""
        results = self.scoring_runner.run_for_wai(
            wai_number=wai_number,
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
        )

        # Convert dataclass results to plain dicts for JSON serialization
        out: Dict[str, Any] = {}
        for agent_name, res in results.items():
            out[agent_name] = {
                "success": res.success,
                "output_path": str(res.output_path) if res.output_path else None,
                "error": res.error,
            }
        return out
    
    def run_preflight_check(
        self,
        wai_numbers: Optional[List[str]] = None,
        max_applicants: Optional[int] = None,
        required_attachments: int = 5,
    ) -> PreflightResult:
        """Run preflight validation on applicant files before processing.
        
        Scans all applicant directories for:
        - Missing primary application files
        - Empty files (0 bytes)
        - Corrupted PDFs (invalid headers)
        
        Args:
            wai_numbers: Optional list of specific WAI numbers to check.
            max_applicants: Optional maximum number of applicants to check.
            required_attachments: Minimum attachment files expected (default: 5).
            
        Returns:
            PreflightResult with validation results.
        """
        self.logger.info("="*60)
        self.logger.info("Running Preflight Check")
        self.logger.info("="*60)
        
        # Preflight checks the DATA folder (where application files are)
        result = run_preflight_check(
            scholarship_folder=self.data_folder,
            wai_numbers=wai_numbers,
            max_applicants=max_applicants,
            required_attachments=required_attachments,
        )
        
        if result.has_errors:
            self.logger.error(f"Preflight check found {result.error_count} errors")
            for issue in result.issues:
                if issue.severity == "error":
                    self.logger.error(f"  {issue}")
        else:
            self.logger.info(f"Preflight check passed: {result.valid_applicants} valid applicants")
        
        return result
    
    def process_all_applicants(
        self,
        wai_numbers: Optional[List[str]] = None,
        skip_stages: Optional[List[str]] = None,
        max_applicants: Optional[int] = None,
        parallel: bool = True,
        stop_on_error: bool = False,
        model: str = "ollama/llama3.2:3b",
        fallback_model: Optional[str] = "ollama/llama3:latest",
        max_retries: int = 3,
        preflight: bool = False,
        preflight_strict: bool = False,
    ) -> Dict[str, Any]:
        """Process all applicants for the scholarship.
        
        Args:
            wai_numbers: Optional list of WAI numbers. If None, processes all found.
            skip_stages: Optional list of stage names to skip.
            max_applicants: Optional maximum number of applicants to process.
            parallel: If True, run analysis stages in parallel (default: True).
            stop_on_error: If True, stop processing when an applicant fails (default: False).
            model: Primary LLM model to use (default: 'ollama/llama3.2:3b').
            fallback_model: Optional fallback LLM model (default: 'ollama/llama3:latest').
            max_retries: Maximum retry attempts for LLM calls (default: 3).
            preflight: If True, run preflight validation before processing (default: False).
            preflight_strict: If True with preflight, abort if any errors found (default: False).
            
        Returns:
            Overall processing results dictionary.
        """
        import time
        
        self.logger.info("="*60)
        self.logger.info(f"Processing All Applicants: {self.scholarship_name}")
        self.logger.info("="*60)
        
        start_time = time.time()
        
        # Get list of applicants if not provided
        if wai_numbers is None:
            wai_numbers = self._discover_applicants()
        
        if max_applicants:
            wai_numbers = wai_numbers[:max_applicants]
        
        self.logger.info(f"Found {len(wai_numbers)} applicants to process")
        
        # Run preflight check if requested
        preflight_result = None
        if preflight:
            preflight_result = self.run_preflight_check(
                wai_numbers=wai_numbers,
                max_applicants=None,  # Already limited above
            )
            
            if preflight_result.has_errors:
                if preflight_strict:
                    self.logger.error("Preflight check failed in strict mode - aborting")
                    return {
                        "scholarship": self.scholarship_name,
                        "start_time": datetime.now().isoformat(),
                        "total_applicants": len(wai_numbers),
                        "applicants": [],
                        "successful": 0,
                        "failed": 0,
                        "aborted": True,
                        "abort_reason": "Preflight check failed (strict mode)",
                        "preflight": {
                            "errors": preflight_result.error_count,
                            "warnings": preflight_result.warning_count,
                            "invalid_applicants": preflight_result.get_invalid_wai_numbers(),
                        },
                        "duration_seconds": time.time() - start_time,
                    }
                else:
                    # Filter out invalid applicants
                    invalid_wais = set(preflight_result.get_invalid_wai_numbers())
                    original_count = len(wai_numbers)
                    wai_numbers = [w for w in wai_numbers if w not in invalid_wais]
                    self.logger.warning(
                        f"Skipping {original_count - len(wai_numbers)} applicants with file errors"
                    )
        
        # Process each applicant
        results = {
            "scholarship": self.scholarship_name,
            "start_time": datetime.now().isoformat(),
            "total_applicants": len(wai_numbers),
            "applicants": [],
            "successful": 0,
            "failed": 0,
            "skipped_stages": skip_stages or []
        }
        
        for i, wai_number in enumerate(wai_numbers, 1):
            self.logger.info(f"\nProcessing {i}/{len(wai_numbers)}: {wai_number}")
            
            applicant_result = self.process_applicant(
                wai_number=wai_number,
                skip_stages=skip_stages,
                parallel=parallel,
                model=model,
                fallback_model=fallback_model,
                max_retries=max_retries,
            )
            results["applicants"].append(applicant_result)
            
            if applicant_result.success:
                results["successful"] += 1
            else:
                results["failed"] += 1
                
                # Stop processing if stop_on_error is True
                if stop_on_error:
                    self.logger.error(f"Stopping processing due to error with applicant {wai_number}")
                    results["stopped_early"] = True
                    results["stopped_at"] = wai_number
                    break
        
        # Generate summary (if not skipped)
        if "summary" not in (skip_stages or []):
            self.logger.info("\n" + "="*60)
            self.logger.info("Generating Final Summary")
            self.logger.info("="*60)
            
            summary_result = self._generate_summary(wai_numbers)
            results["summary"] = summary_result
        
        total_duration = time.time() - start_time
        results["total_duration_seconds"] = total_duration
        results["end_time"] = datetime.now().isoformat()
        results["success"] = results["failed"] == 0
        
        self.logger.info("\n" + "="*60)
        self.logger.info("Workflow Complete")
        self.logger.info("="*60)
        self.logger.info(f"Total time: {total_duration:.2f}s")
        self.logger.info(f"Successful: {results['successful']}/{results['total_applicants']}")
        self.logger.info(f"Failed: {results['failed']}/{results['total_applicants']}")
        
        return results
    
    def _discover_applicants(self) -> List[str]:
        """Discover all applicant WAI numbers in the data folder.
        
        Returns:
            List of WAI numbers.
        """
        # Data folder contains WAI ID folders directly (no Applications subfolder)
        if self.data_folder.exists() and self.data_folder.is_dir():
            wai_numbers = [
                d.name
                for d in self.data_folder.iterdir()
                if d.is_dir() and not d.name.startswith('.')
            ]
            self.logger.info(f"Found {len(wai_numbers)} applicants in {self.data_folder}")

            # Sort WAI numbers numerically when possible so that, for example,
            # 58320 and 70015 come before 100439 and 101866, instead of using
            # plain string (lexicographic) ordering.
            def sort_key(name: str):
                try:
                    return int(name)
                except ValueError:
                    # Fall back to string ordering for any non-numeric names
                    return name

            return sorted(wai_numbers, key=sort_key)
        
        self.logger.warning(f"Data folder not found: {self.data_folder}")
        return []
    
    def _generate_summary(self, wai_numbers: List[str]) -> Dict[str, Any]:
        """Generate final summary and statistics.
        
        Args:
            wai_numbers: List of WAI numbers to summarize.
            
        Returns:
            Summary result dictionary.
        """
        try:
            # Generate summary CSV and statistics in scholarship folder
            scholarship_dir = self.outputs_dir / self.scholarship_name
            csv_file = scholarship_dir / "summary.csv"
            stats_file = scholarship_dir / "statistics.txt"

            stats = self.summary_agent.generate_summary_csv(csv_file, wai_numbers)
            
            # Only generate statistics report if we have data
            if stats and 'final_score_stats' in stats:
                self.summary_agent.generate_statistics_report(stats, stats_file)
            else:
                self.logger.warning("No applicant data available for statistics report")
            
            return {
                "success": True,
                "total_applicants": stats.get('total_applicants', 0),
                "complete_applications": stats.get('complete_applications', 0),
                "csv_file": str(csv_file),
                "stats_file": str(stats_file) if stats else None
            }
        except Exception as e:
            self.logger.error(f"Summary generation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow configuration and status.
        
        Returns:
            Status dictionary.
        """
        return {
            "scholarship": self.scholarship_name,
            "config_folder": str(self.config_folder),
            "data_folder": str(self.data_folder),
            "outputs_dir": str(self.outputs_dir),
            "agents": {
                "attachment": "AttachmentAgent",
                "application_extract": "ApplicationAgent",
                "scoring": "ScoringRunner",
                "summary": "SummaryAgent"
            },
            "available_stages": [
                "attachments",
                "application_extract",
                "scoring",
                "summary"
            ]
        }

# Made with Bob
