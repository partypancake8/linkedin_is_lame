"""Radio button detection"""


def detect_radio_groups(page):
    """
    Detect and extract metadata for all radio groups in modal.
    Returns list of radio group metadata dicts.
    """
    try:
        radio_groups_data = []
        processed_names = set()

        radios = page.locator('[role="dialog"] input[type="radio"]')
        radio_count = radios.count()

        for i in range(radio_count):
            radio = radios.nth(i)
            name = radio.get_attribute("name")

            if not name or name in processed_names:
                continue

            processed_names.add(name)

            # Get all radios in this group
            group_radios = page.locator(
                f'[role="dialog"] input[type="radio"][name="{name}"]'
            )
            option_count = group_radios.count()

            # Extract question text from label/legend/fieldset
            question_text = ""

            # Try to find parent fieldset/legend
            try:
                parent_fieldset = radio.evaluate(
                    """el => {
                    let current = el;
                    while (current && current.tagName !== 'FIELDSET') {
                        current = current.parentElement;
                    }
                    if (current) {
                        const legend = current.querySelector('legend');
                        if (legend) return legend.textContent;
                        const label = current.querySelector('label');
                        if (label) return label.textContent;
                    }
                    return '';
                }"""
                )
                if parent_fieldset:
                    question_text = parent_fieldset.strip()
            except:
                pass

            # If no fieldset, try first radio's label
            if not question_text:
                radio_id = group_radios.first.get_attribute("id")
                if radio_id:
                    label = page.locator(f'[role="dialog"] label[for="{radio_id}"]')
                    if label.count() > 0:
                        question_text = label.first.inner_text().strip()

            # If still no question, try aria-label
            if not question_text:
                aria_label = radio.get_attribute("aria-label")
                if aria_label:
                    question_text = aria_label.strip()

            # Get option labels
            option_labels = []
            for j in range(option_count):
                opt_radio = group_radios.nth(j)
                opt_id = opt_radio.get_attribute("id")
                if opt_id:
                    opt_label = page.locator(f'[role="dialog"] label[for="{opt_id}"]')
                    if opt_label.count() > 0:
                        option_labels.append(opt_label.first.inner_text().strip())
                    else:
                        option_labels.append(f"Option {j+1}")
                else:
                    option_labels.append(f"Option {j+1}")

            radio_groups_data.append(
                {
                    "name": name,
                    "question_text": question_text,
                    "option_count": option_count,
                    "option_labels": option_labels,
                    "radios": group_radios,
                }
            )

        return radio_groups_data
    except Exception as e:
        print(f"  ⚠️ Error detecting radio groups: {e}")
        return []
