# Quick Reference: Command-Line Flags

## Mode Selection

### Production Mode (Default) - Autonomous Processing

```bash
# Single job
./run.sh "https://www.linkedin.com/jobs/view/123456789/"

# Batch mode
./run.sh --links-file jobs.txt
```

- ⏭️ **Auto-skips** violations (no human intervention)
- 📊 **CSV summary** output with metrics
- ✅ Ideal for high-volume processing

### Interactive Mode - Rule Authoring

```bash
# Single job with pauses
./run.sh --interactive "https://www.linkedin.com/jobs/view/123456789/"

# Batch mode with pauses (not recommended)
./run.sh --interactive --links-file jobs.txt
```

- ⏸️ **Pauses** on violations for manual inspection
- 🔍 Browser stays open for debugging
- ✅ Use when developing new field rules

## Speed Modes

### Production Speed (Default)

```bash
./run.sh --links-file jobs.txt
```

- Safest, most human-like timing
- Recommended for large-scale runs

### Dev Speed (1.5x-2x faster)

```bash
./run.sh --speed dev --links-file jobs.txt
```

- 40-50% faster
- Good for testing

### Super Speed (3x-5x faster)

```bash
./run.sh --speed super --links-file jobs.txt
```

- 70-80% faster
- Maximum safe speed for rapid iteration

## Common Combinations

### Production Run (High Volume)

```bash
./run.sh --links-file jobs.txt
# Auto-skip violations, production timing, CSV output
```

### Development Testing (Fast Iteration)

```bash
./run.sh --interactive --speed super "https://linkedin.com/jobs/view/123/"
# Pause on issues, maximum speed, browser inspection
```

### Batch Testing (Medium Volume)

```bash
./run.sh --speed dev --links-file test_jobs.txt
# Auto-skip, faster timing, test batch
```

### Rule Authoring (Single Job)

```bash
./run.sh --interactive "https://linkedin.com/jobs/view/123/"
# Pause on violations, production speed, manual inspection
```

## Flag Reference Table

| Flag            | Values         | Default | Purpose                                  |
| --------------- | -------------- | ------- | ---------------------------------------- |
| `--interactive` | (boolean)      | False   | Pause on violations instead of auto-skip |
| `--speed`       | `dev`, `super` | (none)  | Speed up timing (1.5x or 3x)             |
| `--links-file`  | FILE           | (none)  | Batch mode: process multiple job URLs    |

## Output Files

### log.jsonl

- Detailed event log
- One JSON object per line
- Includes field-level resolution details
- Written for all modes

### job_results_YYYYMMDD_HHMMSS.csv

- One row per job processed
- Columns: timestamp, job_url, job_id, result, skip_reason, state_at_exit, elapsed_seconds, fields_resolved_count, fields_unresolved_count, confidence_floor_hit
- Written at process exit (batch or single)
- Production mode only (not interactive)

## Examples

### Process 100 jobs autonomously

```bash
./run.sh --links-file jobs.txt
# Expected: ~60% success, 30% skipped, 10% already applied
# Output: job_results_20251214_143022.csv
```

### Debug a specific job

```bash
./run.sh --interactive --speed super "https://linkedin.com/jobs/view/123456789/"
# Expected: Pause at first violation, browser stays open
# Output: log.jsonl (no CSV in interactive mode)
```

### Test new field rules

```bash
# 1. Run in interactive mode to identify missing rules
./run.sh --interactive "https://linkedin.com/jobs/view/123/"

# 2. Add rules to resolve_text.py / resolve_radio.py / resolve_select.py

# 3. Test in production mode with small batch
./run.sh --speed dev --links-file test_jobs.txt

# 4. Verify CSV shows improved success rate
```

## Troubleshooting

### "No module named 'linkedin_easy_apply'"

```bash
# Make sure you're running from repo root
cd /path/to/linkedin_is_lame
./run.sh --links-file jobs.txt
```

### "Either job_url or --links-file must be provided"

```bash
# Need to provide at least one input
./run.sh "https://linkedin.com/jobs/view/123/"  # Single job
./run.sh --links-file jobs.txt                  # Batch mode
```

### "Cannot use both job_url and --links-file"

```bash
# Pick one mode:
./run.sh "https://linkedin.com/jobs/view/123/"  # Single job
./run.sh --links-file jobs.txt                  # Batch mode

# Not both:
# ❌ ./run.sh "URL" --links-file jobs.txt
```

### CSV not generated

- Check that at least one job completed
- CSV written at process exit (Ctrl+C won't save)
- Interactive mode doesn't write CSV (design choice)

### All jobs skipped

- Check answer_bank.py has required fields
- Review skip_reason column in CSV
- Run one job in `--interactive` mode to see which fields fail
- Add resolution rules for common skip reasons
