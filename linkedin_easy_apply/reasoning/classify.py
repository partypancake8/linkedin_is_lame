"""Field classification logic"""


def classify_field_type(field_metadata):
    """
    Classify field as TIER1_SAFE, TIER2_SAFE, NUMERIC, TEXT, DATE, or UNKNOWN.
    
    Tier-1 and Tier-2 fields are explicitly named and require strict eligibility checks.
    All other classifications use keyword patterns.
    
    Classification order matters: Tier-1 → Tier-2 → Numeric → Date → Text → Unknown
    """
    input_type = field_metadata.get('input_type', '').lower()
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine all text for keyword matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
    # TIER-1 CLASSIFICATION (checked first - highest priority)
    # These must be explicitly identified before falling through to generic handling
    
    # applicant_full_name - Must be single-line text, not signature/certification
    if input_type in ['text', ''] and field_metadata.get('tag') != 'textarea':
        # Check for name patterns
        name_patterns = ['your name', 'full name', 'legal name', 'first and last name']
        # Anti-patterns (reject these)
        signature_patterns = ['sign', 'certif', 'affirm', 'attest', 'acknowledge']
        
        has_name_pattern = any(pattern in combined_text for pattern in name_patterns)
        has_signature_pattern = any(pattern in combined_text for pattern in signature_patterns)
        
        if has_name_pattern and not has_signature_pattern:
            return 'TIER1_APPLICANT_FULL_NAME'
    
    # current_date_mm_dd_yyyy - Must show date format, not be birth date
    if input_type in ['text', 'date', '']:
        # Check for date format indicators in placeholder or label
        date_format_patterns = ['mm/dd/yyyy', 'mm-dd-yyyy', 'mm/dd/yy', 'date (mm/dd/yyyy)']
        birth_patterns = ['birth', 'dob', 'date of birth', 'born']
        
        has_date_format = any(pattern in combined_text for pattern in date_format_patterns)
        has_birth_pattern = any(pattern in combined_text for pattern in birth_patterns)
        
        # Only match if format is explicit and it's NOT a birth date
        if has_date_format and not has_birth_pattern:
            return 'TIER1_CURRENT_DATE'
    
    # TIER-2 CLASSIFICATION (checked second)
    
    # applicant_email - Must be email type OR contain "email" keyword
    if input_type == 'email' or 'email' in combined_text:
        # Anti-patterns: username creation flows
        username_patterns = ['username', 'user name', 'create account', 'sign up']
        has_username_pattern = any(pattern in combined_text for pattern in username_patterns)
        
        if not has_username_pattern:
            return 'TIER2_APPLICANT_EMAIL'
    
    # applicant_phone_number - Must be tel type OR contain "phone" keyword
    if input_type == 'tel' or 'phone' in combined_text:
        # Anti-patterns: extension fields
        extension_patterns = ['ext', 'extension', 'ext.']
        has_extension_pattern = any(pattern in combined_text for pattern in extension_patterns)
        
        if not has_extension_pattern:
            return 'TIER2_APPLICANT_PHONE'
    
    # applicant_college_university - Education institution field
    if any(pattern in combined_text for pattern in ['college', 'university', 'school name']):
        # Anti-patterns: high school, other non-college questions
        high_school_patterns = ['high school', 'secondary school']
        has_high_school = any(pattern in combined_text for pattern in high_school_patterns)
        
        if not has_high_school:
            return 'TIER2_COLLEGE_UNIVERSITY'
    
    # SKIP CREATIVE/ESSAY FIELDS - Detect and reject long-form creative prompts
    # These require human input and should trigger a pause
    if field_metadata.get('tag') == 'textarea' or 'maxlength' in str(field_metadata):
        creative_patterns = [
            'unique', 'creative', 'catch our eye', 'tell us about yourself',
            'why you', 'what makes you', 'stand out', 'describe yourself',
            'in your own words', 'essay', 'personal statement'
        ]
        has_creative_pattern = any(pattern in combined_text for pattern in creative_patterns)
        
        if has_creative_pattern:
            return 'SKIP_CREATIVE_FIELD'
    
    # EXISTING CLASSIFICATION LOGIC (unchanged)
    # These run after Tier-1 and Tier-2 checks
    
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
