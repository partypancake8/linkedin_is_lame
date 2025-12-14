"""Text field resolution logic"""

from datetime import datetime, timedelta
from linkedin_easy_apply.data.answer_bank import ANSWER_BANK


def resolve_field_answer(field_metadata, field_classification):
    """
    Pure function: given field metadata and classification, return answer or None.
    
    Supports classifications:
    - TIER1_APPLICANT_FULL_NAME: Return user's full name
    - TIER1_CURRENT_DATE: Return today's date in MM/DD/YYYY format
    - TIER1_CITY_LOCATION: Return user's current city
    - TIER2_APPLICANT_EMAIL: Return user's email
    - TIER2_APPLICANT_PHONE: Return user's phone number
    - NUMERIC_FIELD: Match numeric answer from bank
    - TEXT_FIELD: Match text answer from bank
    - DATE_FIELD: Return future date (legacy behavior)
    - UNKNOWN_FIELD: Return None
    
    Returns:
        str: value to type into field
        None: if no confident match found (triggers pause/skip)
    """
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine for matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
    # TIER-1 FIELD RESOLUTION (highest priority, always safe)
    
    if field_classification == 'TIER1_APPLICANT_FULL_NAME':
        # Deterministic: always return configured full name
        if 'applicant_full_name' in ANSWER_BANK:
            return ANSWER_BANK['applicant_full_name']
        # If not configured, fail safely (pause)
        return None
    
    if field_classification == 'TIER1_CURRENT_DATE':
        # Deterministic: always return today's date in MM/DD/YYYY format
        # No inference, no date math - just current date
        return datetime.now().strftime('%m/%d/%Y')
    
    if field_classification == 'TIER1_CITY_LOCATION':
        # Deterministic: always return configured city location
        if 'applicant_city_location' in ANSWER_BANK:
            return ANSWER_BANK['applicant_city_location']
        # If not configured, fail safely (pause)
        return None
    
    # TIER-2 FIELD RESOLUTION (contact information, usually safe)
    
    if field_classification == 'TIER2_APPLICANT_EMAIL':
        # Check if field is empty (additional safety check)
        # Return configured email if available
        if 'applicant_email' in ANSWER_BANK:
            return ANSWER_BANK['applicant_email']
        # If not configured, fail safely (pause)
        return None
    
    if field_classification == 'TIER2_APPLICANT_PHONE':
        # Check if field is empty (additional safety check)
        # Return configured phone number if available
        if 'applicant_phone_number' in ANSWER_BANK:
            return ANSWER_BANK['applicant_phone_number']
        # If not configured, fail safely (pause)
        return None
    
    if field_classification == 'TIER2_COLLEGE_UNIVERSITY':
        # Return configured college/university name
        if 'applicant_college_university' in ANSWER_BANK:
            return ANSWER_BANK['applicant_college_university']
        # If not configured, fail safely (pause)
        return None
    
    # SKIP CREATIVE/ESSAY FIELDS - Always return None to trigger pause
    if field_classification == 'SKIP_CREATIVE_FIELD':
        return None
    
    # EXISTING RESOLUTION LOGIC (unchanged for backward compatibility)
    
    # DATE FIELD - return current date + 30 days in mm/dd/yyyy format
    if field_classification == 'DATE_FIELD':
        future_date = datetime.now() + timedelta(days=30)
        return (future_date.strftime('%m/%d/%Y'), 'high', 'start_date')
    
    # Keyword → answer bank key mappings
    keyword_mappings = {
        # Numeric mappings
        ('year', 'experience'): 'years_experience',
        ('years', 'experience'): 'years_experience',
        ('work experience',): 'work_experience',
        ('total experience',): 'total_experience',
        ('notice period', 'week'): 'notice_period_weeks',
        ('notice',): 'notice_period',
        ('gpa',): 'gpa',
        
        # Text mappings
        ('linkedin', 'url'): 'linkedin_url',
        ('linkedin', 'profile'): 'linkedin_url',
        ('portfolio', 'url'): 'portfolio_url',
        ('portfolio', 'website'): 'portfolio_url',
        ('github',): 'github_url',
        ('website',): 'website',
        ('skills',): 'skills_summary',
        ('why', 'interested'): 'why_interested',
        ('why', 'want', 'work'): 'why_interested',
    }
    
    # Try to match keywords
    matched_key = None
    for keywords, bank_key in keyword_mappings.items():
        if all(kw in combined_text for kw in keywords):
            matched_key = bank_key
            break
    
    if matched_key and matched_key in ANSWER_BANK:
        answer = ANSWER_BANK[matched_key]
        
        # TYPE SAFETY CHECK
        if field_classification == 'NUMERIC_FIELD':
            # Ensure answer is numeric
            if not answer.replace('.', '').isdigit():
                print(f"  ⚠️ Warning: Numeric field matched to non-numeric answer '{matched_key}'")
                return None
        
        return answer
    
    # No confident match - return None (triggers pause/skip, NO "TEST" fallback)
    return None
