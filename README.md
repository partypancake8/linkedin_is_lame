# LinkedIn Easy Apply Bot

Modular LinkedIn Easy Apply automation using keyboard-only navigation, semantic field resolution, and state machine architecture. Submits applications while mimicking human interaction patterns to avoid detection.

## What This Bot Does

- **Finds Easy Apply button** using keyboard Tab navigation (no mouse clicks)
- **Fills out forms** automatically by matching field labels to your answer bank
- **Handles multi-step applications** (Next/Review/Submit progression)
- **Answers yes/no questions** using keyword matching (work authorization, sponsorship, etc.)
- **Uploads resume** when file input detected
- **Requires manual confirmation** before final submission (prevents accidental applications)

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

Run the bot with a job URL:

```bash
./run.sh "https://www.linkedin.com/jobs/view/123456789/"
```

Or using Python directly:

```bash
source venv/bin/activate
python -m linkedin_easy_apply.main "https://www.linkedin.com/jobs/view/123456789/"
```

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
5. **Manual confirmation:** You must type `YES` to submit
6. **Logs result** to `log.jsonl`

### When It Pauses

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
