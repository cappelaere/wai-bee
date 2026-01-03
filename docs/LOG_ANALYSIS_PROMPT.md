# Log Analysis Prompt Template

Use this prompt to analyze log files manually in Claude, ChatGPT, or other LLM interfaces.

## Quick Start

1. Open your log file (e.g., `logs/process_Delaney_Wings_20260102_120600.log`)
2. Copy the relevant portion (or use `grep -E "ERROR|WARNING|failed|Failed" logfile.log` to pre-filter)
3. Paste the prompt below into your LLM, followed by the log content

---

## The Prompt

```
Analyze this log file from a scholarship application processing workflow.

**Context:**
- This system processes scholarship applications through multiple stages:
  1. Application extraction (parsing PDF forms)
  2. Attachment processing (converting documents, removing PII)
  3. Scoring agents (application, resume, essay, recommendation)
  4. Summary generation
- Each applicant is identified by a WAI number (e.g., "75179")
- Log levels: INFO (normal), WARNING (potential issues), ERROR (failures)

**Identify and summarize:**
1. **Errors**: Any ERROR or CRITICAL level messages, with context
2. **Warnings**: WARNING messages that may indicate problems
3. **Failures**: Any applicants that failed processing and why
4. **Anomalies**: Unusual patterns (e.g., very slow operations, repeated retries)
5. **Success Rate**: How many applicants succeeded vs failed

**For each issue found:**
- Quote the relevant log lines
- Explain the likely cause
- Suggest a fix if applicable

**Output format:**
- Executive Summary (2-3 sentences)
- Errors (grouped by type)
- Warnings (grouped by type)
- Failed Applicants (with reasons)
- Processing Statistics
- Recommendations (prioritized actions)

---
LOG FILE:
[paste log content here]
```

---

## Pre-Filtering Tips

For large log files (10K+ lines), pre-filter before pasting:

### Extract Only Errors and Warnings

```bash
grep -E "ERROR|WARNING|CRITICAL|failed|Failed|Exception" logs/your_log.log
```

### Extract Errors with Context (5 lines before/after)

```bash
grep -B5 -A5 -E "ERROR|CRITICAL|Exception" logs/your_log.log
```

### Extract Processing Summary Lines

```bash
grep -E "Processing Applicant|Success:|Failed:|Workflow Complete|Total time" logs/your_log.log
```

### Combined Filter for Analysis

```bash
grep -E "ERROR|WARNING|CRITICAL|failed|Failed|Exception|Processing Applicant|Success:|Workflow Complete" logs/your_log.log
```

---

## Automated Alternative

For automated analysis, use the script:

```bash
# Analyze most recent log
python examples/analyze_log.py --latest

# Analyze specific log
python examples/analyze_log.py logs/process_Delaney_Wings_20260102_120600.log

# Save to file
python examples/analyze_log.py --latest --output analysis.md

# Just see filtered content without LLM analysis
python examples/analyze_log.py --latest --raw
```

---

## Example Issues to Look For

### Common Error Patterns

| Pattern | Meaning |
|---------|---------|
| `APIConnectionError` | Ollama not running or model not available |
| `Validation failed` | Application missing required fields or attachments |
| `File is empty (0 bytes)` | Corrupt or empty attachment file |
| `model 'X' not found` | LLM model needs to be pulled |
| `JSON validation` errors | LLM output didn't match expected schema |

### Warning Patterns

| Pattern | Meaning |
|---------|---------|
| `Missing scores for:` | Some agents didn't produce scores |
| `retry` / `attempt 2/3` | LLM needed multiple attempts |
| `File already exists, skipping` | Previous run data reused (normal) |

### Success Indicators

| Pattern | Meaning |
|---------|---------|
| `JSON validation successful after 0 fix attempts` | Clean LLM output |
| `Success: True` | Applicant fully processed |
| `Successful: N/N` | All applicants completed |

