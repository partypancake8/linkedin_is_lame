# LinkedIn Easy Apply Bot

Modular LinkedIn Easy Apply automation using keyboard-only navigation, semantic field resolution, and state machine architecture. Submits applications while mimicking human interaction patterns to avoid detection.

## What This Bot Does

- **Finds Easy Apply button** using keyboard Tab navigation (no mouse clicks)
- **Fills out forms** automatically by matching field labels to your answer bank
- **Handles multi-step applications** (Next/Review/Submit progression)
- **Answers yes/no questions** using keyword matching (work authorization, sponsorship, etc.)
- **Uploads resume** when file input detected
- **Requires manual confirmation** before final submission (prevents accidental applications)
- **Production mode**: Auto-skips jobs with unresolved fields (no pausing)
- **Interactive mode**: Pauses for manual inspection when issues arise (for rule authoring)

## Operating Modes

### Production Mode (Default)

Autonomous operation for batch processing:

- **Auto-skips** jobs with unresolved fields, low confidence, or validation errors
- **No pausing** for human intervention
- **CSV summary** output with skip reasons and performance metrics
- Ideal for high-volume application processing

```bash
./run.sh --links-file jobs.txt
```

### Test Mode (--test-mode)

Validation mode for testing automation completeness without submitting:

- **Runs non-interactively** through entire application flow
- **Auto-skips** jobs with violations (same as production mode)
- **Stops before submission** - validates form completion without applying
- **Marks as TEST_SUCCESS** if application reaches submit-ready state
- Use for testing new field rules or validating automation coverage

```bash
./run.sh --test-mode --links-file jobs.txt
```

**Output:**

- Jobs that complete all fields: `TEST_SUCCESS`
- Jobs with unresolved fields: `SKIPPED` (with skip reason)
- CSV includes both TEST_SUCCESS and SKIPPED results

### Interactive Mode (--interactive)

Manual inspection mode for rule authoring and debugging:

- **Pauses** when encountering unresolved fields or issues
- Allows manual correction before continuing
- Keeps browser open for inspection
- Use when developing new field resolution rules

```bash
./run.sh --interactive "https://www.linkedin.com/jobs/view/123456789/"
```

**Note:** Cannot use `--interactive` and `--test-mode` together.

## Dev Test Speed Mode

For faster local testing, use command-line flags to enable speed modes:

```bash
# Standard speed mode (40-50% faster, 1.5x-2x speed)
./run.sh --speed dev "https://www.linkedin.com/jobs/view/123456789/"

# Super speed mode (70-80% faster, 3x-5x speed)
./run.sh --speed super "https://www.linkedin.com/jobs/view/123456789/"

# Production mode (default, no flag needed)
./run.sh "https://www.linkedin.com/jobs/view/123456789/"
```

⚠️ **Production use**: Run without `--speed` flag (default, safest)

- **--speed dev**: Balanced speed increase, good for general testing
- **--speed super**: Maximum safe speed without appearing bot-like, best for rapid iteration

Both modes maintain human-like randomization patterns to avoid detection.

Alternatively, you can still set speed modes in `linkedin_easy_apply/config.py`:

```python
DEV_TEST_SPEED = True   # 40-50% faster
SUPER_DEV_SPEED = True  # 70-80% faster (overrides DEV_TEST_SPEED)
```

Command-line flags override config file settings.

## Setup

1. **Install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 -m playwright install chromium
   ```

2. **Configure your answers in `linkedin_easy_apply/data/answer_bank.py`:**

   ```python
   ANSWER_BANK = {
       # Numeric fields
       'years_experience': '1',
       'gpa': '3.5',
       'notice_period_weeks': '2',

       # Text fields
       'linkedin_url': 'https://linkedin.com/in/yourprofile',
       'github_url': 'https://github.com/yourusername',

       # Boolean questions (yes/no radio buttons)
       'authorized_to_work': True,
       'requires_sponsorship': False,
       'willing_to_relocate': False,
   }
   ```

3. **Set resume path in `linkedin_easy_apply/browser/session.py` (line ~40):**

   ```python
   RESUME_PATH = "/Users/yourusername/Documents/resume.pdf"
   ```

## Usage

### Single Job Mode

Run the bot with a single job URL:

```bash
# Production speed (default, safest)
./run.sh "https://www.linkedin.com/jobs/view/123456789/"

# Dev test speed (1.5x-2x faster)
./run.sh --speed dev "https://www.linkedin.com/jobs/view/123456789/"

# Super dev speed (3x-5x faster)
./run.sh --speed super "https://www.linkedin.com/jobs/view/123456789/"
```

Or using Python directly:

```bash
source venv/bin/activate
python -m linkedin_easy_apply.main "https://www.linkedin.com/jobs/view/123456789/"
python -m linkedin_easy_apply.main --speed dev "https://www.linkedin.com/jobs/view/123456789/"
python -m linkedin_easy_apply.main --speed super "https://www.linkedin.com/jobs/view/123456789/"
```

### Batch Mode (Multiple Jobs)

Process multiple job applications in one session using a links file:

1. **Create a text file** (e.g., `jobs.txt`) with one job URL per line:

   ```
   # My job applications - lines starting with # are comments
   https://www.linkedin.com/jobs/view/4012345678/
   https://www.linkedin.com/jobs/view/4087654321/
   https://www.linkedin.com/jobs/view/4056789012/

   # Duplicate URLs are automatically removed
   ```

2. **Run in batch mode:**

   ```bash
   # Production speed
   ./run.sh --links-file jobs.txt

   # With speed modes
   ./run.sh --speed dev --links-file jobs.txt
   ./run.sh --speed super --links-file jobs.txt
   ```

   Or using Python:

   ```bash
   python -m linkedin_easy_apply.main --links-file jobs.txt
   python -m linkedin_easy_apply.main --speed dev --links-file jobs.txt
   ```

3. **Batch mode features:**
   - Browser stays open across all jobs
   - Automatically continues to next job after completion
   - Skips jobs already applied to
   - Shows progress: "JOB 2/10"
   - Summary report at the end:
     ```
     BATCH COMPLETE
     Processed 10 jobs:
       SUCCESS: 6
       SKIPPED: 2
       SKIPPED_ALREADY_APPLIED: 1
       FAILED: 1
     ```
   - **CSV summary output** with detailed metrics per job:
     ```
     📊 CSV summary written to: job_results_20251214_143022.csv
     ```

**Sample jobs.txt file** is included in the repository (`test_jobs.txt`).

### CSV Output Format

Each job processed generates one row with the following columns:

| Column                    | Description                                                                            |
| ------------------------- | -------------------------------------------------------------------------------------- |
| `timestamp`               | ISO 8601 timestamp of job processing                                                   |
| `job_url`                 | Full LinkedIn job URL                                                                  |
| `job_id`                  | Extracted job ID from URL                                                              |
| `result`                  | SUCCESS / SKIPPED / SKIPPED_ALREADY_APPLIED / CANCELLED / FAILED                       |
| `skip_reason`             | Structured reason code (e.g., `unresolved_field`, `low_confidence`, `disabled_button`) |
| `state_at_exit`           | State machine state when job ended                                                     |
| `elapsed_seconds`         | Total processing time for this job                                                     |
| `fields_resolved_count`   | Number of text fields successfully auto-filled                                         |
| `fields_unresolved_count` | Number of text fields that could not be resolved                                       |
| `confidence_floor_hit`    | Boolean indicating if any field fell below confidence threshold                        |

Example CSV output:

```csv
timestamp,job_url,job_id,result,skip_reason,state_at_exit,elapsed_seconds,fields_resolved_count,fields_unresolved_count,confidence_floor_hit
2025-12-14T14:30:22Z,https://linkedin.com/jobs/view/123,123,SUCCESS,,SUBMITTED,45.3,3,0,False
2025-12-14T14:31:15Z,https://linkedin.com/jobs/view/456,456,TEST_SUCCESS,,SUBMIT_READY,38.1,4,0,False
2025-12-14T14:32:05Z,https://linkedin.com/jobs/view/789,789,SKIPPED,unresolved_field,TEXT_FIELD_UNRESOLVED,12.1,2,1,False
2025-12-14T14:32:30Z,https://linkedin.com/jobs/view/321,321,SKIPPED_ALREADY_APPLIED,already_applied,ALREADY_APPLIED,5.2,0,0,False
```

**Result Types:**

- `SUCCESS` - Application submitted successfully (production mode)
- `TEST_SUCCESS` - Application ready but not submitted (test mode)
- `SKIPPED` - Unresolved fields or violations
- `SKIPPED_ALREADY_APPLIED` - Job already applied to
- `CANCELLED` - User declined submission (interactive mode)
- `FAILED` - Technical error or unexpected state

### What Happens

1. **Browser launches** with persistent LinkedIn session (stay logged in)
2. **Navigates to job page**
3. **Auto-finds Easy Apply** by tabbing through page elements (typically Tab #19)
4. **Form filling loop:**
   - Detects current state (text fields / radio buttons / dropdowns)
   - Uploads resume if file input found
   - Fills text fields using answer bank matches
   - Answers yes/no questions using keyword matching
   - Selects dropdown options when confident
   - Navigates multi-step forms automatically
5. **Manual confirmation:** You must type `YES` to submit (in interactive mode)
6. **Logs result** to `log.jsonl` and CSV summary

### When It Skips (Production Mode)

The bot will **auto-skip** jobs when encountering:

- **Unresolved fields**: Text fields, radio buttons, or dropdowns without confident matches
- **Low confidence**: Field resolution below safety threshold
- **Validation errors**: LinkedIn rejects input (invalid format, missing required fields)
- **Disabled buttons**: Next/Review/Submit buttons not clickable
- **Already applied**: Job shows "Applied" status or confirmation

Skip reasons are logged to CSV with structured codes for analysis.

### When It Pauses (Interactive Mode Only)

With `--interactive` flag, the bot pauses instead of skipping:

The bot pauses and requires manual intervention when:

- **Unresolved text field** - No match found in answer bank (types "TEST" as placeholder)
- **Unresolved yes/no question** - Question not recognized by keyword patterns
- **Multi-option radio buttons** - More than 2 options (bot only handles binary yes/no)
- **Large dropdowns** - More than 5 options (too risky to guess)
- **Validation errors** - Typed value rejected by LinkedIn's inline validation

You can skip (press Enter) or manually fix and continue.

## How It Works

See [STRUCTURE.md](STRUCTURE.md) for complete architecture documentation.

**High-level flow:**

```
Job Page → Find Easy Apply (Tab navigation)
         → Wait for Modal
         → State Detection Loop:
            ├─ Upload resume
            ├─ Answer yes/no questions (radios)
            ├─ Fill dropdowns (selects)
            ├─ Fill text fields (inputs)
            ├─ Navigate multi-step (Next/Review buttons)
            └─ Manual confirmation → Submit
```

**Key behaviors:**

- **Keyboard-only** - No mouse clicks, uses Tab/Enter/Space like a human
- **Conservative** - Pauses on uncertainty rather than guessing incorrectly
- **Logged** - All decisions written to `log.jsonl` for debugging
- **Auto-skip** - Ignores pre-filled fields (email, phone, address)

## Logs

Application results are logged to `log.jsonl`:

```json
{"timestamp": "2025-12-13T10:30:00Z", "job_url": "...", "status": "SUCCESS", "steps_completed": 8}
{"timestamp": "2025-12-13T10:31:00Z", "job_url": "...", "status": "SKIPPED", "reason": "Unresolved radio question"}
```

Status values: `SUCCESS`, `SKIPPED`, `FAILED`, `CANCELLED`

## Architecture

This project uses a modular structure. See [STRUCTURE.md](STRUCTURE.md) for detailed documentation.

**Package layout:**

```
linkedin_easy_apply/
├── main.py              # CLI entry point, orchestration loop
├── browser/             # Browser session management
├── state/               # State detection (modal vs form vs review)
├── perception/          # DOM detection (text fields, radios, selects)
├── reasoning/           # Field classification and answer resolution
├── interaction/         # Keyboard automation (typing, tabbing, clicking)
├── data/                # Answer bank configuration
└── utils/               # Logging and timing utilities
```

## Notes

- Browser runs in non-headless mode (you can watch it work)
- Session persists in `browser_data/` directory (stay logged into LinkedIn)
- No retries - exits immediately on pause/failure
- One application per invocation
