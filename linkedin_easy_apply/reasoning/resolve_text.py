"""Text field resolution logic"""

from datetime import datetime, timedelta
from linkedin_easy_apply.data.answer_bank import ANSWER_BANK


def resolve_field_answer(field_metadata, field_classification):
    """
    Pure function: given field metadata and classification, return answer or None.
    Supports: NUMERIC_FIELD, TEXT_FIELD, DATE_FIELD, UNKNOWN_FIELD
    
    Returns:
        str: value to type into field
        None: if no confident match found
    """
    label = field_metadata.get('label', '').lower()
    placeholder = field_metadata.get('placeholder', '').lower()
    aria_label = field_metadata.get('aria_label', '').lower()
    
    # Combine for matching
    combined_text = f"{label} {placeholder} {aria_label}"
    
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
    
    # No confident match
    return None
