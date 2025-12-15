"""Text field detection and validation"""


def detect_text_fields_in_modal(page):
    """Detect visible text input fields inside Easy Apply modal only"""
    try:
        # Scope detection to modal container only
        modal_selector = '[role="dialog"]'

        # Find all text-like inputs within the modal
        field_selectors = [
            f'{modal_selector} input[type="text"]',
            f'{modal_selector} input[type="number"]',
            f'{modal_selector} input[type="date"]',
            f"{modal_selector} textarea",
        ]

        # Fields to SKIP - these are auto-fillable or optional
        skip_patterns = [
            "phone",
            "mobile",
            "telephone",
            "cell",
            "phone number",  # Phone fields
            "email",
            "e-mail",
            "email address",  # Email fields
            "address",
            "street",
            "city",
            "zip",
            "postal",
            "country",  # Address fields
            "linkedin",
            "website",
            "url",
            "portfolio",  # Social/web links
            "first name",
            "last name",
            "full name",  # Name fields (auto-filled)
            "prefix",
            "suffix",  # Name prefix/suffix
        ]

        detected_fields = []

        for selector in field_selectors:
            fields = page.locator(selector)
            count = fields.count()

            for i in range(count):
                field = fields.nth(i)

                # Skip if disabled or hidden
                if not field.is_visible() or field.is_disabled():
                    continue

                # Skip if field already has a value (already filled)
                current_value = field.input_value()
                if current_value and current_value.strip():
                    continue

                # Extract metadata
                field_id = field.get_attribute("id") or ""
                field_name = field.get_attribute("name") or ""
                placeholder = field.get_attribute("placeholder") or ""
                aria_label = field.get_attribute("aria-label") or ""

                # Try to find associated label
                label_text = ""
                if field_id:
                    label = page.locator(f'label[for="{field_id}"]')
                    if label.count() > 0:
                        label_text = label.first.inner_text().strip()

                # Determine field type
                tag_name = field.evaluate("el => el.tagName").lower()
                input_type = (
                    field.get_attribute("type") if tag_name == "input" else "textarea"
                )

                # Check if this field should be skipped
                should_skip = False
                text_to_check = f"{field_id} {field_name} {label_text} {placeholder} {aria_label}".lower()

                for pattern in skip_patterns:
                    if pattern in text_to_check:
                        should_skip = True
                        print(
                            f"  ⏭️  Skipping auto-fillable field: {label_text or placeholder or field_name} (matched: {pattern})"
                        )
                        break

                if should_skip:
                    continue

                detected_fields.append(
                    {
                        "element": field,
                        "tag": tag_name,
                        "input_type": input_type,
                        "label": label_text,
                        "aria_label": aria_label,
                        "placeholder": placeholder,
                        "name": field_name,
                    }
                )

        return detected_fields

    except Exception as e:
        print(f"  ⚠️ Error detecting text fields: {e}")
        return []


def detect_inline_validation_error(page, field_element):
    """
    Detect inline validation errors near a field.
    Returns: (has_error: bool, error_text: str)
    """
    try:
        # Check if field has aria-invalid
        aria_invalid = field_element.get_attribute("aria-invalid")
        if aria_invalid == "true":
            # Try to find error message
            field_id = field_element.get_attribute("id") or ""

            # Look for aria-describedby error message
            aria_describedby = field_element.get_attribute("aria-describedby")
            if aria_describedby:
                error_el = page.locator(f"#{aria_describedby}")
                if error_el.count() > 0:
                    error_text = error_el.first.inner_text().strip()
                    if error_text:
                        return (True, error_text)

            # Look for nearby error elements (common patterns)
            error_selectors = [
                f'[role="dialog"] [id="{field_id}-error"]',
                f'[role="dialog"] .error-message',
                f'[role="dialog"] .field-error',
                f'[role="dialog"] [class*="error"][class*="text"]',
            ]

            for selector in error_selectors:
                error_el = page.locator(selector)
                if error_el.count() > 0 and error_el.first.is_visible():
                    error_text = error_el.first.inner_text().strip()
                    if error_text:
                        return (True, error_text)

            return (True, "Validation error (no error text found)")

        return (False, "")
    except Exception as e:
        return (False, "")
