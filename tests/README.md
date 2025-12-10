# API Tests

Comprehensive test suite for the Bee Agents API.

## Test Structure

```
tests/
├── __init__.py              # Package initialization
├── conftest.py              # Pytest fixtures and configuration
├── test_api_health.py       # Health and status endpoint tests
├── test_api_scores.py       # Score endpoint tests
├── test_api_statistics.py   # Statistics endpoint tests
├── test_api_analysis.py     # Analysis endpoint tests
└── README.md                # This file
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-cov httpx
```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=bee_agents --cov-report=html

# Run specific test file
pytest tests/test_api_health.py

# Run specific test
pytest tests/test_api_health.py::test_root_endpoint
```

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest tests/ -n auto
```

## Test Coverage

### Health & Status Tests (`test_api_health.py`)
- ✅ Root endpoint returns API information
- ✅ Health check endpoint returns status
- ✅ OpenAPI YAML spec is available
- ✅ OpenAPI JSON spec is available

### Score Tests (`test_api_scores.py`)
- ✅ Get top scores with default limit
- ✅ Get top scores with custom limit
- ✅ Limit parameter validation
- ✅ Top scores structure validation
- ✅ Get individual score for valid WAI number
- ✅ Get individual score for invalid WAI number (404)
- ✅ Top scores are sorted in descending order

### Statistics Tests (`test_api_statistics.py`)
- ✅ Get statistics for all applications
- ✅ Statistics scores are within valid ranges
- ✅ Score distribution has correct structure
- ✅ Distribution counts sum to total applications
- ✅ Statistics are internally consistent

### Analysis Tests (`test_api_analysis.py`)
- ✅ Get application analysis for valid WAI number
- ✅ Get application analysis for invalid WAI number (404)
- ✅ Get academic analysis (when available)
- ✅ Get essay analysis for essays 1 and 2
- ✅ Invalid essay number returns error
- ✅ Get recommendation analysis for recommendations 1 and 2
- ✅ Invalid recommendation number returns error
- ✅ Analysis endpoints return consistent data

## Test Fixtures

### `test_client` (module scope)
Provides a FastAPI TestClient initialized with the Delaney_Wings scholarship data.

### `sample_wai_number` (module scope)
Returns a valid WAI number from the test data for use in tests.

### `invalid_wai_number` (function scope)
Returns an invalid WAI number for testing error cases.

## Writing New Tests

### Example Test

```python
def test_new_endpoint(test_client):
    """Test description."""
    response = test_client.get("/new_endpoint")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "expected_field" in data
    assert data["expected_field"] == "expected_value"
```

### Using Fixtures

```python
def test_with_wai_number(test_client, sample_wai_number):
    """Test using a valid WAI number."""
    response = test_client.get(f"/endpoint/{sample_wai_number}")
    
    assert response.status_code == 200
```

## Test Data

Tests use the actual data from `outputs/Delaney_Wings/` directory. Ensure this data exists before running tests:

```bash
# Check if test data exists
ls -la outputs/Delaney_Wings/
```

If test data is missing, process some applications first:

```bash
python examples/run_application_agent.py
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run tests
      run: pytest tests/ --cov=bee_agents --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

## Troubleshooting

### Import Errors

If you see import errors, ensure the project root is in your Python path:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest tests/
```

Or run tests as a module:

```bash
python -m pytest tests/
```

### Service Not Initialized

If tests fail with "Service not initialized", ensure the `outputs/Delaney_Wings/` directory exists and contains application data.

### Fixture Not Found

If pytest can't find fixtures, ensure `conftest.py` is in the tests directory and properly configured.

## Best Practices

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Clear Names**: Use descriptive test names that explain what is being tested
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification
4. **Error Cases**: Test both success and failure scenarios
5. **Data Validation**: Verify response structure and data types, not just status codes

## Coverage Goals

- **Line Coverage**: > 80%
- **Branch Coverage**: > 70%
- **Critical Paths**: 100% coverage for all API endpoints

## Future Tests

Potential areas for additional testing:

- [ ] Performance tests (response time, concurrent requests)
- [ ] Load tests (stress testing with many requests)
- [ ] Integration tests with actual LLM processing
- [ ] Security tests (authentication, authorization)
- [ ] Edge cases (malformed requests, special characters)