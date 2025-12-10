# API Configuration Endpoints Documentation

## Overview

The API now includes endpoints to retrieve:
1. **Evaluation Criteria** - Detailed scoring criteria for each evaluation type
2. **Agent Configuration** - Agent scoring weights and evaluation details

These endpoints provide transparency into the evaluation process and scoring methodology.

## Criteria Endpoints

### 1. List All Criteria

**Endpoint:** `GET /criteria`

**Description:** List all available evaluation criteria for the scholarship.

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "criteria_count": 5,
  "criteria": [
    {
      "type": "application",
      "name": "Application Criteria",
      "description": "Criteria for evaluating application completeness and validity",
      "filename": "application_criteria.txt",
      "url": "/criteria/application"
    },
    {
      "type": "academic",
      "name": "Academic Criteria",
      "description": "Criteria for evaluating academic performance and readiness",
      "filename": "academic_criteria.txt",
      "url": "/criteria/academic"
    },
    {
      "type": "essay",
      "name": "Essay Criteria",
      "description": "Criteria for evaluating essay quality and content",
      "filename": "essay_criteria.txt",
      "url": "/criteria/essay"
    },
    {
      "type": "recommendation",
      "name": "Recommendation Criteria",
      "description": "Criteria for evaluating letters of recommendation",
      "filename": "recommendation_criteria.txt",
      "url": "/criteria/recommendation"
    },
    {
      "type": "social",
      "name": "Social Criteria",
      "description": "Criteria for evaluating social impact and community involvement",
      "filename": "social_criteria.txt",
      "url": "/criteria/social"
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8200/criteria
```

---

### 2. Get Specific Criteria

**Endpoint:** `GET /criteria/{criteria_type}`

**Description:** Get evaluation criteria for a specific type.

**Parameters:**
- `criteria_type` (path): Type of criteria
  - Valid values: `application`, `academic`, `essay`, `recommendation`, `social`

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "criteria_type": "application",
  "filename": "application_criteria.txt",
  "content": "APPLICATION COMPLETENESS AND VALIDITY SCORING CRITERIA\n\n...",
  "line_count": 51
}
```

**Examples:**

```bash
# Get application criteria
curl http://localhost:8200/criteria/application

# Get academic criteria
curl http://localhost:8200/criteria/academic

# Get essay criteria
curl http://localhost:8200/criteria/essay

# Get recommendation criteria
curl http://localhost:8200/criteria/recommendation

# Get social criteria
curl http://localhost:8200/criteria/social
```

**Error Response (Invalid Type):**
```json
{
  "detail": "Invalid criteria type. Must be one of: application, academic, essay, recommendation, social"
}
```

**Error Response (Not Found):**
```json
{
  "detail": "Academic criteria not found for Delaney_Wings"
}
```

---

## Criteria Types

### Application Criteria
Evaluates the completeness and validity of the application itself:
- Completeness score (30 points)
- Data validity score (30 points)
- Attachment completeness score (40 points)

### Academic Criteria
Evaluates academic performance and readiness:
- Academic performance
- Academic relevance to aviation
- Academic readiness for training
- Academic awards and achievements

### Essay Criteria
Evaluates essay quality and content:
- Writing quality and clarity
- Content relevance to scholarship goals
- Personal insight and reflection
- Alignment with aviation career goals

### Recommendation Criteria
Evaluates letters of recommendation:
- Recommender credibility and relationship
- Specific examples and evidence
- Assessment of applicant's qualifications
- Strength of endorsement

### Social Criteria
Evaluates social impact and community involvement:
- Community service and volunteer work
- Leadership roles and initiatives
- Social impact and contributions
- Commitment to helping others

---

## Use Cases

### 1. Display Criteria in UI
```javascript
// Fetch all criteria
const response = await fetch('http://localhost:8200/criteria');
const data = await response.json();

// Display criteria list
data.criteria.forEach(criteria => {
  console.log(`${criteria.name}: ${criteria.description}`);
});
```

### 2. Show Specific Criteria to Reviewers
```javascript
// Get application criteria for review
const response = await fetch('http://localhost:8200/criteria/application');
const data = await response.json();

// Display criteria content
document.getElementById('criteria-content').textContent = data.content;
```

### 3. Validate Criteria Availability
```python
import requests

# Check which criteria are available
response = requests.get('http://localhost:8200/criteria')
criteria_types = [c['type'] for c in response.json()['criteria']]

print(f"Available criteria: {', '.join(criteria_types)}")
```

---

## Integration with Multi-Tenancy

The criteria endpoints are **scholarship-aware**:

- Each scholarship has its own criteria files in `data/{scholarship}/criteria/`
- The API automatically serves criteria for the initialized scholarship
- Different scholarships can have different evaluation criteria
- Criteria are isolated per scholarship (no cross-scholarship access)

**Example Directory Structure:**
```
data/
├── Delaney_Wings/
│   └── criteria/
│       ├── application_criteria.txt
│       ├── academic_criteria.txt
│       ├── essay_criteria.txt
│       ├── recommendation_criteria.txt
│       └── social_criteria.txt
└── Evans_Wings/
    └── criteria/
        ├── application_criteria.txt
        ├── academic_criteria.txt
        ├── essay_criteria.txt
        ├── recommendation_criteria.txt
        └── social_criteria.txt
```

---

## Testing

### Run Criteria Tests
```bash
# Run only criteria tests
python3 -m pytest tests/test_api_criteria.py -v

# Run all API tests including criteria
python3 -m pytest tests/test_api_*.py -v
```

### Test Results
```
tests/test_api_criteria.py::test_list_criteria PASSED
tests/test_api_criteria.py::test_get_application_criteria PASSED
tests/test_api_criteria.py::test_get_academic_criteria PASSED
tests/test_api_criteria.py::test_get_essay_criteria PASSED
tests/test_api_criteria.py::test_get_recommendation_criteria PASSED
tests/test_api_criteria.py::test_get_invalid_criteria_type PASSED
tests/test_api_criteria.py::test_criteria_content_structure PASSED
tests/test_api_criteria.py::test_all_criteria_types_available PASSED

8 passed in 0.04s
```

---

## Error Handling

### Service Not Initialized (503)
```json
{
  "detail": "Service not initialized"
}
```

### Invalid Criteria Type (400)
```json
{
  "detail": "Invalid criteria type. Must be one of: application, academic, essay, recommendation, social"
}
```

### Criteria Not Found (404)
```json
{
  "detail": "Essay criteria not found for Delaney_Wings"
}
```

### Internal Server Error (500)
```json
{
  "detail": "Error message details"
}
```

---

## API Documentation

The criteria endpoints are automatically included in the OpenAPI documentation:

- **Swagger UI:** http://localhost:8200/docs
- **ReDoc:** http://localhost:8200/redoc
- **OpenAPI JSON:** http://localhost:8200/openapi.json
- **OpenAPI YAML:** http://localhost:8200/openapi.yml

---

## Agent Configuration Endpoints

### 1. Get All Agents Configuration

**Endpoint:** `GET /agents`

**Description:** Get complete agent configuration including scoring weights and evaluation details.

**Response:**
```json
{
  "scholarship_name": "Delaney_Wings",
  "description": "Agent configuration for Valerie Delaney Memorial Scholarship application processing",
  "version": "1.0.0",
  "agents": [
    {
      "name": "application",
      "display_name": "Application Agent",
      "description": "Extracts and analyzes applicant information from the main application PDF",
      "weight": 0.20,
      "enabled": true,
      "required": true,
      "evaluates": [
        "Basic eligibility",
        "Contact information",
        "Educational background",
        "Aviation experience",
        "Career goals"
      ],
      "criteria": "data/Delaney_Wings/criteria/application_criteria.txt"
    },
    {
      "name": "academic",
      "display_name": "Academic Agent",
      "weight": 0.25,
      "evaluates": [
        "Educational background",
        "Academic achievements",
        "Aviation certifications",
        "Work experience",
        "Skills and qualifications"
      ]
    },
    {
      "name": "essay",
      "display_name": "Essay Agent",
      "weight": 0.30,
      "evaluates": [
        "Aviation passion and motivation",
        "Career goals clarity",
        "Personal character traits",
        "Leadership and community service",
        "Alignment with WAI values"
      ]
    },
    {
      "name": "recommendation",
      "display_name": "Recommendation Agent",
      "weight": 0.25,
      "evaluates": [
        "Recommender credibility",
        "Specific examples and evidence",
        "Character assessment",
        "Professional qualities",
        "Consistency across letters"
      ]
    }
  ],
  "scoring_agents": ["application", "recommendation", "academic", "essay"],
  "total_weight": 1.00
}
```

**Example:**
```bash
curl http://localhost:8200/agents
```

---

### 2. Get Specific Agent Configuration

**Endpoint:** `GET /agents/{agent_name}`

**Description:** Get configuration for a specific agent.

**Parameters:**
- `agent_name` (path): Name of the agent
  - Valid values: `application`, `academic`, `essay`, `recommendation`, `attachment`

**Response:**
```json
{
  "scholarship": "Delaney_Wings",
  "agent": {
    "name": "application",
    "display_name": "Application Agent",
    "description": "Extracts and analyzes applicant information from the main application PDF",
    "weight": 0.20,
    "enabled": true,
    "required": true,
    "evaluates": [
      "Basic eligibility",
      "Contact information",
      "Educational background",
      "Aviation experience",
      "Career goals"
    ],
    "criteria": "data/Delaney_Wings/criteria/application_criteria.txt",
    "schema": "schemas/application_agent_schema.json",
    "output_directory": "outputs/applications",
    "output_file": "{wai_number}_application_analysis.json"
  }
}
```

**Examples:**

```bash
# Get application agent config
curl http://localhost:8200/agents/application

# Get academic agent config
curl http://localhost:8200/agents/academic

# Get essay agent config
curl http://localhost:8200/agents/essay

# Get recommendation agent config
curl http://localhost:8200/agents/recommendation

# Get attachment agent config (non-scoring)
curl http://localhost:8200/agents/attachment
```

**Error Response (Not Found):**
```json
{
  "detail": "Agent 'invalid_agent' not found in configuration"
}
```

---

## Agent Scoring Weights

### Understanding Weights

Each scoring agent has a weight that determines its contribution to the final score:

| Agent | Weight | Contribution |
|-------|--------|--------------|
| Application | 0.20 | 20% |
| Academic | 0.25 | 25% |
| Essay | 0.30 | 30% |
| Recommendation | 0.25 | 25% |
| **Total** | **1.00** | **100%** |

**Final Score Calculation:**
```
Final Score = (Application Score × 0.20) +
              (Academic Score × 0.25) +
              (Essay Score × 0.30) +
              (Recommendation Score × 0.25)
```

### Non-Scoring Agents

The **Attachment Agent** does not contribute to scoring:
- Processes and redacts PII from documents
- Extracts text from PDFs
- Prerequisite for other agents
- No weight assigned

---

## Use Cases

### 1. Display Scoring Breakdown
```javascript
// Fetch agent configuration
const response = await fetch('http://localhost:8200/agents');
const config = await response.json();

// Display scoring weights
config.agents
  .filter(a => config.scoring_agents.includes(a.name))
  .forEach(agent => {
    console.log(`${agent.display_name}: ${agent.weight * 100}%`);
  });
```

### 2. Show What Each Agent Evaluates
```javascript
// Get specific agent details
const response = await fetch('http://localhost:8200/agents/essay');
const data = await response.json();

// Display evaluation criteria
console.log(`${data.agent.display_name} evaluates:`);
data.agent.evaluates.forEach(item => {
  console.log(`- ${item}`);
});
```

### 3. Validate Scoring Configuration
```python
import requests

# Get agent configuration
response = requests.get('http://localhost:8200/agents')
config = response.json()

# Verify weights sum to 1.0
total_weight = sum(
    agent['weight']
    for agent in config['agents']
    if agent['name'] in config['scoring_agents']
)

print(f"Total weight: {total_weight}")
assert abs(total_weight - 1.0) < 0.01, "Weights must sum to 1.0"
```

---

## Integration with Criteria Endpoints

Agents and criteria work together:

```javascript
// Get agent configuration
const agentResponse = await fetch('http://localhost:8200/agents/academic');
const agentData = await agentResponse.json();

// Get the criteria file path from agent config
const criteriaPath = agentData.agent.criteria;
console.log(`Criteria file: ${criteriaPath}`);

// Fetch the actual criteria content
const criteriaResponse = await fetch('http://localhost:8200/criteria/academic');
const criteriaData = await criteriaResponse.json();

console.log(`Criteria content:\n${criteriaData.content}`);
```

---

## Testing

### Run Agent Configuration Tests
```bash
# Run only agent tests
python3 -m pytest tests/test_api_agents.py -v

# Run all configuration tests (agents + criteria)
python3 -m pytest tests/test_api_agents.py tests/test_api_criteria.py -v
```

### Test Results
```
tests/test_api_agents.py::test_get_agents_config PASSED
tests/test_api_agents.py::test_agents_config_structure PASSED
tests/test_api_agents.py::test_get_application_agent PASSED
tests/test_api_agents.py::test_get_academic_agent PASSED
tests/test_api_agents.py::test_get_essay_agent PASSED
tests/test_api_agents.py::test_get_recommendation_agent PASSED
tests/test_api_agents.py::test_get_attachment_agent PASSED
tests/test_api_agents.py::test_get_invalid_agent PASSED
tests/test_api_agents.py::test_scoring_agents_weights_sum_to_one PASSED
tests/test_api_agents.py::test_all_scoring_agents_have_weights PASSED
tests/test_api_agents.py::test_agent_evaluates_field PASSED
tests/test_api_agents.py::test_agent_criteria_field PASSED

12 passed in 0.05s
```

---

## Summary

**New Endpoints Added:**
- `GET /criteria` - List all available criteria
- `GET /criteria/{criteria_type}` - Get specific criteria content
- `GET /agents` - Get complete agent configuration
- `GET /agents/{agent_name}` - Get specific agent configuration

**Test Coverage:**
- 20 new tests added (8 criteria + 12 agents)
- All tests passing (61 total tests)
- Comprehensive validation of configuration endpoints

**Benefits:**
- **Transparent Evaluation:** Complete visibility into scoring methodology
- **Scoring Weights:** Clear breakdown of how final scores are calculated
- **Evaluation Details:** What each agent evaluates and why
- **Criteria Access:** Detailed scoring criteria for each evaluation type
- **Multi-Tenancy:** Each scholarship has its own configuration
- **Consistency:** Ensures uniform evaluation across all applications

---

**Last Updated:** 2025-12-10
**Version:** 2.0.0
**Author:** Pat G Cappelaere, IBM Federal Consulting