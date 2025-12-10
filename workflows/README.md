# Scholarship Processing Workflow

This directory contains workflow orchestration for processing scholarship applications through multiple specialized agents.

## Overview

The `ScholarshipProcessingWorkflow` class coordinates all agents to process scholarship applications from start to finish in a structured, repeatable manner.

📊 **[View Workflow Diagrams](WORKFLOW_DIAGRAM.md)** - Comprehensive Mermaid diagrams showing system architecture, data flow, and processing sequences.

🎨 **[Visualization Guide](VISUALIZATION_GUIDE.md)** - Learn how to view and interact with the workflow diagrams in VS Code, GitHub, or online tools.

## Architecture

### Workflow Stages

The workflow processes each applicant through 4 sequential stages:

#### Stage 1: Application Processing
**Application Agent** - Extract and analyze applicant information from application PDF

#### Stage 2: Attachment Processing
**Attachment Agent** - Process and redact PII from application attachments

#### Stage 3: Parallel Analysis (runs concurrently after attachments complete)
Three agents run in parallel using ThreadPoolExecutor (3 workers):
- **Recommendation Agent** - Analyze recommendation letters
- **Academic Agent** - Analyze academic profile from resume/CV
- **Essay Agent** - Analyze personal essays for motivation and character

#### Stage 4: Summary Generation
**Summary Agent** - Generate final CSV and statistics report (batch operation)

**Performance Benefit**: Stage 3 agents run in parallel, significantly reducing processing time for each applicant. Parallel execution begins only after both Application and Attachment agents complete sequentially.

### Components

```
workflows/
├── __init__.py                    # Package initialization
├── scholarship_workflow.py        # Main workflow orchestration
└── README.md                      # This file
```

## Usage

### Basic Usage

```python
from pathlib import Path
from workflows import ScholarshipProcessingWorkflow

# Initialize workflow
workflow = ScholarshipProcessingWorkflow(
    scholarship_folder=Path("data/Delaney_Wings"),
    outputs_dir=Path("outputs")
)

# Process a single applicant
result = workflow.process_applicant("75179")

# Process all applicants
results = workflow.process_all_applicants()
```

### Process Single Applicant

```python
# Process one applicant through all stages (parallel mode - default)
result = workflow.process_applicant("75179")

# Process with sequential execution (disable parallelization)
result = workflow.process_applicant("75179", parallel=False)

# Check result
if result.success:
    print(f"Successfully processed {result.wai_number}")
    print(f"Total time: {result.total_duration_seconds:.2f}s")
    
    # Check individual stages
    for stage in result.stages:
        print(f"{stage.stage_name}: {stage.message}")
```

### Process Multiple Applicants

```python
# Process all applicants (parallel mode - default)
results = workflow.process_all_applicants()

# Process with sequential execution (disable parallelization)
results = workflow.process_all_applicants(parallel=False)

# Process specific applicants
results = workflow.process_all_applicants(
    wai_numbers=["75179", "77747", "82799"]
)

# Limit number of applicants (useful for testing)
results = workflow.process_all_applicants(
    max_applicants=5,
    parallel=True  # Enable parallel processing
)
```

### Skip Stages

You can skip stages that have already been completed:

```python
# Skip attachment processing (already done)
results = workflow.process_all_applicants(
    skip_stages=["attachments"]
)

# Skip multiple stages
results = workflow.process_all_applicants(
    skip_stages=["attachments", "application"]
)
```

### Available Stages

- `attachments` - Attachment processing
- `application` - Application analysis
- `recommendations` - Recommendation analysis
- `academic` - Academic profile analysis
- `essays` - Essay analysis
- `summary` - Summary generation (only in batch mode)

## Data Classes

### StageResult

Represents the result of a single processing stage:

```python
@dataclass
class StageResult:
    stage_name: str              # Name of the stage
    success: bool                # Whether stage succeeded
    message: str                 # Status message
    data: Dict[str, Any]         # Stage output data
    error: Optional[str]         # Error message if failed
    duration_seconds: float      # Time taken
```

### ApplicantResult

Represents the complete processing result for an applicant:

```python
@dataclass
class ApplicantResult:
    wai_number: str                    # WAI application number
    success: bool                      # Overall success
    stages: List[StageResult]          # Results from each stage
    total_duration_seconds: float      # Total processing time
```

## Example Script

See `examples/run_workflow.py` for a complete example demonstrating:

1. Processing a single applicant
2. Processing multiple applicants with limits
3. Processing with skipped stages
4. Accessing and displaying results

Run the example:

```bash
python3 examples/run_workflow.py
```

## Workflow Results

The workflow returns a comprehensive results dictionary:

```python
{
    "scholarship": "Delaney_Wings",
    "start_time": "2025-12-06T09:00:00",
    "end_time": "2025-12-06T09:15:00",
    "total_applicants": 10,
    "successful": 9,
    "failed": 1,
    "total_duration_seconds": 900.5,
    "applicants": [
        ApplicantResult(...),
        ApplicantResult(...),
        ...
    ],
    "summary": {
        "success": True,
        "total_applicants": 10,
        "complete_applications": 8,
        "csv_file": "outputs/summary/Delaney_Wings_summary.csv",
        "stats_file": "outputs/summary/Delaney_Wings_statistics.txt"
    }
}
```

## Error Handling

The workflow includes comprehensive error handling:

- Each stage is wrapped in try-except blocks
- Failures in one stage don't prevent other stages from running
- All errors are logged and included in results
- Stage timing is tracked even for failed stages

## Performance

### Timing Tracking

The workflow tracks timing for:

- Individual stages
- Per-applicant total time
- Overall workflow duration

This helps identify bottlenecks and optimize processing.

### Parallel Processing Benefits

**Default Mode (parallel=True)**:
- Phase 1 (Sequential): Attachments + Application run one after another
- Phase 2 (Parallel): Recommendations, Academic, and Essays run simultaneously using ThreadPoolExecutor
- Phase 3 (Sequential): Summary generation after all applicants processed

**Performance Improvement**:
- Sequential mode: ~15-20 seconds per applicant (5 stages × 3-4 seconds each)
- Parallel mode: ~10-12 seconds per applicant (2 sequential + 1 parallel phase)
- **~40% faster** with parallel processing enabled

**When to Use Sequential Mode**:
- Debugging individual agent issues
- Limited system resources
- Single-threaded LLM backends that don't support concurrent requests

**Example**:
```python
# Fast: Parallel processing (default)
results = workflow.process_all_applicants(parallel=True)

# Slower but more predictable: Sequential processing
results = workflow.process_all_applicants(parallel=False)
```

## Future Enhancements

### BeeAI Integration

The workflow is designed to be compatible with the BeeAI framework for more advanced agent orchestration. To integrate BeeAI:

1. Install BeeAI: `pip install bee-agent`
2. Update workflow to use BeeAI agents and tools
3. Leverage BeeAI's memory and planning capabilities

### Parallel Processing

For large batches, consider adding parallel processing:

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(workflow.process_applicant, wai)
        for wai in wai_numbers
    ]
    results = [f.result() for f in futures]
```

### Checkpointing

Add checkpointing to resume interrupted workflows:

```python
# Save progress after each applicant
workflow.save_checkpoint(applicant_result)

# Resume from checkpoint
workflow.resume_from_checkpoint()
```

## Configuration

The workflow uses the scholarship's `agents.json` configuration file for:

- Agent weights
- Processing order
- Criteria files
- Output directories

See `data/Delaney_Wings/agents.json` for an example.

## Logging

The workflow uses Python's standard logging module. Configure logging in your script:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

## Troubleshooting

### Common Issues

1. **Missing application folders**: Ensure the scholarship folder contains the correct application directory structure
2. **Agent initialization errors**: Check that all required configuration files exist
3. **Stage failures**: Review logs for specific error messages from individual agents

### Debug Mode

Enable debug logging for more detailed output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new stages or modifying the workflow:

1. Update the `_run_stage` method to handle new stage types
2. Add stage to `available_stages` in `get_workflow_status`
3. Update this README with new stage documentation
4. Add tests for new functionality

## License

MIT License - See LICENSE file for details

## Author

Pat G Cappelaere, IBM Federal Consulting