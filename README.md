# LinkedIn Easy Apply Bot

Minimal Python automation for LinkedIn Easy Apply submissions.

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

3. **Configure resume path in `bot.py` if needed:**
   - `RESUME_PATH`: Currently set to `/Users/sawyersmith/Documents/resume2025.pdf`

## Usage

### Option 1: Manual Trigger Bot (Recommended - Most Reliable)

This approach works around LinkedIn's bot detection by having you manually click Easy Apply, then automating the form filling:

```bash
./run_manual.sh "https://www.linkedin.com/jobs/view/123456789/"
```

**What happens:**

1. Browser opens to the job page
2. You manually click the "Easy Apply" button
3. Press Enter when the modal opens
4. Bot automatically fills and submits the form

**Advantages:**

- Bypasses LinkedIn's anti-automation completely
- 100% reliable
- Still saves significant time (no manual form filling)

### Option 2: Fully Automated Bot (Experimental)

**Quick run with helper script:**

```bash
./run.sh "https://www.linkedin.com/jobs/view/123456789/"
```

**Or run directly (remember to activate venv first):**

```bash
source venv/bin/activate
python bot.py "https://www.linkedin.com/jobs/view/123456789/"
```

The script will:

- Open the job URL in Chrome
- Attempt to automate Easy Apply (may be blocked by LinkedIn)
- Submit if flow is simple (single-step, no questions)
- Skip if complexity exceeds MVP scope

**Note:** This fully automated approach is unreliable due to LinkedIn's bot detection. Use Option 1 for reliable results.

- Log result to `log.jsonl`

## What Gets Skipped

- Easy Apply button not found
- Multi-step applications (has "Next" or "Continue" buttons)
- Applications requiring text answers
- Modal doesn't appear or submit fails

**Skipping is normal and expected.**

## Logs

All runs are logged to `log.jsonl`:

```json
{"timestamp": "2025-12-12T15:30:00Z", "job_url": "...", "status": "SUCCESS", "steps_completed": 8}
{"timestamp": "2025-12-12T15:31:00Z", "job_url": "...", "status": "SKIPPED", "failure_reason": "Multi-step application detected", "steps_completed": 4}
```

Status values: `SUCCESS`, `SKIPPED`, `FAILED`

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
