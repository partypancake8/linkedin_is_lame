# LinkedIn Easy Apply Bot

Minimal Python automation for LinkedIn Easy Apply submissions.

## Setup

1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Configure paths in `bot.py`:**

   - `CHROME_USER_DATA_DIR`: Your Chrome profile directory (default: `~/Library/Application Support/Google/Chrome`)
   - `CHROME_PROFILE`: Chrome profile name (default: `Default`)
   - `RESUME_PATH`: Path to your resume PDF (update this!)

3. **Prepare resume:**

   - Place your resume PDF in the project directory or update `RESUME_PATH` in `bot.py`

4. **Ensure LinkedIn session:**
   - Open Chrome and log into LinkedIn
   - Keep the browser profile active (the bot uses your existing session)

## Usage

```bash
python bot.py "https://www.linkedin.com/jobs/view/123456789/"
```

The script will:

- Open the job URL in Chrome
- Detect Easy Apply availability
- Submit if flow is simple (single-step, no questions)
- Skip if complexity exceeds MVP scope
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
- No automated login - uses your existing Chrome session
- No retries - exits immediately on skip/fail
