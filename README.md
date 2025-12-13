# LinkedIn Easy Apply Bot

Keyboard-driven automation for LinkedIn Easy Apply submissions using state machine architecture and semantic text field resolution.

## Features

✅ **Keyboard Navigation** - Tab + Enter (more human-like, avoids detection)
✅ **AUTO Mode** - Automatically finds and clicks Easy Apply button
✅ **Multi-Step Forms** - Handles Next/Review/Submit progression
✅ **Smart Text Fields** - Classifies fields and auto-fills from answer bank
✅ **Manual Confirmation** - Requires YES/NO before submission
✅ **Resume Upload** - Automatic PDF upload
✅ **Auto-Skip** - Filters phone, email, address, web link fields

## Setup

1. **Create virtual environment and install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Log into LinkedIn (one-time setup):**

   ```bash
   ./setup_login.sh
   ```

   - A browser will open showing LinkedIn login
   - Log in with your credentials
   - **Press Ctrl+C in the terminal when done** to save the session
   - Your login will be saved for all future bot runs

3. **Configure settings in `bot_manual.py`:**
   - **Resume path** (line 558): `/Users/sawyersmith/Documents/resume2025.pdf`
   - **Answer bank** (lines 17-36): Edit ANSWER_BANK dictionary to customize responses

## Usage

### Run the bot (AUTO mode enabled by default):

```bash
python3 bot_manual.py "https://www.linkedin.com/jobs/view/123456789/"
```

**What happens:**

1. **Browser opens** to the job page
2. **AUTO mode**: Bot uses Tab navigation to find Easy Apply button
   - Tabs through page elements checking text and aria-labels
   - Presses Enter when found (typically around tab 19)
   - Falls back to manual if not found after 30 tabs
3. **State machine loop** analyzes form and takes actions:
   - **Text fields detected**: Classifies each field (numeric vs text)
     - Matches to answer bank using keyword mappings
     - Types resolved value or "TEST" for unknowns
     - Pauses if numeric field has no answer
   - **Radio buttons**: Selects first option in each group (blind)
   - **Checkboxes**: Auto-checks consent/agreement boxes
   - **Resume upload**: Uploads PDF if file input detected
   - **Multi-step**: Presses Next/Review buttons automatically
4. **Manual confirmation**: You must type YES to submit
5. **Success verification**: Checks for "Application sent" message
6. **Logging**: Appends result to `log.jsonl` with field metadata

### Customizing Answers

Edit the `ANSWER_BANK` dictionary in `bot_manual.py` (lines 17-36):

```python
ANSWER_BANK = {
    # Numeric answers
    'years_experience': '1',  # Change to your actual years
    'gpa': '3.5',
    'notice_period': '2',

    # Text answers
    'linkedin_url': 'https://linkedin.com/in/yourprofile',
    'skills_summary': 'Your skills here...',
    'why_interested': 'Your reason here...',
}
```

The bot matches field labels to these keys using keyword patterns defined in `resolve_field_answer()`.

## Auto-Skipped Fields

Bot automatically skips auto-fillable fields:

- **Phone/mobile/telephone** - LinkedIn auto-fills from profile
- **Email** - LinkedIn auto-fills from profile
- **Address fields** - Street, city, zip, postal
- **Web links** - LinkedIn URL, portfolio, website

## Pause Conditions

Bot pauses for manual input when:

- **Unresolved text fields** - Field detected but no match in answer bank
  - Types "TEST" as placeholder
  - Pauses to let you review/correct
- **Unresolved numeric fields** - Cannot type "TEST" into number fields
  - Pauses immediately without filling

**Manual confirmation required before ALL submissions** - prevents accidental applications.

## Logs

All runs are logged to `log.jsonl` with enhanced metadata:

```json
{"timestamp": "2025-12-12T15:30:00Z", "job_url": "...", "status": "SUCCESS", "steps_completed": 8}
{"timestamp": "2025-12-12T15:31:00Z", "job_url": "...", "status": "SKIPPED", "failure_reason": "Text fields with unresolved answers", "steps_completed": 4}
{"timestamp": "2025-12-12T15:32:00Z", "job_url": "...", "state": "MODAL_TEXT_FIELD_DETECTED", "action": "FIELD_RESOLUTION_ATTEMPTED", "field_count": 3, "fields": [{"label": "Years of experience", "classification": "NUMERIC_FIELD", "resolved_answer": "1", "typed_value": "1", "needs_pause": false}]}
```

Status values: `SUCCESS`, `SKIPPED`, `FAILED`, `CANCELLED`

## Current Limitations

⚠️ **Radio buttons**: Bot selects first option without understanding the question

- Works for many questions but may answer incorrectly
- Example: "Do you need sponsorship?" → Always selects first option

⚠️ **Dropdowns/Selects**: Not yet implemented

- Bot skips applications with dropdown fields

⚠️ **Question semantic understanding**: No logic for:

- Work authorization questions
- Sponsorship questions
- Salary expectations
- Start date preferences

## Technical Details

**State Machine:**

- `JOB_PAGE` → `MODAL_OPEN` → `TEXT_FIELD_DETECTED` → `FORM_STEP` → `REVIEW_STEP` → `SUBMITTED`
- Each state has specific actions
- State detection happens BEFORE actions (read → decide → act)

**Text Field Resolution:**

1. `classify_field_type()` - Returns NUMERIC_FIELD, TEXT_FIELD, or UNKNOWN
2. `resolve_field_answer()` - Matches label keywords to answer bank
3. Type safety check - Prevents "TEST" in numeric fields

**Keyboard Controls:**

- Tab: Navigate through elements
- Enter: Activate buttons/links
- Space: Select radio buttons and checkboxes
- Control+A: Select all text in field

**Modal Scoping:**

- All selectors prefixed with `[role="dialog"]`
- Prevents tabbing outside modal context
- Actions never escape to job page

## Notes

- The script runs once per invocation (no loops)
- Browser runs in non-headless mode by default (set `headless=True` for background use)
- Browser session saved in `browser_data/` directory
- No retries - exits immediately on skip/fail

## Project Structure

See [STRUCTURE.md](STRUCTURE.md) for complete file organization.

**Key files:**

- `bot_manual.py` - Main bot (recommended)
- `bot.py` - Experimental automation
- `run_manual.sh` - Quick run script
- `archive/` - Debug scripts and screenshots
