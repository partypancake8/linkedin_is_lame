# Architecture Documentation

This document describes the modular architecture of the LinkedIn Easy Apply bot. If you're modifying the codebase (especially with AI assistance), read this file to understand separation of concerns and where different logic belongs.

## Design Principles

### Separation of Concerns

The bot is organized into distinct layers:

1. **Perception** - What is on the page? (read-only DOM queries)
2. **Reasoning** - What should we do? (pure functions, no browser interaction)
3. **Interaction** - Execute actions (keyboard typing, button clicks)
4. **Policy** - Orchestration and control flow (state machine, main loop)

### Key Constraints

- **Keyboard-only navigation** - No mouse clicks, no JavaScript `.click()` hacks
- **Conservative behavior** - Pause on uncertainty rather than guess
- **Modal scoping** - All interactions happen within `[role="dialog"]` context
- **Human-like timing** - Random delays between actions (300-800ms)
- **No retries** - Fail fast and log, don't loop endlessly

## Module Responsibilities

### `linkedin_easy_apply/main.py`

**Purpose:** Entry point and orchestration

**Contains:**

- CLI argument parsing
- Browser launch
- Easy Apply button detection (Tab navigation)
- Main state machine loop
- Multi-step form progression logic
- Manual submission confirmation

**Imports from:** All other modules

**What belongs here:**

- Control flow logic
- State transition decisions
- Manual intervention prompts
- Integration of perception → reasoning → interaction

**What does NOT belong here:**

- DOM selectors (those go in `perception/`)
- Answer resolution logic (goes in `reasoning/`)
- Keyboard automation primitives (goes in `interaction/`)

---

### `linkedin_easy_apply/browser/session.py`

**Purpose:** Browser lifecycle management

**Contains:**

- `launch_browser()` - Returns (context, page)
- Persistent browser context configuration
- Browser arguments (anti-detection flags)

**Dependencies:** Playwright only

**What belongs here:**

- Browser launch options
- Context persistence (`browser_data/` directory)
- User agent configuration
- Viewport settings

**What does NOT belong here:**

- Page navigation logic
- Form interactions
- Resume path configuration (should be in `data/` or passed as parameter)

---

### `linkedin_easy_apply/state/detector.py`

**Purpose:** Determine current UI state

**Contains:**

- `detect_state(page)` - Returns state enum

**States:**

- `JOB_PAGE` - Before modal opens
- `MODAL_TEXT_FIELD_DETECTED` - Form with text inputs
- `MODAL_SINGLE_STEP` - Single-page application
- `MODAL_FORM_STEP` - Multi-step (has Next button)
- `MODAL_REVIEW_STEP` - Final review page
- `SUBMITTED` - Application submitted successfully

**Dependencies:** `perception/` modules

**What belongs here:**

- State detection logic based on element presence
- No actions - pure observation

**What does NOT belong here:**

- Button clicking
- Form filling
- Answer resolution

---

### `linkedin_easy_apply/perception/`

**Purpose:** Detect and extract DOM elements (read-only queries)

#### `perception/text_fields.py`

- `detect_text_fields_in_modal(page)` - Returns list of input metadata
- `detect_inline_validation_error(page, element)` - Check for validation failures

#### `perception/radios.py`

- `detect_radio_groups(page)` - Returns list of radio group metadata
  - Group name, question text, options, option count

#### `perception/selects.py`

- `detect_select_fields(page)` - Returns list of dropdown metadata
  - Label, options, current value

**What belongs here:**

- `page.locator()` calls
- DOM queries (selectors)
- Metadata extraction (labels, values, options)
- Element existence checks

**What does NOT belong here:**

- Typing into fields
- Clicking buttons
- Answer resolution logic
- State transitions

---

### `linkedin_easy_apply/reasoning/`

**Purpose:** Pure logic functions - no browser interaction

#### `reasoning/normalize.py`

- `normalize_text(text)` - Clean text for keyword matching
- `normalize_option_text(text)` - Clean option labels

#### `reasoning/classify.py`

- `classify_field_type(label_text, input_type)` - Returns NUMERIC_FIELD, TEXT_FIELD, or UNKNOWN

#### `reasoning/resolve_text.py`

- `resolve_field_answer(label_text, field_type)` - Match label to answer bank
  - Returns `(answer, confidence, matched_key)`

#### `reasoning/resolve_radio.py`

- `resolve_radio_question(page, group_name, question_text, option_count)` - Semantic yes/no matching
  - Returns `(bool_answer, confidence, matched_key)`

#### `reasoning/resolve_select.py`

- `resolve_select_answer(select_metadata)` - Match dropdown to answer bank
  - Returns `(selected_value, confidence, matched_key)`

**What belongs here:**

- Keyword matching logic
- Answer bank lookups
- Classification rules
- Confidence scoring

**What does NOT belong here:**

- `page.fill()` or `page.click()`
- DOM queries
- State machine logic
- Logging (use return values, let caller log)

---

### `linkedin_easy_apply/interaction/`

**Purpose:** Execute keyboard actions on browser

#### `interaction/keyboard.py`

- `keyboard_fill_input(page, element, value)` - Type into text field with human timing
- `keyboard_select_radio(page, element, option_index)` - Navigate to radio and press Space
- `keyboard_navigate_and_click_button(page, button_text)` - Tab to button and press Enter

#### `interaction/buttons.py`

- `activate_button_in_modal(page, button_text)` - Click button inside modal
- `wait_for_easy_apply_modal(page)` - Wait for modal to appear

**Dependencies:** `utils/timing.py` for `human_delay()`

**What belongs here:**

- `page.keyboard.press()` calls
- `page.keyboard.type()` with realistic delays
- Focus management
- Button activation logic

**What does NOT belong here:**

- Answer resolution
- Field detection
- State detection
- Decision-making logic

---

### `linkedin_easy_apply/data/answer_bank.py`

**Purpose:** User-editable configuration

**Contains:**

- `ANSWER_BANK` dictionary with all user answers
  - Numeric fields: `years_experience`, `gpa`, `notice_period_weeks`
  - Text fields: `linkedin_url`, `github_url`, `skills_summary`
  - Boolean fields: `authorized_to_work`, `requires_sponsorship`, `willing_to_relocate`

**What belongs here:**

- Static user data
- Answer mappings
- Configuration constants

**What does NOT belong here:**

- Logic or functions
- Browser interaction code
- Keyword matching patterns (those go in `reasoning/`)

---

### `linkedin_easy_apply/utils/`

**Purpose:** Shared utilities

#### `utils/timing.py`

- `human_delay(min_ms, max_ms)` - Random sleep with realistic timing

#### `utils/logging.py`

- `log_result(data)` - Append JSON to `log.jsonl`

**What belongs here:**

- Cross-cutting concerns
- Helper functions used by multiple modules
- No business logic

---

## Data Flow Example

**Scenario:** Fill a text field

1. **Perception** detects text fields:

   ```python
   fields = detect_text_fields_in_modal(page)
   # Returns: [{"label": "Years of experience", "element": <locator>, "input_type": "number"}]
   ```

2. **Reasoning** classifies field:

   ```python
   field_type = classify_field_type("Years of experience", "number")
   # Returns: "NUMERIC_FIELD"
   ```

3. **Reasoning** resolves answer:

   ```python
   answer, confidence, key = resolve_field_answer("Years of experience", "NUMERIC_FIELD")
   # Returns: ("1", "high", "years_experience")
   ```

4. **Interaction** types answer:

   ```python
   keyboard_fill_input(page, field["element"], answer)
   # Executes: focus → type with delays
   ```

5. **Perception** checks validation:

   ```python
   has_error, error_text = detect_inline_validation_error(page, field["element"])
   # Returns: (False, None)
   ```

6. **Policy** (main.py) logs result:
   ```python
   log_result({"field_label": "Years of experience", "typed_value": "1", "confidence": "high"})
   ```

**Notice:** Each layer has a clear responsibility. No layer reaches across boundaries.

---

## State Machine Flow

```
JOB_PAGE
   ├─ Tab navigation to find Easy Apply
   └─ Press Enter → Wait for modal

MODAL_TEXT_FIELD_DETECTED
   ├─ Upload resume (if file input present)
   ├─ Resolve and select radio buttons
   ├─ Resolve and select dropdowns
   ├─ Classify and fill text fields
   └─ Detect Next/Review/Submit button

MODAL_FORM_STEP (multi-step)
   ├─ Press Next button
   └─ Loop back to MODAL_TEXT_FIELD_DETECTED

MODAL_REVIEW_STEP
   ├─ Manual confirmation (type YES)
   └─ Press Submit

SUBMITTED
   └─ Verify success, log result, exit
```

---

## Adding New Features

### Adding a new question type

1. Add answer to `data/answer_bank.py`:

   ```python
   'salary_expectation': '80000'
   ```

2. Add keyword pattern to appropriate resolver in `reasoning/`:

   ```python
   ('salary', 'expectation'): 'salary_expectation'
   ```

3. Test with job posting that has this question

**DO NOT:**

- Add logic to `main.py` (use existing resolution functions)
- Create new state (use existing state handlers)
- Add new interaction primitives unless absolutely necessary

### Adding a new field type (e.g., file upload for cover letter)

1. Add detection function to `perception/`:

   ```python
   def detect_cover_letter_input(page):
       return page.locator('input[type="file"][id*="cover"]')
   ```

2. Add interaction function to `interaction/`:

   ```python
   def upload_cover_letter(page, element, path):
       element.set_input_files(path)
   ```

3. Integrate into main loop in `main.py`:
   ```python
   cover_letter = detect_cover_letter_input(page)
   if cover_letter.count() > 0:
       upload_cover_letter(page, cover_letter, COVER_LETTER_PATH)
   ```

### Modifying behavior constraints

**Before modifying:**

- Read this document completely
- Understand which module owns the behavior
- Check if change affects state machine flow
- Verify keyboard-only constraint is preserved

**Safe to modify:**

- Answer bank (`data/answer_bank.py`)
- Keyword patterns (`reasoning/resolve_*.py`)
- Timing delays (`utils/timing.py`)
- Log format (`utils/logging.py`)

**Modify with caution:**

- State detection logic (`state/detector.py`)
- Main loop orchestration (`main.py`)
- Keyboard primitives (`interaction/keyboard.py`)

**DO NOT modify without deep understanding:**

- Browser session configuration (`browser/session.py`)
- Modal scoping selectors
- State machine transitions

---

## Testing Philosophy

**No automated tests** - Behavior is validated manually with real LinkedIn job postings.

**Why:**

- LinkedIn's DOM structure changes frequently
- Testing against real site is more reliable than mocks
- Manual verification ensures human-like behavior

**How to validate changes:**

1. Run bot with known job posting
2. Compare behavior to previous run
3. Check `log.jsonl` for identical decisions
4. Verify no regressions in field resolution

**Test checklist:**

- ✅ Same fields detected
- ✅ Same answers selected
- ✅ Same pause conditions
- ✅ Same keyboard actions
- ✅ Same submission confirmation

---

## Common Pitfalls

### ❌ Adding logic to wrong module

**Bad:**

```python
# In perception/text_fields.py
def detect_text_fields_in_modal(page):
    fields = page.locator('input').all()
    for field in fields:
        answer = resolve_field_answer(field.label)  # ❌ Reasoning in perception
        field.fill(answer)  # ❌ Interaction in perception
```

**Good:**

```python
# In perception/text_fields.py
def detect_text_fields_in_modal(page):
    fields = page.locator('input').all()
    return [{"label": f.label, "element": f} for f in fields]  # ✅ Just return data

# In main.py
fields = detect_text_fields_in_modal(page)
for field in fields:
    answer = resolve_field_answer(field["label"])  # ✅ Reasoning
    keyboard_fill_input(page, field["element"], answer)  # ✅ Interaction
```

### ❌ Breaking keyboard-only constraint

**Bad:**

```python
button.click()  # ❌ Mouse click
page.evaluate("el => el.click()", button)  # ❌ JavaScript hack
```

**Good:**

```python
button.focus()
page.keyboard.press("Enter")  # ✅ Keyboard-only
```

### ❌ Guessing instead of pausing

**Bad:**

```python
if not answer:
    answer = "N/A"  # ❌ Submits incorrect data
```

**Good:**

```python
if not answer:
    needs_pause = True  # ✅ Pause for manual intervention
```

---

## Future AI-Assisted Development

When using AI to modify this codebase:

1. **Provide this file as context** - AI should understand separation of concerns
2. **Specify which module to modify** - Don't let AI dump everything in main.py
3. **Verify keyboard-only constraint** - AI might suggest click-based solutions
4. **Check for state machine changes** - Ensure new states are truly necessary
5. **Validate conservative behavior** - AI should prefer pausing over guessing

**Example prompt:**

> "Add support for date picker fields. Add detection to perception/text_fields.py, add date formatting to reasoning/resolve_text.py, and integrate into main.py text field handler. Preserve keyboard-only constraint and pause if date format is ambiguous."
