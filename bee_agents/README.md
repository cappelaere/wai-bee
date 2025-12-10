# Bee Agents - Scholarship Analysis API

FastAPI server for accessing scholarship application analysis data.

## Features

- **Scholarship-specific**: API is initialized for a specific scholarship
- **RESTful endpoints**: Clean, intuitive API design
- **Comprehensive data access**: Scores, statistics, and detailed analyses
- **Auto-generated documentation**: Interactive API docs at `/docs`
- **Type-safe**: Full Pydantic validation for requests and responses

## Installation

Ensure you have the required dependencies:

```bash
pip install fastapi uvicorn pydantic
```

## Quick Start

### Method 1: Using the built-in runner

```bash
python -m bee_agents.api --scholarship Delaney_Wings --port 8200
```

### Method 2: Using uvicorn directly

First, initialize the service in your code:

```python
from bee_agents.api import initialize_service, app

# Initialize for a specific scholarship
initialize_service("Delaney_Wings")

# Then run with uvicorn
# uvicorn bee_agents.api:app --reload --port 8200
```

Or create a startup script:

```python
# run_api.py
from bee_agents.api import initialize_service, app
import uvicorn

if __name__ == "__main__":
    initialize_service("Delaney_Wings")
    uvicorn.run(app, host="0.0.0.0", port=8200)
```

## API Endpoints

### Health & Status

- `GET /` - Root endpoint with API info
- `GET /health` - Health check

### Scores

- `GET /top_scores?limit=10` - Get top scoring applications
- `GET /score/{wai_number}` - Get score for specific application

### Statistics

- `GET /statistics` - Get aggregated statistics for all applications

### Detailed Analysis

- `GET /application/{wai_number}` - Get detailed application analysis
- `GET /academic/{wai_number}` - Get academic analysis
- `GET /essay/{wai_number}/{essay_number}` - Get essay analysis (1 or 2)
- `GET /recommendation/{wai_number}/{rec_number}` - Get recommendation analysis (1 or 2)

## API Documentation

Once the server is running, visit:

- **Interactive docs**: http://localhost:8200/docs
- **ReDoc**: http://localhost:8200/redoc

## Usage Examples

### Get Top 10 Scores

```bash
curl http://localhost:8200/top_scores?limit=10
```

Response:
```json
{
  "scholarship": "Delaney_Wings",
  "total_applications": 156,
  "top_scores": [
    {
      "wai_number": "75179",
      "overall_score": 95,
      "completeness_score": 28,
      "validity_score": 29,
      "attachment_score": 38,
      "summary": "Excellent application with complete information"
    },
    ...
  ]
}
```

### Get Individual Score

```bash
curl http://localhost:8200/score/75179
```

Response:
```json
{
  "wai_number": "75179",
  "overall_score": 95,
  "completeness_score": 28,
  "validity_score": 29,
  "attachment_score": 38,
  "summary": "Excellent application with complete information"
}
```

### Get Statistics

```bash
curl http://localhost:8200/statistics
```

Response:
```json
{
  "scholarship": "Delaney_Wings",
  "total_applications": 156,
  "average_score": 82.5,
  "median_score": 84.0,
  "min_score": 45,
  "max_score": 98,
  "score_distribution": {
    "90-100": 25,
    "80-89": 78,
    "70-79": 35,
    "60-69": 12,
    "50-59": 4,
    "0-49": 2
  }
}
```

### Get Application Analysis

```bash
curl http://localhost:8200/application/75179
```

Response:
```json
{
  "wai_number": "75179",
  "summary": "The scholarship application is mostly complete and valid",
  "scores": {
    "completeness_score": 28,
    "validity_score": 29,
    "attachment_score": 38,
    "overall_score": 95
  },
  "score_breakdown": {
    "completeness_reasoning": "All required fields are present...",
    "validity_reasoning": "Data is valid and properly formatted...",
    "attachment_reasoning": "All required attachments present..."
  },
  "completeness_issues": [],
  "validity_issues": [],
  "attachment_status": "All attachments present and valid",
  "processed_date": "2025-12-07T22:38:42.290242+00:00",
  "source_file": "75179_19.pdf"
}
```

### Get Academic Analysis

```bash
curl http://localhost:8200/academic/75179
```

### Get Essay Analysis

```bash
curl http://localhost:8200/essay/75179/1
curl http://localhost:8200/essay/75179/2
```

### Get Recommendation Analysis

```bash
curl http://localhost:8200/recommendation/75179/1
curl http://localhost:8200/recommendation/75179/2
```

## Python Client Example

```python
import requests

# Base URL
base_url = "http://localhost:8200"

# Get top scores
response = requests.get(f"{base_url}/top_scores?limit=5")
top_scores = response.json()
print(f"Top 5 applications:")
for score in top_scores['top_scores']:
    print(f"  {score['wai_number']}: {score['overall_score']}/100")

# Get specific application
wai_number = "75179"
response = requests.get(f"{base_url}/application/{wai_number}")
analysis = response.json()
print(f"\nApplication {wai_number}:")
print(f"  Summary: {analysis['summary']}")
print(f"  Overall Score: {analysis['scores']['overall_score']}/100")

# Get statistics
response = requests.get(f"{base_url}/statistics")
stats = response.json()
print(f"\nStatistics:")
print(f"  Total Applications: {stats['total_applications']}")
print(f"  Average Score: {stats['average_score']}")
print(f"  Score Distribution: {stats['score_distribution']}")
```

## Error Handling

The API returns standard HTTP status codes:

- `200` - Success
- `404` - Resource not found (e.g., WAI number doesn't exist)
- `422` - Validation error (e.g., invalid parameters)
- `500` - Internal server error
- `503` - Service not initialized

Error responses follow this format:

```json
{
  "detail": "Application 99999 not found"
}
```

## Configuration

### Command Line Arguments

```bash
python -m bee_agents.api \
  --scholarship Delaney_Wings \
  --output-dir outputs \
  --host 0.0.0.0 \
  --port 8200
```

Arguments:
- `--scholarship`: Scholarship name (required)
- `--output-dir`: Base output directory (default: "outputs")
- `--host`: Host to bind to (default: "0.0.0.0")
- `--port`: Port to bind to (default: 8200)

## Development

### Running in Development Mode

```bash
uvicorn bee_agents.api:app --reload --port 8200
```

Note: You must initialize the service before running in development mode. Create a startup script or modify `api.py` to call `initialize_service()` at module level.

### Testing

```bash
# Test health endpoint
curl http://localhost:8200/health

# Test with different scholarships
python -m bee_agents.api --scholarship Evans_Wings --port 8001
```

## Architecture

```
bee_agents/
├── __init__.py          # Package initialization
├── api.py               # FastAPI application and endpoints
├── data_service.py      # Data loading and aggregation
├── models.py            # Pydantic models for API
└── README.md            # This file
```

### Components

1. **api.py**: FastAPI application with all endpoints
2. **data_service.py**: Service layer for loading JSON files from outputs directory
3. **models.py**: Pydantic models for request/response validation

## License

MIT License - See main project LICENSE file

## Author

Pat G Cappelaere, IBM Federal Consulting