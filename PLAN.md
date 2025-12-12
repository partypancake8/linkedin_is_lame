# LinkedIn Easy Apply Bot - MVP Plan

## Goal

Single-run Python script that attempts one LinkedIn Easy Apply submission given a job URL. Detects Easy Apply availability, submits if flow is trivial, skips if complexity exceeds MVP scope, logs outcome to JSONL, and exits.

## Supported Flow

1. Launch browser with persistent Chrome profile (LinkedIn session assumed active)
2. Navigate to job URL (provided via CLI argument)
3. Detect Easy Apply button (10s timeout)
4. Click button and wait for modal to appear
5. Check modal is single-step (no "Next" or "Continue" buttons)
6. Upload resume PDF if file input exists
7. Click "Submit" button
8. Wait for confirmation (modal close + success message)
9. Log result to `log.jsonl`
10. Exit

**All steps are linear. Any failure or skip condition immediately exits.**

## Skip Rules

Script skips (logs `SKIPPED` status) and exits if:

1. Easy Apply button not found within 10 seconds
2. Modal does not appear after clicking button
3. Modal contains buttons with text "Next" or "Continue" (multi-step flow)
4. Required text input fields detected (questions requiring answers)
5. CAPTCHA or security challenge detected

**Skipping is a successful outcome** - it prevents the bot from attempting unsupported flows.

## Failure Policy

- Log `FAILED` status with exception message for unexpected errors
- Include `steps_completed` counter in log to identify where failure occurred
- No retries - script exits immediately on failure
- Failures should be rare if skip rules are comprehensive

## MVP Success Criteria

1. Script runs without crashing on valid job URLs
2. Correctly identifies and skips unsupported Easy Apply flows
3. Successfully uploads resume and submits for simple one-step flows
4. Appends valid JSON entry to `log.jsonl` on every run
5. Chrome profile session persists across runs (no re-login required)

## Non-Goals

- Multi-job processing
- Scheduling or automation loops
- Resume tailoring or customization
- Answering application questions
- Retry logic or error recovery
- Dashboard or analytics
- Automated login

## Technical Stack

- Python 3.10+
- Playwright (browser automation)
- Chrome browser with persistent profile
- JSONL for logging (append-only, no database)

## File Structure

```
/Users/sawyersmith/linkedin_is_lame/
  PLAN.md           # This file
  requirements.txt  # Python dependencies
  bot.py            # Main script
  log.jsonl         # Structured logs (created on first run)
  resume.pdf        # Resume to upload (hardcoded path)
```
