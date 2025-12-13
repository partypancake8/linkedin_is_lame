# Keyboard Navigation Update

## What Changed

The bot now uses **keyboard controls** instead of mouse clicks:

### Old Approach (Clicks)

```python
button.click()              # Detectable by LinkedIn
checkbox.click()            # Triggers anti-bot
radio.click(force=True)     # LinkedIn blocks this
```

### New Approach (Keyboard)

```python
element.focus()             # Focus element
page.keyboard.press("Tab")  # Navigate like a human
page.keyboard.press("Space") # Select radio/checkbox
page.keyboard.press("Enter") # Press button
```

## Why This Works Better

1. **More Human-Like** - Real users navigate with Tab/Enter
2. **Harder to Detect** - Keyboard events are harder to distinguish from real input
3. **More Reliable** - Bypasses click interception
4. **Natural Timing** - Includes realistic delays between keypresses

## Keyboard Actions

| Action          | Key              | Use Case                     |
| --------------- | ---------------- | ---------------------------- |
| Navigate        | `Tab`            | Move between form fields     |
| Select Radio    | `Space`          | Choose radio button option   |
| Toggle Checkbox | `Space`          | Check/uncheck consent boxes  |
| Press Button    | `Enter`          | Submit, Next, Review buttons |
| Fill Input      | Type with delays | 50-150ms per character       |

## Human Delays

```python
human_delay(300, 800)  # Random 300-800ms pause
keyboard.type(text, delay=random.randint(50, 150))  # Realistic typing
```

## Example Flow

```
1. Tab to first radio button → Press Space
2. Tab to second radio button → Press Space
3. Tab through form fields
4. Focus Submit button → Press Enter
5. Wait 800-1200ms for response
```

## Testing

Run with keyboard navigation:

```bash
./run_manual.sh "https://www.linkedin.com/jobs/view/XXXXXXX/"
```

Watch the terminal - you'll see:

```
✓ Selected radio group 'certification' (keyboard)
✓ Checked consent checkbox (keyboard)
✓ Pressed 'Review' button (keyboard)
```

## Advantages

- ✅ Mimics actual human interaction patterns
- ✅ No forced clicks or JavaScript hacks
- ✅ Works even when elements are "protected"
- ✅ More consistent across different form structures
