# Scholarship Processing Examples

This directory contains example scripts for processing scholarship applications.

## Available Scripts

### process_applicants.py

Process scholarship applicants with configurable options for any scholarship.

**Features:**
- Support for multiple scholarships (Delaney_Wings, Evans_Wings)
- Configurable number of applicants to process
- Parallel processing for speed
- Comprehensive summary reports
- Full workflow execution (all stages)

**Usage:**

```bash
# Process Delaney Wings with default 20 applicants
python examples/process_applicants.py --scholarship Delaney_Wings

# Process Evans Wings with default 20 applicants
python examples/process_applicants.py --scholarship Evans_Wings

# Process 10 applicants from Evans Wings
python examples/process_applicants.py --scholarship Evans_Wings --max-applicants 10

# Process all applicants (use large number)
python examples/process_applicants.py --scholarship Delaney_Wings --max-applicants 1000

# Use a non-default outputs directory
python examples/process_applicants.py --scholarship Delaney_Wings --outputs-dir outputs

# Skip specific workflow stages
python examples/process_applicants.py --scholarship Delaney_Wings --skip-stages attachments,scoring

# Control model and retry behavior
python examples/process_applicants.py --scholarship Delaney_Wings --model ollama/llama3.2:3b --fallback-model ollama/llama3:latest --max-retries 3

# Disable preflight check (process all applicants without validation)
python examples/process_applicants.py --scholarship Delaney_Wings --no-preflight

# Run preflight in strict mode (abort if any errors found instead of skipping)
python examples/process_applicants.py --scholarship Delaney_Wings --preflight-strict

# Show help
python examples/process_applicants.py --help
```

**Arguments:**
- `--scholarship` (optional): Scholarship folder name under `data/` (e.g., `Delaney_Wings`, `Evans_Wings`, `WAI-Harvard-June-2026`)
- `--max-applicants` (optional): Maximum number of applicants to process (default: 20)
- `--outputs-dir` (optional): Base output directory (default: `outputs/`)
- `--model` / `--fallback-model` / `--max-retries` (optional): LLM execution controls (defaults match the other examples)
- `--skip-stages` (optional): Comma-separated list (e.g., `attachments,scoring,summary`)
- `--no-parallel` (optional): Disable parallel stage execution per applicant
- `--stop-on-error` (optional): Stop when an applicant fails
- `--preflight` (default): Run preflight validation before processing (detect missing/corrupt files)
- `--no-preflight` (optional): Disable preflight validation (process all applicants without checks)
- `--preflight-strict` (optional): Abort if any preflight errors found (default: skip invalid applicants)

**Output:**
- Per-applicant outputs in `outputs/<scholarship>/<wai_number>/`
  - `application_data.json` (extraction)
  - `attachments/*.txt` (attachment preprocessing)
  - `application_analysis.json`, `resume_analysis.json`, `essay_analysis.json`, `recommendation_analysis.json` (scoring)
- Summary CSV in `outputs/<scholarship>/summary.csv`
- Statistics report in `outputs/<scholarship>/statistics.txt`
- Logs in `logs/process_<scholarship>_<timestamp>.log` (e.g., `process_Delaney_Wings_20260102_120600.log`)

**Example Output:**
```
============================================================
Processing 20 Applicants - Evans_Wings
============================================================
Scholarship folder: data/Evans_Wings
Outputs directory: outputs/Evans_Wings

Processing Complete!
============================================================
Total applicants processed: 20
Successful: 18
Failed: 2
Total duration: 45.32 seconds

Summary files generated:
  CSV: outputs/Evans_Wings/summary.csv
  Statistics: outputs/Evans_Wings/statistics.txt
  Complete applications: 18/20

============================================================
Check outputs/Evans_Wings/ for results
============================================================
```

### run_application_agent.py

Run **application extraction** for a single applicant (writes `application_data.json`).

```bash
python examples/run_application_agent.py --scholarship Delaney_Wings --wai 75179
```

Common options:
- `--outputs-dir outputs`
- `--model ollama/llama3.2:3b`
- `--fallback-model ollama/llama3:latest`
- `--max-retries 3`

### run_attachment_agent.py

Run **attachment preprocessing** (PII removal + text extraction) for a scholarship (writes `outputs/<scholarship>/<wai>/attachments/*.txt`).

```bash
python examples/run_attachment_agent.py --scholarship Delaney_Wings --max-wai-folders 5 --skip-processed
```

Common options:
- `--outputs-dir outputs`
- `--model ollama/llama3.2:1b`
- `--fallback-model ollama/llama3:latest`
- `--max-files-per-folder 5`
- `--overwrite`

### run_single_wai.py

Run a **single scoring artifact** for one applicant (and automatically runs extraction/attachments first if missing).

```bash
python examples/run_single_wai.py --scholarship Delaney_Wings --wai 75179 --agent recommendation
python examples/run_single_wai.py --scholarship Delaney_Wings --wai 75179 --agent resume
python examples/run_single_wai.py --scholarship Delaney_Wings --wai 75179 --agent essay
python examples/run_single_wai.py --scholarship Delaney_Wings --wai 75179 --agent application
```

### run_complete_workflow_single.py

Run the workflow stages for a single applicant:

- `application_extract` → `attachments` → `scoring`

```bash
python examples/run_complete_workflow_single.py --scholarship Delaney_Wings --wai 75179
```

Backward-compatible positional usage still works:

```bash
python examples/run_complete_workflow_single.py 75179 Delaney_Wings
```

### run_summary_agent.py

Generate summary CSV/statistics for a scholarship based on outputs:

```bash
python examples/run_summary_agent.py --scholarship Delaney_Wings
```

### analyze_log.py

Analyze log files for errors, warnings, and failures using LLM.

```bash
# Analyze the most recent log file (saves to logs/process_*.md)
python examples/analyze_log.py --latest

# Analyze a specific log file (saves to same path with .md extension)
python examples/analyze_log.py logs/process_Delaney_Wings_20260102_120600.log
# → saves to logs/process_Delaney_Wings_20260102_120600.md

# Save to a custom path
python examples/analyze_log.py --latest --output reports/analysis.md

# Print to console instead of saving
python examples/analyze_log.py --latest --stdout

# Just see filtered log content (no LLM analysis)
python examples/analyze_log.py --latest --raw
```

**Features:**
- Pre-filters logs to extract ERROR, WARNING, and failure-related lines
- Uses Claude to provide structured analysis with failed applicant details
- Automatically saves report alongside the log file
- Identifies failed applicants and root causes
- Provides actionable recommendations

**Options:**
- `--latest`: Analyze the most recent log in `logs/`
- `--output FILE`: Save to custom path (default: same as input with .md extension)
- `--stdout`: Print to console instead of saving to file
- `--model`: LLM model to use (default: `anthropic/claude-sonnet-4-20250514`)
- `--fallback-model`: Fallback if primary fails (default: `ollama/llama3.2:3b`)
- `--raw`: Show filtered content without LLM analysis

For manual analysis with Claude/ChatGPT, see [docs/LOG_ANALYSIS_PROMPT.md](../docs/LOG_ANALYSIS_PROMPT.md).

## Multi-Tenancy Support

The processing script is fully compatible with the multi-tenancy system:

- Each scholarship's data is isolated in its own folder
- Output files are separated by scholarship
- Users can only process scholarships they have access to
- Admin users can process any scholarship

## Adding New Scholarships

Adding a new scholarship is straightforward:

1. **Create data folder with configuration**:
   ```bash
   mkdir -p data/New_Scholarship
   ```

2. **Create `config.yml`** with scholarship criteria (see `docs/SCHOLARSHIP_PROCESS.md`)

3. **Generate artifacts**:
   ```bash
   python scripts/generate_all.py data/New_Scholarship
   ```

4. **Use it**:
   ```python
   from utils.config import Config as config
   
   # Dynamic folder resolution (no code changes needed)
   scholarship_folder = config.get_scholarship_folder("New_Scholarship")
   ```

That's it! The system dynamically discovers scholarships by folder name.

## Requirements

- Python 3.8+
- All dependencies from `requirements.txt`
- Scholarship configuration: `data/<scholarship>/config.yml`
- Generated artifacts: Run `python scripts/generate_all.py data/<scholarship>`
- Application files in `data/<scholarship>/Applications/`
- Valid `.env` configuration

## Troubleshooting

**Error: Scholarship folder does not exist**
- Ensure the data folder exists: `ls -la data/<scholarship>/`
- Check `.env` file for correct folder paths

**Error: Unknown scholarship**
- Ensure the scholarship folder exists under `data/`
- Check spelling and capitalization (must match folder name exactly)

**No applicants processed**
- Verify applications exist in `data/<scholarship>/Applications/`
- Check that application folders contain required files

**Processing fails**
- Analyze logs: `python examples/analyze_log.py --latest`
- Or check manually: `logs/process_<scholarship>_<timestamp>.log`
- Verify LLM models are available (Ollama running)
- Ensure sufficient disk space for outputs

## Related Documentation

- [Scholarship Process](../docs/SCHOLARSHIP_PROCESS.md) — End-to-end configuration workflow
- [Agent Architecture](../docs/AGENT_ARCHITECTURE.md) — How agents work
- [Log Analysis Prompt](../docs/LOG_ANALYSIS_PROMPT.md) — Manual log analysis with LLMs
- [Multi-Tenancy Design](../docs/MULTI_TENANCY_DESIGN.MD) — Multi-scholarship architecture
- [API Server Architecture](../docs/API_SERVER_ARCHITECTURE.MD) — API design

---

**Last Updated**: 2026-01-01  
**Maintained By**: Pat G Cappelaere, IBM Federal Consulting