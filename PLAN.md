# LinkedIn Easy Apply Bot - Implementation Status

## Goal

Keyboard-driven Python automation that submits LinkedIn Easy Apply applications using human-like Tab navigation. Uses state machine architecture to handle multi-step forms, automatically fills text fields using semantic resolution, and requires manual confirmation before final submission.

## Current Implementation

### Core Features

1. **Keyboard Navigation** - Uses Tab + Enter instead of mouse clicks to avoid detection
2. **State Machine** - Detects current UI state and takes appropriate actions
3. **Semantic Text Field Resolution** - Classifies fields (numeric vs text) and matches to answer bank
4. **Multi-Step Form Support** - Handles Next/Review/Submit button progression
5. **AUTO Mode** - Automatically finds and activates Easy Apply button via keyboard
6. **Resume Upload** - Automatically uploads PDF resume from configured path
7. **Manual Confirmation** - Requires YES/NO input before any submission

### Application Flow

1. Launch browser with persistent Chrome profile (LinkedIn session assumed active)
2. Navigate to job URL (provided via CLI argument)
3. **AUTO MODE**: Bot uses Tab navigation to find and activate Easy Apply button
   - Falls back to manual activation if not found after 30 tabs
4. Wait for modal to appear
5. **State Detection Loop** (max 10 steps):
   - Detect current state: TEXT_FIELDS / SINGLE_STEP / FORM_STEP / REVIEW_STEP
   - Upload resume if file input detected
   - Select first radio button in each group (blind selection)
   - Check consent/agreement checkboxes
   - **Text Field Handler**: Classify → Resolve → Fill all fields
   - Navigate with Next/Review buttons if multi-step
   - **Manual Confirmation** before Submit
6. Log result to `log.jsonl` with enhanced metadata
7. Exit

**State-driven architecture prevents rogue tabbing and ensures actions are scoped to modal context.**

## Skip/Pause Rules

Script pauses for manual intervention if:

1. **Text fields with unresolved answers** - Field detected but no match in answer bank
2. **Numeric fields requiring specific values** - Cannot auto-fill without semantic match

Script auto-skips auto-fillable fields:

1. Phone/mobile/telephone fields
2. Email fields
3. Address fields (street, city, zip, postal)
4. Social/web links (LinkedIn, portfolio, website)

**User must confirm (YES/NO) before any submission** - prevents accidental applications.

## Failure Policy

- Log `FAILED` status with exception message for unexpected errors
- Include `steps_completed` counter in log to identify where failure occurred
- No retries - script exits immediately on failure
- Failures should be rare if skip rules are comprehensive

## Current Capabilities

✅ **Working:**

- Keyboard-only navigation (Tab + Enter + Space)
- AUTO mode Easy Apply activation
- Multi-step form progression (Next/Review/Submit)
- Text field semantic resolution (years_experience, GPA, skills, etc.)
- Resume upload automation
- Consent checkbox handling
- Manual submission confirmation
- Re-fill prevention (tracks processed state + checks field values)
- Auto-fillable field filtering (phone, email, address, web links)
- Enhanced JSONL logging with field metadata

⚠️ **Limited:**

- Radio buttons: Blindly selects first option (no question understanding)
- Checkboxes: Only handles consent, not questions

❌ **Not Implemented:**

- Yes/No question semantic understanding
- Radio button answer resolution based on question type
- Dropdown/select field handling
- Work authorization question logic
- Sponsorship question logic

## Answer Bank

Static dictionary in `bot_manual.py` (lines 17-36):

**Numeric answers:** years_experience='1', GPA='3.5', notice_period='2'

**Text answers:** linkedin_url, portfolio_url, github_url, skills_summary, why_interested

**User-editable** - modify ANSWER_BANK to customize responses.

## Technical Stack

- Python 3.14.0
- Playwright 1.57.0 (Chromium automation)
- Persistent browser context (./browser_data/)
- Keyboard controls: Tab, Enter, Space, Control+A
- State machine architecture
- Semantic field classification (NUMERIC_FIELD, TEXT_FIELD, UNKNOWN_FIELD)
- JSONL logging with field resolution metadata

## File Structure

```
/Users/sawyersmith/linkedin_is_lame/
  PLAN.md                    # This file
  README.md                  # User documentation
  requirements.txt           # Python dependencies
  bot_manual.py             # Main script (942 lines)
  log.jsonl                 # Structured logs with field metadata
  browser_data/             # Persistent Chrome session
  /Users/sawyersmith/Documents/resume2025.pdf  # Resume path
```
