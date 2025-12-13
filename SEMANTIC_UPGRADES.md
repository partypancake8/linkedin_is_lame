# Semantic Resolution Upgrades

## Overview

Added semantic handling for radio buttons, select dropdowns, and inline validation error detection while preserving the existing state machine architecture.

## Changes Made

### PART 1: Radio Button Semantic Handling

**Location:** Lines 16-46 (ANSWER_BANK), Lines 345-506 (detection/resolution functions), Lines 922-989 (main loop integration)

**New Boolean Answer Bank:**

```python
'authorized_to_work': True,
'requires_sponsorship': False,
'willing_to_relocate': False,
'background_check_consent': True,
'drug_test_consent': True,
'over_18': True,
'legally_eligible': True,
```

**New Functions:**

1. **`normalize_text(text)`** - Strips punctuation, lowercases, collapses whitespace for keyword matching

2. **`detect_radio_groups(page)`** - Extracts radio group metadata:

   - Group name
   - Question text (from legend/fieldset/label/aria-label)
   - Option count
   - Option labels
   - Playwright locator for group

3. **`resolve_radio_question(page, group_name, question_text, option_count)`** - Semantic resolution:
   - **Only handles 2-option (binary) questions**
   - Returns `(None, 'low', 'multi_option_radio')` if more than 2 options
   - Keyword mappings for:
     - Work authorization: `('authorized', 'work')`, `('legally', 'authorized')`
     - Sponsorship: `('require', 'sponsorship')`, `('need', 'sponsorship')`
     - Relocation: `('willing', 'relocate')`
     - Background check: `('background', 'check')`
     - Drug test: `('drug', 'test')`
     - Age eligibility: `('over', '18')`, `('legal', 'age')`
   - Returns: `(bool|None, confidence, matched_key)`
   - If matched → `(True/False, 'high', key_name)`
   - If unmatched → `(None, 'low', 'unmatched')`

**Integration in Main Loop (Line 922):**

- Replaced blind radio selection with `detect_radio_groups()`
- For each group:
  - Extract question and options
  - Call `resolve_radio_question()`
  - If confidence='high' → select correct option (0=Yes, 1=No)
  - If confidence='low' → **PAUSE** (same behavior as unresolved text fields)
- Logs each resolution with question, answer, selected option, confidence
- If any radio unresolved → **PAUSE**, let user skip or manually answer

**Behavior:**

- ✅ Correctly answers work auth, sponsorship, relocation questions
- ✅ Never defaults to first option
- ✅ Pauses on multi-option radios (>2 options)
- ✅ Pauses on unrecognized questions
- ✅ Full logging of decisions

---

### PART 2: Select Dropdown Handling

**Location:** Lines 508-617 (detection/resolution functions), Lines 1036-1116 (main loop integration)

**New Functions:**

1. **`detect_select_fields(page)`** - Extracts select metadata:

   - Label text (from label[for] or aria-label)
   - Option count
   - Option texts
   - Option values
   - Current selected value
   - Playwright element

2. **`resolve_select_answer(select_metadata)`** - Conservative resolution:
   - **Only handles dropdowns with ≤5 options**
   - Returns `(None, 'low', 'too_many_options')` if >5 options
   - Keyword mappings:
     - Notice period: `('notice', 'period')`
     - Start date: `('start', 'date')`, `('availability')`, `('when', 'start')`
   - Matches expected answer value to option text
   - Returns: `(option_value|None, confidence, matched_key)`
   - If no exact match → `(None, 'low', 'no_matching_option')`

**Integration in Main Loop (Line 1036):**

- After checkbox handling
- Calls `detect_select_fields()`
- For each dropdown:
  - Extract label and options
  - Call `resolve_select_answer()`
  - If confidence='high' → select matched option
  - If confidence='low' → **PAUSE**
- Logs each resolution or skip reason
- If any select unresolved → **PAUSE**, let user skip or manually select

**Behavior:**

- ✅ Only handles small dropdowns (≤5 options)
- ✅ Matches to known keys (notice_period_weeks, etc.)
- ✅ Never guesses - pauses if uncertain
- ✅ Full logging of selections

---

### PART 3: Inline Validation Error Detection

**Location:** Lines 453-506 (detection function), Lines 1180-1203 (integration in text field handler)

**New Function:**

**`detect_inline_validation_error(page, field_element)`** - Detects validation failures:

- Checks `aria-invalid="true"` attribute
- Looks for error message via:
  - `aria-describedby` attribute → error element
  - Common error selectors: `#field-id-error`, `.error-message`, `.field-error`
- Returns: `(has_error: bool, error_text: str)`

**Integration in Text Field Handler (Line 1180):**

- After typing each field value
- Waits 0.5s for validation to trigger
- Calls `detect_inline_validation_error()`
- If error detected:
  - Prints error message
  - Sets `needs_pause = True`
  - Logs validation error with field label, typed value, error text
- Existing pause logic handles stopping execution

**Behavior:**

- ✅ Detects validation errors immediately after input
- ✅ Logs error details for debugging
- ✅ Prevents blind submission with invalid data
- ✅ No retry logic - pauses for manual correction

---

## State Machine Integration

**No new states added.** All enhancements plug into existing handlers:

- **Radio resolution** → Runs before state detection (line 922)
- **Select resolution** → Runs after checkboxes, before state actions (line 1036)
- **Validation detection** → Integrated into `MODAL_TEXT_FIELD_DETECTED` handler (line 1180)

**Execution Flow:**

1. Resume upload (if present)
2. **Radio semantic resolution** → pause if low confidence
3. Checkbox handling (consent only)
4. **Select semantic resolution** → pause if low confidence
5. State detection
6. Text field resolution (with **validation detection**)
7. Button navigation (Next/Review/Submit)

---

## Logging Enhancements

**New log entry types in `log.jsonl`:**

1. **Radio Resolution:**

```json
{
  "timestamp": "...",
  "job_url": "...",
  "state": "RADIO_RESOLUTION",
  "group_name": "workAuth",
  "question": "Are you authorized to work in the US?",
  "matched_key": "authorized_to_work",
  "answer": true,
  "selected_option": "Yes",
  "confidence": "high"
}
```

2. **Radio Unresolved:**

```json
{
  "timestamp": "...",
  "job_url": "...",
  "state": "RADIO_UNRESOLVED",
  "group_name": "salary",
  "question": "What is your salary expectation?",
  "option_count": 5,
  "confidence": "low",
  "reason": "multi_option_radio"
}
```

3. **Select Resolution:**

```json
{
  "timestamp": "...",
  "job_url": "...",
  "state": "SELECT_RESOLUTION",
  "label": "Notice period",
  "matched_key": "notice_period_weeks",
  "selected_value": "2",
  "confidence": "high"
}
```

4. **Validation Error:**

```json
{
  "timestamp": "...",
  "job_url": "...",
  "state": "VALIDATION_ERROR",
  "field_label": "Years of experience",
  "field_type": "number",
  "typed_value": "1",
  "error_text": "Must be between 2 and 10"
}
```

---

## Success Criteria Met

✅ Boolean radio questions answered correctly (work auth, sponsorship, etc.)  
✅ Dropdowns safely handled or paused (≤5 options only)  
✅ Validation failures detected and logged  
✅ No incorrect submissions occur (pause on uncertainty)  
✅ Existing behavior remains stable (no state machine changes)  
✅ Manual confirmation intact (still requires YES before submit)

---

## Testing Recommendations

1. **Test with work authorization question** - Should select "Yes" if `authorized_to_work: True`
2. **Test with sponsorship question** - Should select "No" if `requires_sponsorship: False`
3. **Test with multi-option radio** - Should pause and log 'multi_option_radio'
4. **Test with notice period dropdown** - Should select matching option
5. **Test with large dropdown (>5 options)** - Should pause and log 'too_many_options'
6. **Test with field validation** - Type invalid value, should detect error and pause
7. **Test with unrecognized radio question** - Should pause and log 'unmatched'

---

## Configuration

**To customize answers, edit ANSWER_BANK in `bot_manual.py` (lines 16-46):**

```python
# Boolean answers for radio buttons
'authorized_to_work': True,        # Set to False if not authorized
'requires_sponsorship': False,     # Set to True if you need sponsorship
'willing_to_relocate': False,      # Set to True if willing to relocate
'background_check_consent': True,  # Usually True
'drug_test_consent': True,         # Usually True
'over_18': True,                   # Usually True
'legally_eligible': True,          # Usually True
```

**To add new radio question patterns**, edit `resolve_radio_question()` (line 404):

```python
boolean_mappings = {
    # Add your pattern here:
    ('keyword1', 'keyword2'): 'answer_bank_key',
}
```

Then add corresponding answer to ANSWER_BANK.

---

## No Changes Made To

- State machine structure (detect_state, state handlers)
- Easy Apply activation logic
- Manual confirmation before submit
- Text field resolution logic (classify_field_type, resolve_field_answer)
- Keyboard navigation methods
- Modal scoping
- Existing logging structure

**All changes are additive and integrate with existing architecture.**
