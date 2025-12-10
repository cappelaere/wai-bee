"""Scholarship Application Processing Workflow.

This workflow orchestrates all agents to process scholarship applications
from start to finish in a coordinated manner.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from beeai_framework.errors import FrameworkError
from beeai_framework.workflows import Workflow

from agents.attachment_agent.agent import AttachmentAgent
from agents.application_agent.agent import ApplicationAgent
from agents.recommendation_agent.agent import RecommendationAgent
from agents.academic_agent.agent import AcademicAgent
from agents.essay_agent.agent import EssayAgent
from agents.summary_agent.agent import SummaryAgent


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
    
    Attributes:
        scholarship_folder: Path to scholarship configuration folder.
        outputs_dir: Base outputs directory.
        logger: Logger instance.
    """
    
    def __init__(
        self,
        scholarship_folder: Path,
        outputs_dir: Path = Path("outputs"),
        schema: Optional[type] = None
    ):
        """Initialize the workflow.
        
        Args:
            scholarship_folder: Path to scholarship folder (e.g., data/Delaney_Wings).
            outputs_dir: Base outputs directory.
            schema: Optional workflow schema type/class for beeai-framework.
        """
        # Initialize parent Workflow class with schema (use default if not provided)
        super().__init__(schema=schema or DefaultWorkflowSchema)
        
        self.logger = logging.getLogger(__name__)
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        self.outputs_dir = outputs_dir
        
        # Initialize all agents
        self._initialize_agents()
        
        self.logger.info(f"Initialized ScholarshipProcessingWorkflow for {self.scholarship_name}")
    
    def _initialize_agents(self) -> None:
        """Initialize all processing agents."""
        # Most agents don't take constructor parameters
        self.attachment_agent = AttachmentAgent()
        self.application_agent = ApplicationAgent()
        self.recommendation_agent = RecommendationAgent()
        self.academic_agent = AcademicAgent()
        self.essay_agent = EssayAgent()
        
        # Only SummaryAgent takes outputs_dir and scholarship_folder
        self.summary_agent = SummaryAgent(
            self.outputs_dir,
            self.scholarship_folder
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
        parallel: bool = True
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
            
        Returns:
            ApplicantResult with all stage results.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self.logger.info("="*60)
        self.logger.info(f"Processing Applicant: {wai_number}")
        self.logger.info(f"Parallel Mode: {parallel}")
        self.logger.info("="*60)
        
        skip_stages = skip_stages or []
        start_time = time.time()
        stages = []
        
        # Determine scholarship folder path for agents
        scholarship_folder_str = str(self.scholarship_folder)
        
        # Stage 1: Analyze application (must be first to extract applicant info)
        self.logger.info("Stage 1: Application analysis...")
        if "application" not in skip_stages:
            stage_result = self._run_stage(
                "application",
                self.application_agent.analyze_application,
                wai_number,
                scholarship_folder_str
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
                scholarship_folder_str
            )
            stages.append(stage_result)
        
        # Stage 3: Parallel analysis (after attachments complete)
        self.logger.info("Stage 3: Parallel analysis (Recommendations, Academic, Essays)...")
        
        analysis_tasks = []
        
        if "recommendations" not in skip_stages:
            analysis_tasks.append(("recommendations",
                                   self.recommendation_agent.analyze_recommendations,
                                   wai_number,
                                   scholarship_folder_str))
        
        if "academic" not in skip_stages:
            analysis_tasks.append(("academic",
                                   self.academic_agent.analyze_academic_profile,
                                   wai_number,
                                   scholarship_folder_str))
        
        if "essays" not in skip_stages:
            # EssayAgent has a different signature - needs more parameters
            analysis_tasks.append(("essays",
                                   self._analyze_essays_wrapper,
                                   wai_number))
        
        if parallel and analysis_tasks:
            # Run analysis stages in parallel
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_stage = {
                    executor.submit(self._run_stage, name, func, *args): name
                    for name, func, *args in analysis_tasks
                }
                
                for future in as_completed(future_to_stage):
                    stage_name = future_to_stage[future]
                    try:
                        stage_result = future.result()
                        stages.append(stage_result)
                        self.logger.info(f"  ✓ {stage_name} completed")
                    except Exception as e:
                        self.logger.error(f"  ✗ {stage_name} failed: {e}")
                        stages.append(StageResult(
                            stage_name=stage_name,
                            success=False,
                            message=f"{stage_name} failed",
                            error=str(e),
                            duration_seconds=0.0
                        ))
        else:
            # Run analysis stages sequentially
            for stage_name, func, *args in analysis_tasks:
                stage_result = self._run_stage(stage_name, func, *args)
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
    
    def process_all_applicants(
        self,
        wai_numbers: Optional[List[str]] = None,
        skip_stages: Optional[List[str]] = None,
        max_applicants: Optional[int] = None,
        parallel: bool = True,
        stop_on_error: bool = False
    ) -> Dict[str, Any]:
        """Process all applicants for the scholarship.
        
        Args:
            wai_numbers: Optional list of WAI numbers. If None, processes all found.
            skip_stages: Optional list of stage names to skip.
            max_applicants: Optional maximum number of applicants to process.
            parallel: If True, run analysis stages in parallel (default: True).
            stop_on_error: If True, stop processing when an applicant fails (default: False).
            
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
            
            applicant_result = self.process_applicant(wai_number, skip_stages, parallel)
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
        """Discover all applicant WAI numbers in the scholarship folder.
        
        Returns:
            List of WAI numbers.
        """
        # Look for Applications subfolder
        applications_folder = self.scholarship_folder / "Applications"
        
        if applications_folder.exists() and applications_folder.is_dir():
            wai_numbers = [d.name for d in applications_folder.iterdir() if d.is_dir() and not d.name.startswith('.')]
            self.logger.info(f"Found {len(wai_numbers)} applicants in {applications_folder}")
            return sorted(wai_numbers)
        
        self.logger.warning(f"No Applications folder found in {self.scholarship_folder}")
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
    
    def _analyze_essays_wrapper(self, wai_number: str) -> Optional[Any]:
        """Wrapper for essay analysis to match workflow interface.
        
        Args:
            wai_number: WAI application number.
        
        Returns:
            EssayData if successful, None otherwise.
        """
        from pathlib import Path
        
        attachments_dir = self.outputs_dir / "attachments"
        criteria_path = self.scholarship_folder / "criteria" / "essay_criteria.txt"
        
        return self.essay_agent.analyze_essays(
            attachments_dir=attachments_dir,
            scholarship_name=self.scholarship_name,
            wai_number=wai_number,
            criteria_path=criteria_path,
            output_dir=self.outputs_dir
        )
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow configuration and status.
        
        Returns:
            Status dictionary.
        """
        return {
            "scholarship": self.scholarship_name,
            "outputs_dir": str(self.outputs_dir),
            "agents": {
                "attachment": "AttachmentAgent",
                "application": "ApplicationAgent",
                "recommendation": "RecommendationAgent",
                "academic": "AcademicAgent",
                "essay": "EssayAgent",
                "summary": "SummaryAgent"
            },
            "available_stages": [
                "attachments",
                "application",
                "recommendations",
                "academic",
                "essays",
                "summary"
            ]
        }

# Made with Bob
