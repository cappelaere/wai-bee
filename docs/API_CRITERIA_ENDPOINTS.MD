# API Prompt & Agent Configuration Endpoints

## Overview

The API provides read-only access to:
1. **Evaluation Prompts** — Generated analysis and repair prompts used by agents
2. **Agent Configuration** — Agent settings, weights, and evaluation facets

All prompts and configurations are generated from `config.yml` via `generate_artifacts.py` and should not be modified at runtime.

---

## Prompt Endpoints

### 1. List All Prompts

**Endpoint:** `GET /criteria?scholarship={scholarship}`

**Description:** List all available evaluation prompts for a scholarship.

**Parameters:**
- `scholarship` (query, required): Scholarship name (e.g., `Delaney_Wings`)

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "criteria_count": 8,
  "criteria": [
    {
      "name": "application_analysis",
      "filename": "application_analysis.txt",
      "type": "analysis",
      "agent": "application",
      "url": "http://localhost:8200/criteria/file?scholarship=Delaney_Wings&filename=application_analysis.txt"
    },
    {
      "name": "application_repair",
      "filename": "application_repair.txt",
      "type": "repair",
      "agent": "application",
      "url": "http://localhost:8200/criteria/file?scholarship=Delaney_Wings&filename=application_repair.txt"
    },
    {
      "name": "resume_analysis",
      "filename": "resume_analysis.txt",
      "type": "analysis",
      "agent": "resume",
      "url": "..."
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8200/criteria?scholarship=Delaney_Wings"
```

---

### 2. Get Prompt by Agent Type

**Endpoint:** `GET /criteria/by-type?criteria_type={agent}&scholarship={scholarship}`

**Description:** Get the full analysis prompt text for a specific agent.

**Parameters:**
- `criteria_type` (query, required): Agent name (`application`, `resume`, `essay`, `recommendation`)
- `scholarship` (query, required): Scholarship name

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "criteria_type": "essay",
  "filename": "essay_analysis.txt",
  "content": "You are an **evaluation assistant** supporting the...",
  "line_count": 92
}
```

**Examples:**
```bash
# Get essay analysis prompt
curl "http://localhost:8200/criteria/by-type?criteria_type=essay&scholarship=Delaney_Wings"

# Get resume analysis prompt
curl "http://localhost:8200/criteria/by-type?criteria_type=resume&scholarship=Delaney_Wings"
```

---

### 3. Download Prompt File

**Endpoint:** `GET /criteria/file?scholarship={scholarship}&filename={filename}`

**Description:** Download a specific prompt file as plain text.

**Parameters:**
- `scholarship` (query, required): Scholarship name
- `filename` (query, required): Prompt filename (e.g., `essay_analysis.txt`)

**Response:** Plain text file

**Example:**
```bash
curl "http://localhost:8200/criteria/file?scholarship=Delaney_Wings&filename=essay_analysis.txt" -o essay_prompt.txt
```

---

## Agent Configuration Endpoints

### 4. Get All Agents Configuration

**Endpoint:** `GET /admin/{scholarship}/agents`

**Description:** Get complete agent configuration including weights, prompts, and schemas.

**Response:**
```json
{
  "scholarship_name": "Delaney_Wings",
  "description": "Agent configuration for Valerie Delaney Memorial Scholarship",
  "version": "1.0.0",
  "agents": [
    {
      "name": "application",
      "display_name": "Application Agent",
      "description": "Evaluates application completeness and eligibility",
      "weight": 0.20,
      "enabled": true,
      "required": true,
      "evaluates": ["Completeness", "Eligibility & Validity", "Attachment Quality"],
      "analysis_prompt": "prompts/application_analysis.txt",
      "repair_prompt": "prompts/application_repair.txt",
      "schema": "schemas_generated/application_analysis.schema.json"
    },
    {
      "name": "resume",
      "display_name": "Resume Agent",
      "weight": 0.25,
      "evaluates": ["Academic Achievement", "Aviation Experience", "Leadership & Activities"]
    },
    {
      "name": "essay",
      "display_name": "Essay Agent",
      "weight": 0.30,
      "evaluates": ["Aviation Passion & Goals", "Personal Character", "Scholarship Connection"]
    },
    {
      "name": "recommendation",
      "display_name": "Recommendation Agent",
      "weight": 0.25,
      "evaluates": ["Recommender Credibility", "Specific Endorsements", "Potential Assessment"]
    }
  ],
  "scoring_agents": ["application", "resume", "essay", "recommendation"],
  "total_weight": 1.0
}
```

**Example:**
```bash
curl "http://localhost:8200/admin/Delaney_Wings/agents"
```

---

### 5. Get Scoring Weights

**Endpoint:** `GET /admin/{scholarship}/weights`

**Description:** Get agent scoring weights for final score calculation.

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "weights": {
    "application": 0.20,
    "resume": 0.25,
    "essay": 0.30,
    "recommendation": 0.25
  },
  "total": 1.0
}
```

---

### 6. Get Agent Prompts

**Endpoint:** `GET /admin/{scholarship}/prompts/{agent_name}`

**Description:** Get analysis and repair prompts for a specific agent.

**Parameters:**
- `scholarship` (path): Scholarship name
- `agent_name` (path): Agent name (`application`, `resume`, `essay`, `recommendation`)

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "agent": "essay",
  "analysis_prompt": "You are an **evaluation assistant**...",
  "repair_prompt": "You previously generated JSON that does **not** conform..."
}
```

---

### 7. Get Agent Schema

**Endpoint:** `GET /admin/{scholarship}/schema/{agent_name}`

**Description:** Get the output JSON schema for a specific agent.

**Parameters:**
- `scholarship` (path): Scholarship name
- `agent_name` (path): Agent name

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "agent": "essay",
  "schema": {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Essay Analysis Output",
    "type": "object",
    "required": ["facets", "overall_notes"],
    "properties": {
      "facets": {
        "type": "array",
        "items": {...}
      }
    }
  }
}
```

---

## Prompt Types

### Analysis Prompts

Analysis prompts guide agents in evaluating application materials:

| Agent | Prompt File | Purpose |
|-------|-------------|---------|
| Application | `application_analysis.txt` | Evaluate completeness, eligibility, attachments |
| Resume | `resume_analysis.txt` | Evaluate academic achievement, experience |
| Essay | `essay_analysis.txt` | Evaluate motivation, character, goals |
| Recommendation | `recommendation_analysis.txt` | Evaluate endorsement quality, credibility |

### Repair Prompts

Repair prompts guide the LLM in fixing invalid JSON output:

| Agent | Prompt File | Purpose |
|-------|-------------|---------|
| Application | `application_repair.txt` | Fix schema validation errors |
| Resume | `resume_repair.txt` | Fix schema validation errors |
| Essay | `essay_repair.txt` | Fix schema validation errors |
| Recommendation | `recommendation_repair.txt` | Fix schema validation errors |

---

## Prompt Structure

All analysis prompts follow a consistent structure:

1. **Role Framing** — Establishes the LLM as an evaluation assistant
2. **Scholarship Context** — Identifies the scholarship being evaluated
3. **Evaluation Facets** — Lists the specific criteria to score (0–10)
4. **Scoring Rules** — Guidelines for assigning scores
5. **Evidence Requirements** — What evidence to cite
6. **Output Contract** — JSON schema placeholder (`{{AGENT_SCHEMA}}`)
7. **Self-Check Block** — Validation instructions

Schema placeholders are replaced with actual JSON at runtime by `utils/prompt_loader.py`.

---

## Directory Structure

```
data/{scholarship}/
├── config.yml              # Human-authored configuration
├── agents.json             # Generated agent configuration
├── prompts/                # Generated prompt files
│   ├── application_analysis.txt
│   ├── application_repair.txt
│   ├── resume_analysis.txt
│   ├── resume_repair.txt
│   ├── essay_analysis.txt
│   ├── essay_repair.txt
│   ├── recommendation_analysis.txt
│   └── recommendation_repair.txt
└── schemas_generated/      # Generated output schemas
    ├── application_analysis.schema.json
    ├── resume_analysis.schema.json
    ├── essay_analysis.schema.json
    └── recommendation_analysis.schema.json
```

---

## Generation Workflow

Prompts and schemas are generated, not manually written:

```bash
# Validate configuration first
python scripts/validate_config.py data/{scholarship}

# Generate all artifacts (agents.json, prompts, schemas)
python scripts/generate_artifacts.py data/{scholarship}

# Or generate prompts only
python scripts/generate_prompts.py data/{scholarship}
```

See `docs/SCHOLARSHIP_PROCESS.md` for the complete workflow.

---

## Error Handling

| Status | Error |
|--------|-------|
| 400 | Invalid criteria type or filename |
| 404 | Scholarship not found or prompts not generated |
| 500 | Internal server error |

**Example Error Response:**
```json
{
  "detail": "Prompt not found for 'social'. Available types: application, resume, essay, recommendation"
}
```

---

**Last Updated:** 2026-01-01  
**Version:** 2.0.0  
**Author:** Pat G Cappelaere, IBM Federal Consulting
