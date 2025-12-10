"""Workflows package for orchestrating scholarship application processing.

This package provides workflow orchestration for coordinating multiple
agents to process scholarship applications from start to finish.

Author: Pat G Cappelaere, IBM Federal Consulting
"""

from workflows.scholarship_workflow import (
    ScholarshipProcessingWorkflow,
    StageResult,
    ApplicantResult
)

__all__ = [
    'ScholarshipProcessingWorkflow',
    'StageResult',
    'ApplicantResult'
]

# Made with Bob
