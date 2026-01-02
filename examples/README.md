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
python examples/process_applicants.py

# Process Evans Wings with default 20 applicants
python examples/process_applicants.py Evans_Wings

# Process 10 applicants from Evans Wings
python examples/process_applicants.py Evans_Wings --max-applicants 10

# Process all applicants (use large number)
python examples/process_applicants.py Delaney_Wings --max-applicants 1000

# Show help
python examples/process_applicants.py --help
```

**Arguments:**
- `scholarship` (optional): Scholarship folder name (e.g., `Delaney_Wings`, `Evans_Wings`, `WAI-Harvard-June-2026`)
- `--max-applicants` (optional): Maximum number of applicants to process (default: 20)

**Output:**
- Processed applications in `outputs/<scholarship>/Applications/`
- Summary CSV in `outputs/<scholarship>/summary.csv`
- Statistics JSON in `outputs/<scholarship>/statistics.json`
- Logs in `logs/wai_processing.log`

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
  Statistics: outputs/Evans_Wings/statistics.json
  Complete applications: 18/20

============================================================
Check outputs/Evans_Wings/ for results
============================================================
```

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
- Check logs in `logs/wai_processing.log`
- Verify LLM models are available (Ollama running)
- Ensure sufficient disk space for outputs

## Related Documentation

- [Scholarship Process](../docs/SCHOLARSHIP_PROCESS.md) — End-to-end configuration workflow
- [Agent Architecture](../docs/AGENT_ARCHITECTURE.md) — How agents work
- [Multi-Tenancy Design](../docs/MULTI_TENANCY_DESIGN.MD) — Multi-scholarship architecture
- [API Server Architecture](../docs/API_SERVER_ARCHITECTURE.MD) — API design

---

**Last Updated**: 2026-01-01  
**Maintained By**: Pat G Cappelaere, IBM Federal Consulting