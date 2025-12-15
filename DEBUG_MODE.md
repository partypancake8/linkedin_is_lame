# Debug Unresolved Fields Mode

## Overview

The `--debug-unresolved` flag provides read-only observability into unresolved fields that cause application skips. This mode does NOT change behavior, does NOT relax safety gates, and does NOT submit applications.

## Purpose

This debug mode exists to identify coverage gaps in the automation system - specifically, to understand which fields the system cannot confidently resolve, helping prioritize future automation improvements.

## Usage

```bash
./run.sh --debug-unresolved --links-file jobs.txt
```

Or combine with other flags:

```bash
./run.sh --debug-unresolved --test-mode --speed super --links-file jobs.txt
```

## Behavior

### With `--debug-unresolved` enabled:

1. **Same automation behavior** - All skips still occur at the same points
2. **Same safety gates** - No confidence thresholds are relaxed
3. **Additional logging** - Unresolved fields are recorded to `debug_unresolved.jsonl`

### Without `--debug-unresolved` (default):

- No debug logging
- Identical behavior to previous versions

## Output Format

### File: `debug_unresolved.jsonl`

One JSON object per unresolved field, written on terminal states only (SKIP/TEST_SUCCESS/FAILED/CANCELLED).

**Example entry:**

```json
{
  "timestamp": "2025-12-14T20:45:30.123456-05:00",
  "job_id": "1234567890",
  "job_url": "https://www.linkedin.com/jobs/view/1234567890/",
  "state_at_exit": "RADIO_UNRESOLVED",
  "skip_reason": "unresolved_field",
  "field_type": "radio",
  "question_text": "Are you comfortable working with ambiguity?",
  "options": ["Yes", "No", "Somewhat"],
  "classification": "unmatched",
  "tier": "unknown",
  "eligible": true,
  "confidence": "low",
  "matched_key": "unmatched"
}
```

### Field Descriptions:

- **timestamp**: Eastern Time (America/Detroit) timestamp
- **job_id**: LinkedIn job ID extracted from URL
- **job_url**: Full job URL
- **state_at_exit**: State when field resolution failed (RADIO_UNRESOLVED, SELECT_UNRESOLVED, TEXT_UNRESOLVED)
- **skip_reason**: Skip reason constant (typically "unresolved_field")
- **field_type**: Field type (radio, select, text)
- **question_text**: Question/label text from UI
- **options**: List of available options (for radio/select) or null (for text)
- **classification**: Classification result (e.g., TIER1_WORK_AUTHORIZATION, unmatched)
- **tier**: Tier level (tier-1, tier-2, skip, unknown)
- **eligible**: Whether field was deemed eligible for automation
- **confidence**: Confidence level (high, medium, low, none)
- **matched_key**: Matched answer bank key or null

## Implementation Details

### Recording Points:

1. **Radio questions** - `resolve_radio_question()` returns `(None, "low", ...)`
2. **Select dropdowns** - `resolve_select_answer()` returns `(None, "low", ...)`
3. **Text fields** - `resolve_field_answer()` returns `None`

### Flush Points:

Debug buffer is flushed to file ONLY on terminal states:
- SKIPPED
- TEST_SUCCESS
- FAILED
- CANCELLED

Never flushed mid-run. This ensures complete job context.

## Important Warnings

### What This Mode Does NOT Do:

- ❌ Does NOT add retry logic
- ❌ Does NOT add fallback values
- ❌ Does NOT infer eligibility
- ❌ Does NOT aggregate records
- ❌ Does NOT suppress skip behavior
- ❌ Does NOT submit applications
- ❌ Does NOT change confidence thresholds

### What This Mode DOES Do:

- ✅ Records unresolved fields to debug log
- ✅ Maintains identical automation behavior
- ✅ Preserves all safety gates
- ✅ Provides observability for coverage gap analysis

## Testing

### Test 1: Known failing case

```bash
# Run a job that has unresolved radio question
./run.sh --debug-unresolved --test-mode "https://linkedin.com/jobs/view/12345/"
```

**Expected:**
- result = SKIPPED (same as without flag)
- `debug_unresolved.jsonl` has ≥1 entry
- entry.question_text matches UI

### Test 2: Known TEST_SUCCESS case

```bash
# Run a job that reaches SUBMIT_READY
./run.sh --debug-unresolved --test-mode "https://linkedin.com/jobs/view/67890/"
```

**Expected:**
- result = TEST_SUCCESS (same as without flag)
- `debug_unresolved.jsonl` unchanged (no new lines)

### Test 3: Regression guard

```bash
# Run same batch without --debug-unresolved
./run.sh --test-mode --links-file jobs.txt
```

**Expected:**
- Identical CSV results
- Identical log.jsonl
- No `debug_unresolved.jsonl` created

## Analysis Workflow

1. **Collect data**: Run with `--debug-unresolved` on representative job set
2. **Analyze patterns**: Group by classification, tier, matched_key
3. **Identify gaps**: Find most common unresolved field types
4. **Prioritize**: Focus on Tier-1/Tier-2 eligible fields with low coverage
5. **Extend**: Add new patterns to answer_bank or classification rules

## File Location

`debug_unresolved.jsonl` is created in the project root and is gitignored.
