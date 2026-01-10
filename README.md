# WAI-Bee — AI-Powered Scholarship Evaluation System

An AI-powered, schema-driven scholarship application evaluation system for Women in Aviation International (WAI). The system uses multiple specialized agents to analyze application materials and produce fair, auditable, and repeatable evaluations.

## Key Features

- **Multi-Agent Architecture**: Five specialized agents analyze different aspects of applications
- **Schema-Driven Evaluation**: All criteria defined in human-authored `config.yml`, validated and generated into machine-consumable artifacts
- **Auditable & Repeatable**: Deterministic prompt generation, schema validation, and LLM repair loops
- **Multi-Tenancy**: Support for multiple scholarships with isolated configurations
- **REST API**: FastAPI-based API for accessing scores, statistics, and analyses
- **Docker Deployment**: Production-ready containerized deployment

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scholarship Configuration                     │
│                         config.yml                               │
│              (Single source of truth per scholarship)            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Artifact Generation                           │
│   scripts/generate_artifacts.py → agents.json, schemas, prompts │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Runtime Evaluation                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐│
│  │Attachment │ │Application│ │  Resume   │ │   Essay Agent     ││
│  │  Agent    │ │  Agent    │ │  Agent    │ │                   ││
│  └───────────┘ └───────────┘ └───────────┘ └───────────────────┘│
│  ┌───────────────────┐                                          │
│  │Recommendation     │  →  Weighted Score Aggregation           │
│  │Agent              │                                          │
│  └───────────────────┘                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
wai-bee/
├── agents/                     # Scoring agents
│   ├── academic_agent/         # Resume/CV analysis (aliased as "resume")
│   ├── application_agent/      # Application form analysis
│   ├── attachment_agent/       # PII redaction & text extraction
│   ├── essay_agent/            # Personal essay analysis
│   └── recommendation_agent/   # Recommendation letter analysis
├── bee_agents/                 # FastAPI server & API
├── WAI-general-2025/           # Scholarship data container
│   ├── data/                   # Application files by scholarship
│   │   ├── Delaney_Wings/      # {WAI-ID}/ subfolders with PDFs
│   │   └── Evans_Wings/
│   ├── config/                 # Scholarship configurations
│   │   ├── Delaney_Wings/
│   │   │   ├── config.yml      # Human-authored configuration
│   │   │   ├── agents.json     # Generated agent config
│   │   │   ├── prompts/        # Generated analysis & repair prompts
│   │   │   └── schemas_generated/
│   │   └── Evans_Wings/
│   ├── output/                 # Processing results by scholarship
│   │   ├── Delaney_Wings/      # {WAI-ID}/ subfolders with analysis JSON
│   │   └── Evans_Wings/
│   └── logs/                   # Processing logs by scholarship
│       ├── Delaney_Wings/
│       └── Evans_Wings/
├── docs/                       # Documentation
├── models/                     # Pydantic data models
├── schemas/                    # Shared JSON schemas
├── scripts/                    # Generation & validation scripts
├── terraform/                  # AWS infrastructure (S3, KMS)
├── utils/                      # Shared utilities
└── workflows/                  # Workflow orchestration
```

## Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Install Ollama (for local LLM)

```bash
# Install from https://ollama.ai, then pull models
ollama pull llama3.2:3b
ollama pull llama3:latest  # fallback model
```

### 3. Configure a Scholarship

Create `WAI-general-2025/config/<scholarship-name>/config.yml` with evaluation criteria. See `docs/SCHOLARSHIP_PROCESS.md` for the complete specification.

### 4. Generate Artifacts

```bash
# Validate and generate all artifacts
python scripts/generate_all.py WAI-general-2025/config/<scholarship-name>
```

This produces (in the config folder):
- `agents.json` — Agent configuration with prompts and schemas
- `prompts/*.txt` — Analysis and repair prompts
- `schemas_generated/*.json` — Output validation schemas
- `scholarship.json` — Locked criteria contract

### 5. Process Applications

```python
from pathlib import Path
from workflows import ScholarshipProcessingWorkflow
from utils.config import config

# Initialize workflow
workflow = ScholarshipProcessingWorkflow(
    scholarship_folder=config.get_config_folder("Delaney_Wings"),
    outputs_dir=config.OUTPUTS_DIR
)

# Process all applicants
results = workflow.process_all_applicants()
print(f"Processed: {results['successful']}/{results['total_applicants']}")
```

Or use the CLI:

```bash
python examples/process_applicants.py --scholarship Delaney_Wings --max-applicants 10
```

Or use individual agents:

```python
from pathlib import Path
from agents.scoring_runner import ScoringRunner
from utils.config import config

# Initialize runner with scholarship config
runner = ScoringRunner(
    scholarship_folder=config.get_config_folder("Delaney_Wings"),
    outputs_dir=config.OUTPUTS_DIR,
)

# Score a single applicant across all scoring artifacts
results = runner.run_for_wai(
    wai_number="75179",
    model="ollama/llama3.2:3b",
    fallback_model="ollama/llama3:latest",
    max_retries=3,
)
print(results)
```

### 6. Run the API Server

```bash
python -m bee_agents.api --scholarship WAI-Harvard-June-2026 --port 8200
```

Access the API at http://localhost:8200/docs

## Agents

| Agent | Purpose | Input | Output |
|-------|---------|-------|--------|
| **Attachment** | Extract text, redact PII | PDF/DOCX attachments | Cleaned text files |
| **Application** | Evaluate completeness & eligibility | Application form | Facet scores |
| **Resume** | Evaluate academic profile | Resume/CV | Facet scores |
| **Essay** | Evaluate motivation & character | Personal essays | Facet scores |
| **Recommendation** | Evaluate third-party endorsements | Recommendation letters | Facet scores |

## Configuration System

The system uses a **config-driven architecture**:

1. **`config.yml`** — Human-authored, single source of truth per scholarship
2. **`agents.json`** — Generated, machine-consumable agent configuration
3. **`prompts/*.txt`** — Generated LLM prompts with schema placeholders
4. **`schemas_generated/*.json`** — Generated JSON schemas for output validation

### Validation & Generation

```bash
# Validate configuration
python scripts/validate_config.py data/<scholarship>

# Generate all artifacts
python scripts/generate_artifacts.py data/<scholarship>

# Generate prompts only
python scripts/generate_prompts.py data/<scholarship>
```

See `docs/SCHOLARSHIP_PROCESS.md` for the complete workflow.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /top_scores` | Top scoring applications |
| `GET /score/{wai_number}` | Score for specific application |
| `GET /statistics` | Aggregated statistics |
| `GET /agents` | Agent configuration |
| `GET /application/{wai_number}` | Application analysis |
| `GET /academic/{wai_number}` | Academic/resume analysis |
| `GET /essay/{wai_number}` | Essay analysis |
| `GET /recommendation/{wai_number}` | Recommendation analysis |

## Docker Deployment

```bash
# Build and run
docker-compose up --build

# API available at http://localhost:8200
```

See `docs/DOCKER_DEPLOYMENT.MD` for production configuration.

## Documentation

| Document | Description |
|----------|-------------|
| `docs/SCHOLARSHIP_PROCESS.md` | **Authoritative** — End-to-end process for config → validation → generation → runtime |
| `docs/AGENT_ARCHITECTURE.md` | Shared agent patterns, prompt loading, LLM repair |
| `docs/MULTI_TENANCY_DESIGN.MD` | Multi-scholarship architecture |
| `docs/DOCKER_DEPLOYMENT.MD` | Production deployment guide |
| `docs/API_SERVER_ARCHITECTURE.MD` | API design and endpoints |

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Adding a New Scholarship

1. Create `data/<scholarship-name>/config.yml`
2. Run `python scripts/validate_config.py data/<scholarship-name>`
3. Run `python scripts/generate_artifacts.py data/<scholarship-name>`
4. Process applications with the workflow or individual agents

### Code Quality

```bash
# Lint check
python -m py_compile agents/**/*.py utils/*.py

# Type checking (optional)
mypy agents/ utils/
```

## License

MIT License — See LICENSE file

## Author

Pat G Cappelaere, IBM Federal Consulting
