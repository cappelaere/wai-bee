# Scoring Agent Architecture

This document describes the shared patterns and architecture used by the four scoring agents (Application, Resume, Essay, Recommendation).

## Overview

All scoring agents follow the same lifecycle:

```
┌──────────────────────────────────────────────────────────────┐
│                    Agent Initialization                       │
│  1. Load schema from agents.json                             │
│  2. Validate schema exists                                   │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Analysis Phase                             │
│  1. Load analysis prompt (with schema injection)             │
│  2. Build prompt with artifact content                       │
│  3. Call LLM                                                 │
│  4. Extract JSON from response                               │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Validation & Repair                        │
│  1. Validate against schema                                  │
│  2. Auto-fix minor issues                                    │
│  3. If invalid: load repair prompt & call LLM                │
│  4. Re-validate repaired output                              │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│                    Result Persistence                         │
│  1. Create typed data object                                 │
│  2. Save JSON to output directory                            │
└──────────────────────────────────────────────────────────────┘
```

---

## Agents

| Agent | Module | Artifact Evaluated | Output File |
|-------|--------|-------------------|-------------|
| Application | `agents/application_agent/` | Application form | `application_analysis.json` |
| Resume (Academic) | `agents/academic_agent/` | Resume/CV | `resume_analysis.json` |
| Essay | `agents/essay_agent/` | Personal essays | `essay_analysis.json` |
| Recommendation | `agents/recommendation_agent/` | Recommendation letters | `recommendation_analysis.json` |

---

## Shared Utilities

### 1. Prompt Loading — `utils/prompt_loader.py`

Loads prompts and schemas from `agents.json` configuration:

```python
from utils.prompt_loader import load_analysis_prompt, load_repair_prompt, load_schema_path

# Load analysis prompt (with schema injection)
prompt = load_analysis_prompt(scholarship_folder, "essay")

# Load repair prompt
repair_prompt = load_repair_prompt(scholarship_folder, "essay")

# Get schema path
schema_path = load_schema_path(scholarship_folder, "essay")
```

**Key Features:**
- Reads `agents.json` to find prompt/schema paths
- Injects actual JSON schema into `{{AGENT_SCHEMA}}` placeholders
- Returns `None` if prompt not found (allows graceful fallback)

---

### 2. Schema Validation — `utils/schema_validator.py`

Validates and auto-fixes JSON output:

```python
from utils.schema_validator import load_schema, extract_json_from_text, validate_and_fix_iterative

# Load schema
schema = load_schema(schema_path)

# Extract JSON from LLM response (handles markdown fences, etc.)
json_data = extract_json_from_text(llm_response)

# Validate and auto-fix
is_valid, fixed_data, errors = validate_and_fix_iterative(
    data=json_data,
    schema=schema,
    max_attempts=3
)
```

**Auto-Fix Capabilities:**
- Clamps scores to valid range (0–10)
- Converts string scores to integers
- Normalizes facet names

---

### 3. LLM Repair — `utils/llm_repair.py`

Centralized repair logic for all agents:

```python
from utils.llm_repair import validate_and_repair_once, llm_repair_json

# Combined validate + repair (recommended)
is_valid, fixed_data, errors = validate_and_repair_once(
    data=json_data,
    schema=schema,
    repair_template=repair_prompt,
    model="ollama/llama3.2:3b",
    system_prompt=SYSTEM_PROMPT,  # optional
    local_fix_attempts=3,
    repair_max_tokens=3000
)

# Low-level repair (for edge cases)
repaired = llm_repair_json(
    repair_template=repair_prompt,
    invalid_json={"raw_response": llm_response},
    validation_errors=["facets[0].score: must be integer"],
    model="ollama/llama3.2:3b"
)
```

**Repair Template Placeholders:**
- `{{INVALID_JSON_OUTPUT}}` — The invalid JSON being repaired
- `{{VALIDATION_ERRORS}}` — List of validation errors
- `{{AGENT_SCHEMA}}` — The required output schema (injected by prompt_loader)

---

### 4. LLM Configuration — `utils/llm_config.py`

Centralizes LiteLLM log suppression:

```python
from utils.llm_config import configure_litellm

configure_litellm()  # Call once at agent initialization
```

---

### 5. Input File Discovery — `utils/attachment_finder.py`

Finds input files based on `agents.json` configuration:

```python
from utils.attachment_finder import find_input_files_for_agent

# Find essay files for a WAI application
files = find_input_files_for_agent(
    scholarship_folder=Path("data/Delaney_Wings"),
    agent_name="essay",
    wai_number="WAI-12345",
    outputs_base=Path("outputs")
)
# Returns: [Path("outputs/Delaney_Wings/WAI-12345/essay_1.txt"), ...]
```

---

## Agent Initialization Pattern

All agents follow the same initialization:

```python
class ScoringAgent:
    def __init__(self, scholarship_folder: Path):
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        
        # Load schema from agents.json
        schema_path = load_schema_path(scholarship_folder, "agent_name")
        if not schema_path:
            raise ValueError(f"No schema configured for agent")
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        
        self.schema = load_schema(schema_path)
        self.logger = logging.getLogger(__name__)
```

---

## Analysis Flow Pattern

All agents follow the same analysis loop:

```python
def analyze(self, wai_number: str, model: str, max_retries: int):
    # 1. Load prompt
    analysis_prompt = load_analysis_prompt(self.scholarship_folder, "agent_name")
    if not analysis_prompt:
        return None
    
    # 2. Find input files
    input_files = find_input_files_for_agent(...)
    
    # 3. Read artifact content
    content = read_file(input_files[0])
    
    # 4. Retry loop
    for attempt in range(max_retries):
        current_model = model if attempt == 0 else fallback_model
        
        # 5. Call LLM
        response = completion(model=current_model, messages=[...])
        
        # 6. Extract JSON
        json_data = extract_json_from_text(response)
        if json_data is None:
            continue
        
        # 7. Validate and repair
        repair_template = load_repair_prompt(self.scholarship_folder, "agent_name")
        is_valid, fixed, errors = validate_and_repair_once(
            data=json_data,
            schema=self.schema,
            repair_template=repair_template,
            model=current_model
        )
        
        if is_valid:
            return fixed
    
    return None
```

---

## Output Data Models

Each agent has a corresponding Pydantic model in `models/`:

| Agent | Model | File |
|-------|-------|------|
| Application | `ApplicationData`, `ApplicationAnalysis` | `models/application_data.py` |
| Resume | `AcademicData` | `models/academic_data.py` |
| Essay | `EssayData` | `models/essay_data.py` |
| Recommendation | `RecommendationData` | `models/recommendation_data.py` |

---

## Logging Convention

All agents use module-level loggers:

```python
logger = logging.getLogger(__name__)
```

This allows filtering by module:

```python
logging.getLogger("agents.essay_agent.agent").setLevel(logging.DEBUG)
```

---

## Configuration Flow

```
config.yml (human-authored)
     │
     ▼
scripts/generate_artifacts.py
     │
     ├── agents.json (agent config)
     ├── prompts/*.txt (analysis & repair prompts)
     └── schemas_generated/*.json (output schemas)
           │
           ▼
     Agent Initialization
           │
           ├── load_schema_path() → schema
           ├── load_analysis_prompt() → prompt (with schema injected)
           └── load_repair_prompt() → repair template
```

---

## Prompt Structure

All analysis prompts follow a consistent structure:

```markdown
You are an **evaluation assistant** supporting the **{Scholarship Name}** review process.

Your task is to analyze a **{Artifact}** and score it **only** according to the defined evaluation facets below.

---

## Artifact Being Evaluated

**Artifact:** {Artifact Name}
**Purpose:** {Purpose}

---

## Evaluation Facets (Score Each 0–10)

1. **Facet Name**
   Description...
   
   Evidence expected:
   - ...

---

## Scoring Rules

- Scores must be integers from **0 to 10**
- Use the full range when justified
- ...

---

## Output Contract (Required)

You must return **valid JSON only**, conforming **exactly** to the schema below.

```json
{{AGENT_SCHEMA}}
```

---

## Self-Check Requirement (Mandatory)

Before returning your response:
1. Validate that the output matches the schema exactly
2. Confirm all required facets are present
3. If the output does not conform, **repair it silently**
4. Return **only** the final valid JSON
```

---

## Repair Prompt Structure

```markdown
You previously generated JSON that does **not** conform to the required output schema.

Your task is to **repair the JSON** so that it conforms **exactly** to the authoritative schema.

---

## Invalid JSON Output

```json
{{INVALID_JSON_OUTPUT}}
```

---

## Validation Errors

{{VALIDATION_ERRORS}}

---

## Required Output Schema (Authoritative)

```json
{{AGENT_SCHEMA}}
```

---

Return **only** valid JSON.
```

---

## Testing Agents

```python
from pathlib import Path
from agents.academic_agent import AcademicAgent

# Initialize
agent = AcademicAgent(Path("data/WAI-Harvard-June-2026"))

# Analyze single application
result = agent.analyze_resume(
    wai_number="WAI-12345",
    model="ollama/llama3.2:3b",
    max_retries=3
)

# Process batch
from agents.essay_agent import EssayAgent

essay_agent = EssayAgent(Path("data/WAI-Harvard-June-2026"))
stats = essay_agent.process_batch(
    wai_numbers=["WAI-12345", "WAI-12346"],
    model="ollama/llama3.2:3b",
    output_dir=Path("outputs")
)
```

---

## Adding a New Agent

1. Create module in `agents/new_agent/`
2. Create data model in `models/new_data.py`
3. Add agent to `config.yml` artifacts section
4. Run `generate_artifacts.py` to create prompts and schema
5. Implement agent class following patterns above
6. Register in workflow if needed

---

**Last Updated:** 2026-01-01  
**Author:** Pat G Cappelaere, IBM Federal Consulting

