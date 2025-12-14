# Production Mode Design - Auto-Skip Architecture

## Overview

Transitioned the Easy Apply bot from **rule-authoring mode** (interactive, with pauses) to **production mode** (autonomous, with auto-skip).

This is a **global control-flow change**, not a field logic change. All existing field resolution rules remain unchanged.

---

## Architecture Decision: Centralized Skip Gate

### Location

The skip gate lives **within the main state machine loop** in `linkedin_easy_apply/main.py` (lines ~349-1400).

### Why Centralized?

**Problem with scattered approach:**

- 17+ `input()` pause points throughout main.py
- Each had duplicate logic: `print()` → `input()` → `log_result()` → `finalize_job()` → `return`
- Adding `--interactive` flag would require touching all 17 locations
- Violation detection was already centralized (via `needs_pause` flags)
- Action (pause vs skip) was decentralized

**Centralized solution:**

```python
def handle_violation(violation_type, violation_msg, interactive_mode, elapsed_time):
    """
    Single decision point for ALL state-machine violations.

    Production mode: Returns ('SKIP', skip_reason) immediately (no pause)
    Interactive mode: Pauses for human, then returns ('SKIP', skip_reason)
    """
```

**Benefits:**

1. ✅ Single decision point for skip vs pause behavior
2. ✅ Single place to add CSV logging
3. ✅ Easy to audit all violation types
4. ✅ Future-proof for new violation types
5. ✅ Minimal code surface area

---

## Implementation Details

### 1. Skip Reason Constants

Added structured constants at module level (lines 31-38):

```python
SKIP_UNRESOLVED_FIELD = "unresolved_field"       # No confident match for field
SKIP_LOW_CONFIDENCE = "low_confidence"           # Match below threshold
SKIP_UNEXPECTED_STATE = "unexpected_state"       # State machine error
SKIP_DISABLED_BUTTON = "disabled_button"         # Next/Submit not clickable
SKIP_VALIDATION_ERROR = "validation_error"       # LinkedIn rejected input
SKIP_NO_FORM_ELEMENTS = "no_form_elements"      # Empty modal
SKIP_MODAL_NOT_DETECTED = "modal_not_detected"  # Modal didn't open
SKIP_ALREADY_APPLIED = "already_applied"         # Pre-flight check
```

### 2. Global Violation Handler

Added centralized handler (lines 60-88):

```python
def handle_violation(violation_type, violation_msg, interactive_mode, elapsed_time):
    if interactive_mode:
        # INTERACTIVE MODE: Pause for human decision
        print(f"\n⏸️  PAUSED - {violation_msg}")
        print(f"⏱️  Time so far: {format_elapsed_time(elapsed_time)}")
        print("   Press Enter to SKIP this application")
        input()
    else:
        # PRODUCTION MODE: Auto-skip without pause
        print(f"\n⏭️  AUTO-SKIP - {violation_msg}")
        print(f"⏱️  Time so far: {format_elapsed_time(elapsed_time)}")

    return ('SKIP', violation_type)
```

**Key design:**

- Returns **same output** regardless of mode (`('SKIP', skip_reason)`)
- Interactive mode still allows manual inspection before skip
- Production mode bypasses human input completely

### 3. CLI Flag

Added `--interactive` argument (line 242):

```python
parser.add_argument(
    '--interactive',
    action='store_true',
    help='Enable interactive mode - pause on violations instead of auto-skipping (for rule authoring)'
)
```

**Usage:**

```bash
# Production mode (default) - auto-skip violations
./run.sh --links-file jobs.txt

# Interactive mode - pause for manual inspection
./run.sh --interactive "https://www.linkedin.com/jobs/view/123456789/"
```

### 4. Job-Level Tracking

Added CSV record initialization at job start (lines 280-295):

```python
job_record = {
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'job_url': job_url,
    'job_id': job_url.split('/')[-2] if '/jobs/view/' in job_url else 'unknown',
    'result': None,                    # SUCCESS | SKIPPED | FAILED | CANCELLED
    'skip_reason': '',                 # SKIP_* constant
    'state_at_exit': '',               # State machine state
    'elapsed_seconds': 0,
    'fields_resolved_count': 0,        # Auto-filled fields
    'fields_unresolved_count': 0,      # Failed fields
    'confidence_floor_hit': False      # Low-confidence flag
}
```

### 5. Replaced All Pause Points

Systematically replaced 17+ pause locations:

**Before:**

```python
if radio_needs_pause:
    elapsed = time.time() - start_time
    print("\n⏸️  PAUSED - Unresolved radio button questions")
    print(f"⏱️  Time so far: {format_elapsed_time(elapsed)}")
    print("   Press Enter to SKIP this application")
    input()

    print("\n⚠️ Skipping application")
    log_result(job_url, "SKIPPED", "Radio questions with low confidence", steps_completed)
    status = finalize_job(is_batch_mode, context, "SKIPPED")
    return
```

**After:**

```python
if radio_needs_pause:
    action, skip_reason = handle_violation(
        SKIP_UNRESOLVED_FIELD,
        "Unresolved radio button questions",
        interactive_mode,
        time.time() - start_time
    )

    print("\n⚠️ Skipping application")
    job_record['result'] = 'SKIPPED'
    job_record['skip_reason'] = skip_reason
    job_record['state_at_exit'] = 'RADIO_UNRESOLVED'
    job_record['elapsed_seconds'] = time.time() - start_time
    job_record['confidence_floor_hit'] = True
    csv_records.append(job_record)
    log_result(job_url, "SKIPPED", "Radio questions with low confidence", steps_completed)
    status = finalize_job(is_batch_mode, context, "SKIPPED")
    return
```

**Changes:**

- ✅ Centralized decision (pause vs skip)
- ✅ Added CSV tracking
- ✅ Preserved existing log.jsonl logging
- ✅ No changes to field resolution logic

### 6. CSV Summary Output

Added CSV writer at batch completion (lines 1410-1465):

```python
if csv_records:
    csv_filename = f"job_results_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    fieldnames = [
        'timestamp', 'job_url', 'job_id', 'result', 'skip_reason',
        'state_at_exit', 'elapsed_seconds', 'fields_resolved_count',
        'fields_unresolved_count', 'confidence_floor_hit'
    ]

    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_records)

    print(f"\n📊 CSV summary written to: {csv_filename}")
```

**Output format:**

```csv
timestamp,job_url,job_id,result,skip_reason,state_at_exit,elapsed_seconds,fields_resolved_count,fields_unresolved_count,confidence_floor_hit
2025-12-14T14:30:22Z,https://linkedin.com/jobs/view/123,123,SUCCESS,,SUBMITTED,45.3,3,0,False
2025-12-14T14:31:15Z,https://linkedin.com/jobs/view/456,456,SKIPPED,unresolved_field,TEXT_FIELD_UNRESOLVED,12.1,2,1,False
```

---

## Violation Types Handled

All violations route through `handle_violation()`:

| Violation Type         | Trigger Condition                           | Skip Reason Constant      |
| ---------------------- | ------------------------------------------- | ------------------------- |
| **Unresolved Fields**  | Text/radio/dropdown with no confident match | `SKIP_UNRESOLVED_FIELD`   |
| **Low Confidence**     | Match score below threshold                 | `SKIP_LOW_CONFIDENCE`     |
| **Disabled Buttons**   | Next/Review/Submit not clickable            | `SKIP_DISABLED_BUTTON`    |
| **Validation Errors**  | LinkedIn rejects input                      | `SKIP_VALIDATION_ERROR`   |
| **Unexpected State**   | State machine error                         | `SKIP_UNEXPECTED_STATE`   |
| **No Form Elements**   | Empty modal                                 | `SKIP_NO_FORM_ELEMENTS`   |
| **Modal Not Detected** | Easy Apply modal didn't open                | `SKIP_MODAL_NOT_DETECTED` |
| **Already Applied**    | Pre-flight check detects prior application  | `SKIP_ALREADY_APPLIED`    |

---

## Behavior Matrix

| Scenario                | Production Mode (Default) | Interactive Mode (--interactive)       |
| ----------------------- | ------------------------- | -------------------------------------- |
| Unresolved radio button | ⏭️ Auto-skip immediately  | ⏸️ Pause → manual inspection → skip    |
| Text field no match     | ⏭️ Auto-skip immediately  | ⏸️ Pause → manual correction → skip    |
| Disabled Submit button  | ⏭️ Auto-skip immediately  | ⏸️ Pause → manual investigation → skip |
| Already applied         | ⏭️ Auto-skip (no pause)   | ⏭️ Auto-skip (no pause)                |
| All fields resolved     | ✅ Continue normally      | ✅ Continue normally                   |
| Manual confirmation     | ⚠️ Skips this (no human)  | ✅ Prompts for YES/NO                  |

**Critical difference:**

- **Production**: Manual confirmation sections are unreachable (violations always skip first)
- **Interactive**: Manual confirmation still works for successful paths

---

## Files Modified

### Primary Changes

- `linkedin_easy_apply/main.py` (~250 lines modified)
  - Added skip constants (8 lines)
  - Added `handle_violation()` (30 lines)
  - Added `--interactive` flag (5 lines)
  - Replaced 17+ pause points with violation handler
  - Added CSV tracking to all terminal states
  - Added CSV writer at exit

### Documentation

- `README.md` (~80 lines modified)
  - Added "Operating Modes" section
  - Added CSV output format documentation
  - Updated "When It Pauses" → "When It Skips" + "When It Pauses (Interactive)"
  - Added skip reason examples

---

## Safety Guarantees

✅ **No weakened safety checks**: All existing validation logic preserved  
✅ **No field resolver changes**: Classification and resolution unchanged  
✅ **No heuristics added**: Still deterministic, rule-based  
✅ **No retries**: Fail-fast on violations  
✅ **Minimal code surface**: Centralized decision point  
✅ **Backward compatible**: Interactive mode preserves old behavior

---

## Testing Checklist

### Production Mode (Default)

- [ ] Unresolved radio button → auto-skip (no pause)
- [ ] Unresolved text field → auto-skip (no pause)
- [ ] Disabled Next button → auto-skip (no pause)
- [ ] Batch processing continues after skip
- [ ] CSV summary generated with correct columns
- [ ] Skip reasons logged correctly
- [ ] Already-applied jobs skip without entering state machine

### Interactive Mode (--interactive)

- [ ] Unresolved radio button → pause → manual inspection → skip
- [ ] Unresolved text field → pause → manual correction → skip
- [ ] Disabled Next button → pause → manual fix → skip
- [ ] Browser stays open for inspection
- [ ] Manual confirmation still works for successful paths
- [ ] CSV still generated in interactive mode

### CSV Output

- [ ] One row per job processed
- [ ] Timestamp in ISO 8601 format
- [ ] Job ID extracted correctly
- [ ] Result values: SUCCESS / SKIPPED / SKIPPED_ALREADY_APPLIED / CANCELLED / FAILED
- [ ] Skip reason empty for SUCCESS
- [ ] Skip reason populated for SKIPPED
- [ ] Elapsed seconds accurate
- [ ] Field counts tracked for text fields
- [ ] confidence_floor_hit true when low confidence triggered

---

## Example Outputs

### Production Mode Console

```
⏭️  AUTO-SKIP - Unresolved radio button questions
⏱️  Time so far: 12.3s

⚠️ Skipping application
⏱️  Total time: 12.4s

JOB 2/10
...
```

### Interactive Mode Console

```
⏸️  PAUSED - Unresolved radio button questions
⏱️  Time so far: 12.3s
   Press Enter to SKIP this application
[User presses Enter]

⚠️ Skipping application
⏱️  Total time: 12.5s

Keeping browser open for inspection...
Press Enter to close browser...
```

### CSV Summary

```csv
timestamp,job_url,job_id,result,skip_reason,state_at_exit,elapsed_seconds,fields_resolved_count,fields_unresolved_count,confidence_floor_hit
2025-12-14T14:30:22.123456Z,https://linkedin.com/jobs/view/4012345678/,4012345678,SUCCESS,,SUBMITTED,45.3,3,0,False
2025-12-14T14:31:15.789012Z,https://linkedin.com/jobs/view/4087654321/,4087654321,SKIPPED,unresolved_field,RADIO_UNRESOLVED,12.1,0,0,True
2025-12-14T14:32:05.456789Z,https://linkedin.com/jobs/view/4056789012/,4056789012,SKIPPED_ALREADY_APPLIED,already_applied,ALREADY_APPLIED,5.2,0,0,False
2025-12-14T14:32:22.901234Z,https://linkedin.com/jobs/view/4098765432/,4098765432,SKIPPED,disabled_button,NEXT_BUTTON_DISABLED,18.7,2,1,False
```

---

## Migration Path

### From Rule-Authoring to Production

1. **Development phase** (use `--interactive`):

   ```bash
   ./run.sh --interactive "https://linkedin.com/jobs/view/123/"
   ```

   - Pause on violations
   - Inspect browser state
   - Author new field resolution rules
   - Test confidence thresholds

2. **Testing phase** (production mode + small batch):

   ```bash
   # Create test_jobs.txt with 5-10 jobs
   ./run.sh --links-file test_jobs.txt
   ```

   - Verify auto-skip behavior
   - Check CSV output
   - Validate skip reasons accurate
   - Measure success rate

3. **Production deployment** (production mode + large batch):

   ```bash
   ./run.sh --links-file jobs.txt  # 100+ jobs
   ```

   - Fully autonomous
   - CSV summary for analysis
   - No human intervention required

4. **Analysis**:

   ```bash
   # Review CSV for patterns
   grep "SKIPPED" job_results_*.csv | cut -d',' -f5 | sort | uniq -c
   # Output: Most common skip reasons
   ```

5. **Iteration**:
   - Add resolution rules for common skip reasons
   - Re-run with updated rules
   - Improve success rate incrementally

---

## Future Enhancements

### Potential Additions (Not Implemented)

- [ ] Skip reason analytics dashboard
- [ ] Confidence score logging per field
- [ ] Retry logic with exponential backoff (user requested NO RETRIES)
- [ ] Machine learning field classifier (user requested NO HEURISTICS)
- [ ] Resume A/B testing framework

### Explicitly Not Wanted

- ❌ **Heuristics**: Must remain deterministic, rule-based
- ❌ **Retries**: Fail-fast on violations
- ❌ **Guessing**: No fallback "TEST" values
- ❌ **Weakened safety**: All existing checks preserved

---

## Summary

This implementation achieves the design goals:

✅ **Global auto-skip gate**: Centralized decision point  
✅ **Preserved pause behavior**: `--interactive` flag for rule authoring  
✅ **Structured skip reasons**: 8 violation type constants  
✅ **CSV logging**: Per-job metrics with skip reason tracking  
✅ **Deterministic**: Append-only, one row per job  
✅ **Minimal changes**: Single file modified (main.py + README)  
✅ **No weakened safety**: All existing checks preserved  
✅ **Backward compatible**: Interactive mode works as before

The bot now operates autonomously in production while maintaining the ability to switch to manual inspection mode for development.
