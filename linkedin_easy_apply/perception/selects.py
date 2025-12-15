"""Select dropdown detection"""

from linkedin_easy_apply.reasoning.normalize import normalize_text
from linkedin_easy_apply.utils.timing import human_delay


def detect_select_fields(page):
    """
    Detect <select> dropdowns in modal.
    Returns list of select field metadata dicts.
    """
    try:
        # Patterns to SKIP - these are auto-fillable
        skip_patterns = [
            "phone",
            "mobile",
            "telephone",
            "country code",
            "area code",  # Phone related
            "email",
            "e-mail",
            "email address",  # Email related
            "country",
            "state",
            "province",
            "region",  # Location (often auto-filled)
            "prefix",
            "suffix",  # Name prefix/suffix
            "first name",
            "last name",  # Name fields
        ]

        select_fields = []
        selects = page.locator('[role="dialog"] select')
        select_count = selects.count()

        for i in range(select_count):
            select = selects.nth(i)

            # Skip if disabled or hidden
            if not select.is_visible() or select.is_disabled():
                continue

            # Get label
            label_text = ""
            select_id = select.get_attribute("id")
            if select_id:
                label = page.locator(f'[role="dialog"] label[for="{select_id}"]')
                if label.count() > 0:
                    label_text = label.first.inner_text().strip()

            # Get aria-label fallback
            if not label_text:
                aria_label = select.get_attribute("aria-label")
                if aria_label:
                    label_text = aria_label.strip()

            # If still no label, extract from parent container
            if not label_text:
                try:
                    parent_text = select.evaluate(
                        """el => {
                        let p = el.parentElement;
                        while (p && (!p.innerText || p.innerText.length < 10)) {
                            p = p.parentElement;
                        }
                        return p ? p.innerText : '';
                    }"""
                    )
                    if parent_text:
                        label_text = parent_text.strip()
                except:
                    pass

            # Check if this select should be skipped
            should_skip = False
            select_name = select.get_attribute("name") or ""
            # Normalize and combine all identifying text (handles newlines, extra spaces)
            text_to_check = normalize_text(f"{label_text} {select_name} {select_id}")

            for pattern in skip_patterns:
                # Also normalize the pattern for consistent matching
                normalized_pattern = normalize_text(pattern)
                if normalized_pattern in text_to_check:
                    should_skip = True
                    print(
                        f"  ⏭️  Skipping auto-fillable select: {label_text or select_name} (matched: {pattern})"
                    )
                    break

            if should_skip:
                continue

            # Focus the select to ensure lazy-loaded options populate
            try:
                select.focus()
                human_delay(200, 400)
            except:
                pass

            # Get options (re-query after focus)
            options = select.locator("option")
            option_count = options.count()
            option_texts = []
            option_values = []

            for j in range(option_count):
                opt = options.nth(j)
                opt_text = opt.inner_text().strip()
                opt_value = opt.get_attribute("value") or ""
                if opt_text:  # Skip empty options
                    option_texts.append(opt_text)
                    option_values.append(opt_value)

            # Get currently selected value
            current_value = select.input_value()

            select_fields.append(
                {
                    "element": select,
                    "label": label_text,
                    "option_count": len(option_texts),
                    "option_texts": option_texts,
                    "option_values": option_values,
                    "current_value": current_value,
                }
            )

        return select_fields
    except Exception as e:
        print(f"  ⚠️ Error detecting select fields: {e}")
        return []
