"""Field classification logic"""


def classify_field_type(field_metadata):
    """
    Classify field as NUMERIC, TEXT, DATE, or UNKNOWN based on hard rules.
    No AI, no guessing - deterministic only.
    """
    input_type = field_metadata.get('input_type', '').lower()
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine all text for keyword matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
    # RULE 1: HTML5 input type
    if input_type == 'number':
        return 'NUMERIC_FIELD'
    if input_type == 'date':
        return 'DATE_FIELD'
    
    # RULE 2: Keyword patterns for date fields
    date_keywords = [
        'date', 'when', 'start date', 'end date', 'availability',
        'available', 'begin', 'commence',
    ]
    
    for keyword in date_keywords:
        if keyword in combined_text:
            return 'DATE_FIELD'
    
    # RULE 3: Keyword patterns for numeric fields
    numeric_keywords = [
        'year', 'years', 'yrs',
        'experience',
        'month', 'months',
        'salary', 'compensation',
        'notice period', 'notice',
        'gpa',
    ]
    
    for keyword in numeric_keywords:
        if keyword in combined_text:
            return 'NUMERIC_FIELD'
    
    # RULE 4: Textarea is always text
    if field_metadata.get('tag') == 'textarea':
        return 'TEXT_FIELD'
    
    # RULE 5: If it's a text input type
    if input_type in ['text', 'tel', 'url', '']:
        return 'TEXT_FIELD'
    
    # RULE 6: Unknown
    return 'UNKNOWN_FIELD'
