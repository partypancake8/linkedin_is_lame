"""Checkbox detection and classification"""


def detect_checkbox_groups(page):
    """
    Detect checkbox groups and classify them as either:
    - RADIO_EQUIVALENT: Mutually exclusive choices (Yes/No/Decline)
    - CONSENT: Legal agreements, acknowledgements
    - COMMUNICATION: Marketing opt-ins
    - UNKNOWN: Other checkboxes

    Returns dict with:
    - radio_equivalent: list of groups that should be treated like radio buttons
    - standard_checkboxes: list of regular checkboxes to process normally
    """
    try:
        radio_equivalent_groups = []
        standard_checkboxes = []

        checkboxes = page.locator('[role="dialog"] input[type="checkbox"]')
        checkbox_count = checkboxes.count()

        if checkbox_count == 0:
            return {"radio_equivalent": [], "standard_checkboxes": []}

        # Group checkboxes by their parent container
        checkbox_groups = {}

        for i in range(checkbox_count):
            checkbox = checkboxes.nth(i)
            checkbox_id = checkbox.get_attribute("id") or f"checkbox_{i}"

            # Get label text
            label_text = ""
            label_elem = page.locator(f'label[for="{checkbox_id}"]')
            if label_elem.count() > 0:
                label_text = label_elem.first.inner_text().strip()

            # Try to find parent question container
            try:
                parent_info = checkbox.evaluate(
                    """el => {
                    let current = el;
                    // Look for parent fieldset or form group
                    while (current && current.tagName !== 'FIELDSET') {
                        if (current.classList && 
                            (current.classList.contains('fb-form-element') || 
                             current.classList.contains('form-group') ||
                             current.getAttribute('role') === 'group')) {
                            break;
                        }
                        current = current.parentElement;
                    }
                    
                    if (current) {
                        // Get question text from legend or label
                        const legend = current.querySelector('legend');
                        if (legend) return {
                            question: legend.textContent.trim(),
                            containerId: current.id || current.className
                        };
                        
                        const groupLabel = current.querySelector('label:not([for])');
                        if (groupLabel) return {
                            question: groupLabel.textContent.trim(),
                            containerId: current.id || current.className
                        };
                    }
                    return {question: '', containerId: 'default'};
                }"""
                )

                question_text = parent_info.get("question", "")
                container_id = parent_info.get("containerId", "default")
            except:
                question_text = ""
                container_id = "default"

            # Group by container
            if container_id not in checkbox_groups:
                checkbox_groups[container_id] = {
                    "question": question_text,
                    "checkboxes": [],
                }

            checkbox_groups[container_id]["checkboxes"].append(
                {
                    "element": checkbox,
                    "id": checkbox_id,
                    "label": label_text,
                    "index": i,
                }
            )

        # Analyze each group to determine if it's radio-equivalent
        for container_id, group_data in checkbox_groups.items():
            checkboxes_in_group = group_data["checkboxes"]
            question = group_data["question"]

            # Only consider groups with 2+ checkboxes
            if len(checkboxes_in_group) < 2:
                # Single checkbox - treat as standard
                standard_checkboxes.extend(checkboxes_in_group)
                continue

            # Check if labels indicate mutually exclusive choices
            labels = [cb["label"].lower() for cb in checkboxes_in_group]

            # Patterns that indicate mutually exclusive choices
            mutually_exclusive_patterns = [
                # Yes/No patterns
                {"yes", "no"},
                {"yes", "no", "not applicable"},
                {"yes", "no", "decline"},
                {"yes", "no", "prefer not to answer"},
                {"yes", "no", "i prefer not to specify"},
                # Decline patterns
                {"decline", "decline to answer"},
                {"decline to self-identify", "i prefer not to answer"},
                # Status patterns
                {"currently enrolled", "completed", "not applicable"},
                {"currently attending", "graduated", "did not attend"},
            ]

            # Check if any label starts with common mutually exclusive indicators
            mutually_exclusive_starts = [
                "yes",
                "no",
                "not applicable",
                "decline",
                "i prefer not",
            ]
            has_exclusive_labels = sum(
                any(label.startswith(pattern) for pattern in mutually_exclusive_starts)
                for label in labels
            )

            # Classify as radio-equivalent if:
            # 1. Has 2-4 options (typical for mutually exclusive)
            # 2. Labels match known patterns OR multiple labels start with exclusive indicators
            is_radio_equivalent = 2 <= len(checkboxes_in_group) <= 4 and (
                any(set(labels) >= pattern for pattern in mutually_exclusive_patterns)
                or has_exclusive_labels >= 2
            )

            if is_radio_equivalent:
                radio_equivalent_groups.append(
                    {
                        "question": question,
                        "checkboxes": checkboxes_in_group,
                        "option_count": len(checkboxes_in_group),
                        "option_labels": [cb["label"] for cb in checkboxes_in_group],
                        "classification": "RADIO_EQUIVALENT",
                    }
                )
            else:
                # Not mutually exclusive - treat as standard checkboxes
                standard_checkboxes.extend(checkboxes_in_group)

        return {
            "radio_equivalent": radio_equivalent_groups,
            "standard_checkboxes": standard_checkboxes,
        }

    except Exception as e:
        print(f"  ⚠️ Error detecting checkbox groups: {e}")
        return {"radio_equivalent": [], "standard_checkboxes": []}
