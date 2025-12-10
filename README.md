# WAI 2026 Python - Scholarship Application Processing

This project contains an Application Agent for processing scholarship applications and extracting applicant information using AI.

## Features

- **Application Agent**: Automatically processes scholarship applications
- **Document Parsing**: Uses Docling to parse PDF and DOCX files (optimized with single converter instance)
- **AI Extraction**: Uses LLM to extract applicant name, city, and country
- **Retry Logic**: Automatic retry with configurable attempts (default: 3)
- **Fallback Model**: Optional fallback to different model if primary fails
- **JSON Output**: Saves extracted data as JSON files in organized output structure
- **Performance Tracking**: Detailed timing metrics for processing

## Project Structure

```
wai_2026_python/
├── agents/
│   └── application_agent/      # Main Application Agent
│       ├── agent.py            # Agent implementation
│       └── prompts.py          # LLM prompts
├── utils/
│   ├── folder_scanner.py       # Scan scholarship folders
│   ├── file_identifier.py      # Identify application files
│   ├── document_parser.py      # Parse documents with Docling
│   └── json_writer.py          # Save JSON output
├── models/
│   └── application_data.py     # Data models
├── examples/
│   └── run_application_agent.py # Example usage
└── data/
    └── Delaney_Wings/
        └── Applications/       # Scholarship applications
```

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv venv
```

### 2. Activate Virtual Environment

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and customize it:

```bash
cp .env.example .env
```

Edit `.env` to configure:
- **LLM models** (Ollama or OpenAI)
- **Processing limits** (max applications, retries)
- **Directory paths** (data, outputs, schemas)
- **PII redaction settings**
- **Logging configuration**

See `.env.example` for all available options and defaults.

### 5. Install and Run Ollama

The Application Agent uses Ollama for local LLM inference.

1. Install Ollama from https://ollama.ai
2. Pull the required models:
```bash
ollama pull llama3.2:1b          # Primary model
ollama pull llama3:latest        # Optional fallback model
```
3. Make sure Ollama is running (it starts automatically after installation)

## Usage

### Using Configuration File (Recommended)

The easiest way to run the system is using the configuration from `.env`:

```python
from utils.config import config
from agents.application_agent import ApplicationAgent

# Initialize the agent
agent = ApplicationAgent()

# Process applications using config values
result = agent.process_applications(
    scholarship_folder=str(config.DELANEY_WINGS_FOLDER / "Applications"),
    max_applications=config.MAX_APPLICATIONS,
    skip_processed=config.SKIP_PROCESSED,
    overwrite=config.OVERWRITE_EXISTING,
    output_dir=str(config.OUTPUTS_DIR),
    model=config.PRIMARY_MODEL,
    fallback_model=config.FALLBACK_MODEL,
    max_retries=config.MAX_RETRIES
)

# Check results
print(f"Successful: {result.successful}/{result.total}")
print(f"Failed: {result.failed}")
```

### Manual Configuration (Advanced)

You can also override configuration values programmatically:

```python
from agents.application_agent import ApplicationAgent

# Initialize the agent
agent = ApplicationAgent()

# Process applications with custom settings
result = agent.process_applications(
    scholarship_folder="data/Delaney_Wings/Applications",
    max_applications=10,           # Optional: limit number to process
    skip_processed=True,           # Skip already processed applications
    overwrite=False,               # Don't overwrite existing JSON files
    model="ollama/llama3.2:1b",    # Primary model to use
    fallback_model="ollama/llama3:latest",  # Optional: fallback if primary fails
    max_retries=3                  # Number of retry attempts per model
)

# Check results
print(f"Successful: {result.successful}/{result.total}")
print(f"Failed: {result.failed}")
print(f"Total duration: {result.total_duration:.2f} seconds")
print(f"Average per application: {result.avg_duration_per_app:.2f} seconds")
```

### Retry and Fallback Behavior

The agent implements intelligent retry logic with automatic quality checking:

1. **Primary Model Attempts**: Tries extraction with primary model up to `max_retries` times
2. **Quality Check**: If extraction succeeds but returns "Unknown" for name, city, or country, automatically retries
3. **Fallback Model**: If primary model fails or consistently returns Unknown values, tries `fallback_model`
4. **Fallback Retries**: The fallback model also gets `max_retries` attempts with quality checking
5. **Best Result**: Returns the best result obtained, preferring complete data over partial data
6. **Final Failure**: Only marks as failed if all attempts with both models fail

**Example Flow:**
- Attempt 1 (llama3.2:1b): Extracts name but city/country are "Unknown" → Retry
- Attempt 2 (llama3.2:1b): Successfully extracts all fields → Success!

This ensures maximum data quality and success rate while handling temporary LLM issues or model-specific limitations.

### Run Example Scripts

**Using configuration file (recommended):**
```bash
python examples/run_with_config.py
```

**Using manual configuration:**
```bash
python examples/run_application_agent.py
```

## How It Works

1. **Scan**: The agent scans the scholarship folder for WAI number subfolders
2. **Identify**: For each folder, it identifies the application file (pattern: `{WAI}_{xx}.pdf`)
3. **Parse**: Uses Docling to extract text from the PDF/DOCX document
4. **Extract**: Uses LLM to extract applicant name, city, and country
5. **Save**: Saves the extracted data as JSON in `outputs/application/{scholarship}/{WAI}/` folder
6. **Track**: Records timing information for performance monitoring

## File Patterns

### Input Files
- Application files: `{WAI}_{xx}.pdf` or `{WAI}_{xx}.docx`
- Example: `75179_19.pdf`, `77747_1.pdf`

### Output Files
- JSON files saved in: `outputs/application/{scholarship_name}/{WAI}/{WAI}_{xx}_application.json`
- Example: `outputs/application/Delaney_Wings/75179/75179_19_application.json`

### Output Format

```json
{
  "wai_number": "75179",
  "name": "John Doe",
  "city": "Boston",
  "country": "United States",
  "source_file": "75179_19.pdf",
  "processed_date": "2025-12-05T17:54:00Z"
}
```

## Configuration

### LLM Model

The agent uses Ollama for local LLM inference. Specify the model in `process_applications`:

```python
agent = ApplicationAgent()

# Use Ollama with llama3.2:1b (default)
result = agent.process_applications(
    scholarship_folder="data/Delaney_Wings/Applications",
    model="ollama/llama3.2:1b"
)

# Use a different Ollama model
result = agent.process_applications(
    scholarship_folder="data/Delaney_Wings/Applications",
    model="ollama/llama3.2:3b"
)

# Or use OpenAI (requires OPENAI_API_KEY)
result = agent.process_applications(
    scholarship_folder="data/Delaney_Wings/Applications",
    model="gpt-4o-mini"
)
```

**Note**: Make sure Ollama is running and the model is pulled before use:
```bash
ollama pull llama3.2:1b
```

### Processing Options

- `scholarship_folder`: Path to the scholarship applications folder (required)
- `max_applications`: Limit the number of applications to process (optional)
- `skip_processed`: Skip applications that already have JSON output (default: True)
- `overwrite`: Overwrite existing JSON files (default: False)
- `output_dir`: Base output directory for JSON files (default: "outputs")
- `model`: LLM model to use (default: "ollama/llama3.2:1b")

### Output Structure

```
outputs/
└── application/
    ├── Delaney_Wings/
    │   ├── 75179/
    │   │   └── 75179_19_application.json
    │   ├── 77747/
    │   │   └── 77747_1_application.json
    │   └── ...
    └── Evans_Wings/
        └── ...
```

## Error Handling & Monitoring

The agent includes comprehensive error handling and performance tracking:
- Logs all errors with details
- Continues processing even if individual applications fail
- Returns a summary with success/failure counts
- Provides detailed error messages for debugging
- **Tracks timing information**:
  - Total processing duration
  - Average time per application
  - Start and end timestamps

### Processing Result

The `ProcessingResult` object includes:
```python
result.total              # Total applications processed
result.successful         # Successfully processed count
result.failed            # Failed count
result.errors            # List of error details
result.total_duration    # Total time in seconds
result.avg_duration_per_app  # Average time per application
```

## Dependencies

Key dependencies:
- `docling`: Document parsing (PDF/DOCX)
- `litellm`: LLM interface
- `pydantic`: Data validation
- `beeai-framework`: Agent framework

See `requirements.txt` for complete list.

## Development

### Adding New Features

1. Create new utilities in `utils/`
2. Update data models in `models/`
3. Extend the agent in `agents/application_agent/`

### Testing

Test with a small number of applications first:

```python
result = agent.process_applications(
    scholarship_folder="data/Delaney_Wings/Applications",
    max_applications=5  # Test with 5 applications
)
```

## License

[Add your license here]

## Contact

[Add contact information]