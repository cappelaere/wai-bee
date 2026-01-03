#!/usr/bin/env python3
"""
Analyze log files for errors, warnings, and failures using LLM.

This script pre-filters log content to extract important lines (errors,
warnings, failures) and uses an LLM to provide a structured analysis.

Usage:
    # Analyze a specific log file
    python examples/analyze_log.py logs/process_Delaney_Wings_20260102_120600.log
    
    # Analyze the most recent log file
    python examples/analyze_log.py --latest
    
    # Save output to a file
    python examples/analyze_log.py --latest --output analysis_report.md

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2026-01-02
Version: 1.0.0
License: MIT
"""

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from litellm import completion
from utils.llm_config import configure_litellm

# Patterns to filter for important log lines
IMPORTANT_PATTERNS = [
    r'\bERROR\b',
    r'\bCRITICAL\b',
    r'\bWARNING\b',
    r'\bfailed\b',
    r'\bFailed\b',
    r'\bFAILED\b',
    r'\bException\b',
    r'\bexception\b',
    r'\bTraceback\b',
    r'\bError:\b',
    r'\berror:\b',
    r'❌',
    r'✗',
    r'\bSuccess: False\b',
    r'\bValidation failed\b',
    r'\bretry\b',
    r'\bRetry\b',
    r'\btimeout\b',
    r'\bTimeout\b',
]

# Context patterns - lines we want to keep for context even if not errors
CONTEXT_PATTERNS = [
    r'^2\d{3}-\d{2}-\d{2}.*Processing Applicant:',  # Applicant start markers
    r'^2\d{3}-\d{2}-\d{2}.*Stage \d+:',  # Stage markers
    r'^2\d{3}-\d{2}-\d{2}.*Workflow Complete',  # Completion markers
    r'^2\d{3}-\d{2}-\d{2}.*Successful:',  # Success counts
    r'^2\d{3}-\d{2}-\d{2}.*Total time:',  # Timing info
]

ANALYSIS_PROMPT = """You are a log analysis expert. Analyze this filtered log output from a scholarship application processing workflow.

## Context

This system processes scholarship applications through these stages:
1. **Application extraction** - Parse PDF application forms
2. **Attachment processing** - Convert documents to text, remove PII
3. **Scoring agents** - Four agents score each application:
   - `application` - Eligibility and compliance
   - `resume` - Academic and experience assessment
   - `essay` - Motivation and character
   - `recommendation` - Third-party validation

Each applicant is identified by a **WAI number** (e.g., "75179", "77747").

The log has been pre-filtered to show ERROR, WARNING, failure-related messages, and context markers.

---

## Your Task

Analyze the log and produce a **structured report** with these exact sections:

### 1. Executive Summary
2-3 sentences: Was this run healthy? What's the success rate? Any critical issues?

### 2. Failed Applicants
For EACH applicant that failed (look for "Success: False" or "failed" or "stopping workflow"):

| WAI Number | Stage Failed | Error Message | Likely Cause |
|------------|--------------|---------------|--------------|
| (number)   | (stage)      | (quote error) | (explanation)|

If no failures, write "None - all applicants processed successfully."

### 3. Errors by Category
Group errors by type (e.g., validation errors, LLM errors, file errors). For each category:
- **Category name**
- Count of occurrences
- Example log line (quoted)
- Root cause and fix suggestion

### 4. Warnings Summary
List significant warnings that may indicate problems (ignore routine warnings like "File already exists, skipping").

### 5. Performance Analysis
- Total processing time
- Average time per applicant
- Any unusually slow operations (>60s for a single step)
- LLM retry attempts (look for "attempt 2/3" or "attempt 3/3")

### 6. Action Items
Prioritized list of specific actions to fix issues before the next run. Be concrete (e.g., "Pull missing attachment file for WAI 77747" not "Fix file issues").

---

## Log Content

{log_content}
"""


def find_latest_log(log_dir: Path = Path("logs")) -> Path:
    """Find the most recently modified log file in the logs directory.
    
    Args:
        log_dir: Directory to search for log files.
        
    Returns:
        Path to the most recent log file.
        
    Raises:
        FileNotFoundError: If no log files are found.
    """
    if not log_dir.exists():
        raise FileNotFoundError(f"Log directory not found: {log_dir}")
    
    log_files = list(log_dir.glob("process_*.log"))
    if not log_files:
        # Fall back to any .log file
        log_files = list(log_dir.glob("*.log"))
    
    if not log_files:
        raise FileNotFoundError(f"No log files found in {log_dir}")
    
    # Sort by modification time, most recent first
    log_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return log_files[0]


def filter_log_content(log_path: Path, context_lines: int = 2) -> tuple[str, dict]:
    """Filter log file to extract important lines with context.
    
    Args:
        log_path: Path to the log file.
        context_lines: Number of lines to include before/after important lines.
        
    Returns:
        Tuple of (filtered content string, statistics dict).
    """
    with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
        all_lines = f.readlines()
    
    total_lines = len(all_lines)
    important_pattern = re.compile('|'.join(IMPORTANT_PATTERNS), re.IGNORECASE)
    context_pattern = re.compile('|'.join(CONTEXT_PATTERNS))
    
    # Find indices of important lines
    important_indices = set()
    error_count = 0
    warning_count = 0
    
    for i, line in enumerate(all_lines):
        if important_pattern.search(line):
            # Add this line and context
            for j in range(max(0, i - context_lines), min(len(all_lines), i + context_lines + 1)):
                important_indices.add(j)
            
            # Count errors vs warnings
            if re.search(r'\bERROR\b|\bCRITICAL\b', line, re.IGNORECASE):
                error_count += 1
            elif re.search(r'\bWARNING\b', line, re.IGNORECASE):
                warning_count += 1
        
        # Always include context markers
        if context_pattern.search(line):
            important_indices.add(i)
    
    # Build filtered content
    filtered_lines = []
    last_included = -10  # Track for adding "..." separators
    
    for i in sorted(important_indices):
        if i > last_included + 1:
            filtered_lines.append("...\n")
        filtered_lines.append(all_lines[i])
        last_included = i
    
    stats = {
        'total_lines': total_lines,
        'filtered_lines': len(important_indices),
        'error_count': error_count,
        'warning_count': warning_count,
    }
    
    return ''.join(filtered_lines), stats


def analyze_log(
    log_content: str,
    #model: str = "anthropic/claude-sonnet-4-20250514",
    model: str = "anthropic/claude-haiku-4-5-20251001",
    fallback_model: str = "ollama/llama3.2:3b"
) -> str:
    """Analyze log content using LLM.
    
    Args:
        log_content: Pre-filtered log content.
        model: Primary LLM model to use.
        fallback_model: Fallback model if primary fails.
        
    Returns:
        Analysis report as markdown string.
    """
    configure_litellm()
    
    prompt = ANALYSIS_PROMPT.format(log_content=log_content)
    
    # Try primary model
    try:
        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Primary model failed ({model}): {e}", file=sys.stderr)
        
        # Try fallback
        if fallback_model and fallback_model != model:
            try:
                response = completion(
                    model=fallback_model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=4000,
                )
                return response.choices[0].message.content
            except Exception as e2:
                raise RuntimeError(f"Both models failed. Primary: {e}, Fallback: {e2}")
        else:
            raise


def main():
    parser = argparse.ArgumentParser(
        description="Analyze log files for errors and issues using LLM"
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        type=Path,
        help="Path to log file to analyze"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Analyze the most recent log file in logs/"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Save analysis to custom path (default: same as input with .md extension)"
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print to stdout instead of saving to file"
    )
    parser.add_argument(
        "--model",
        default="anthropic/claude-haiku-4-5-20251001",
        help="Primary LLM model (default: anthropic/claude-haiku-4-5-20251001)"
    )
    parser.add_argument(
        "--fallback-model",
        default="ollama/llama3.2:3b",
        help="Fallback LLM model (default: ollama/llama3.2:3b)"
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Show filtered log content without LLM analysis"
    )
    
    args = parser.parse_args()
    
    # Determine log file
    if args.latest:
        try:
            log_file = find_latest_log()
            print(f"Analyzing latest log: {log_file}", file=sys.stderr)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    elif args.log_file:
        log_file = args.log_file
        if not log_file.exists():
            print(f"Error: Log file not found: {log_file}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()
        print("\nError: Specify a log file or use --latest", file=sys.stderr)
        sys.exit(1)
    
    # Filter log content
    print(f"Filtering log file ({log_file.stat().st_size / 1024:.1f} KB)...", file=sys.stderr)
    filtered_content, stats = filter_log_content(log_file)
    
    print(f"  Total lines: {stats['total_lines']:,}", file=sys.stderr)
    print(f"  Filtered to: {stats['filtered_lines']:,} lines", file=sys.stderr)
    print(f"  Errors found: {stats['error_count']}", file=sys.stderr)
    print(f"  Warnings found: {stats['warning_count']}", file=sys.stderr)
    
    if args.raw:
        # Just show filtered content
        print("\n" + "="*60)
        print("FILTERED LOG CONTENT")
        print("="*60 + "\n")
        print(filtered_content)
        return
    
    # Analyze with LLM
    print(f"\nAnalyzing with {args.model}...", file=sys.stderr)
    
    try:
        analysis = analyze_log(
            filtered_content,
            model=args.model,
            fallback_model=args.fallback_model
        )
    except Exception as e:
        print(f"Error during analysis: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Build report
    report = f"""# Log Analysis Report

**Log File:** `{log_file}`  
**Analyzed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Model:** {args.model}

---

## Pre-Analysis Statistics

| Metric | Value |
|--------|-------|
| Total log lines | {stats['total_lines']:,} |
| Filtered lines | {stats['filtered_lines']:,} |
| Error messages | {stats['error_count']} |
| Warning messages | {stats['warning_count']} |

---

{analysis}
"""
    
    # Determine output path
    if args.stdout:
        # Print to console
        print(report)
    else:
        # Save to file (default: same name as input with .md extension)
        if args.output:
            output_path = args.output
        else:
            output_path = log_file.with_suffix('.md')
        
        output_path.write_text(report, encoding='utf-8')
        print(f"\nAnalysis saved to: {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()

