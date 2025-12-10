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
- `scholarship` (optional): Scholarship to process. Choices: `Delaney_Wings` (default), `Evans_Wings`
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

To add support for a new scholarship:

1. **Add to configuration** (`utils/config.py`):
   ```python
   NEW_SCHOLARSHIP_FOLDER: Path = Path(os.getenv("NEW_SCHOLARSHIP_FOLDER", "data/New_Scholarship"))
   ```

2. **Update get_scholarship_folder method**:
   ```python
   @classmethod
   def get_scholarship_folder(cls, scholarship_name: str) -> Optional[Path]:
       if scholarship_name == "New_Scholarship":
           return cls.NEW_SCHOLARSHIP_FOLDER
       # ... existing code
   ```

3. **Update script choices**:
   ```python
   parser.add_argument(
       'scholarship',
       choices=['Delaney_Wings', 'Evans_Wings', 'New_Scholarship'],
       # ...
   )
   ```

4. **Create data folder**:
   ```bash
   mkdir -p data/New_Scholarship/Applications
   ```

## Requirements

- Python 3.8+
- All dependencies from `requirements.txt`
- Scholarship data in `data/<scholarship>/Applications/`
- Valid `.env` configuration

## Troubleshooting

**Error: Scholarship folder does not exist**
- Ensure the data folder exists: `ls -la data/<scholarship>/`
- Check `.env` file for correct folder paths

**Error: Unknown scholarship**
- Use one of the available scholarships: `Delaney_Wings`, `Evans_Wings`
- Check spelling and capitalization

**No applicants processed**
- Verify applications exist in `data/<scholarship>/Applications/`
- Check that application folders contain required files

**Processing fails**
- Check logs in `logs/wai_processing.log`
- Verify LLM models are available (Ollama running)
- Ensure sufficient disk space for outputs

## Related Documentation

- [Multi-Tenancy System](../docs/README_MULTI_TENANCY.md)
- [Configuration Guide](../docs/implementation_guide.md)
- [API Documentation](../docs/api_server_architecture.md)

---

**Last Updated**: 2025-12-09  
**Maintained By**: Pat G Cappelaere, IBM Federal Consulting