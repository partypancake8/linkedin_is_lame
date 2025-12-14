"""Select dropdown resolution logic"""

from linkedin_easy_apply.data.answer_bank import ANSWER_BANK
from linkedin_easy_apply.reasoning.normalize import normalize_text, normalize_option_text


def resolve_select_answer(select_metadata):
    """
    Resolve select field to answer or None.
    
    STRICT ELIGIBILITY RULE:
    Only self-identification (EEO/diversity) fields are eligible for auto-selection.
    These fields have standardized options and a safe "Decline to answer" fallback.
    
    All other dropdowns (availability, notice period, work-related choices) are
    explicitly rejected as they require business context understanding and lack
    safe defaults.
    
    Eligible types: gender, race, veteran_status, disability_status
    Maximum options: 15 (to accommodate various diversity dropdown formats)
    
    Returns: (resolved_index: int|None, confidence: str, matched_key: str)
    """
    label = select_metadata.get('label', '').lower()
    option_count = select_metadata.get('option_count', 0)
    option_texts = select_metadata.get('option_texts', [])
    option_values = select_metadata.get('option_values', [])
    
    normalized_label = normalize_text(label)
    
    # Eligible dropdown types:
    # 1. Self-identification fields (EEO/diversity with "Decline" option)
    # 2. Start date/notice period (discrete time offsets only, no calendar dates)
    # 3. Education enrollment status (binary Yes/No only, current enrollment)
    # 4. Summer 2026 internship availability (May-August 2026 ONLY, always Yes)
    select_mappings = {
        # Self-identification only (if presented as dropdowns instead of radios)
        ('gender',): 'gender',
        ('sex',): 'gender',
        ('race',): 'race',
        ('ethnicity',): 'race',
        ('ethnic',): 'race',
        ('veteran',): 'veteran_status',
        ('disability',): 'disability_status',
        ('disabled',): 'disability_status',
        
        # Start date / notice period questions
        # Only matches questions about availability timing, not specific dates
        ('when', 'start'): 'start_date_notice_period',
        ('start', 'date'): 'start_date_notice_period',
        ('notice', 'period'): 'start_date_notice_period',
        ('how', 'soon'): 'start_date_notice_period',
        
        # Education enrollment status
        # Only matches questions about CURRENT enrollment, not graduation dates or GPA
        ('currently', 'pursuing', 'degree'): 'education_enrollment_status',
        ('currently', 'enrolled'): 'education_enrollment_status',
        ('current', 'student'): 'education_enrollment_status',
        ('currently', 'attending'): 'education_enrollment_status',
        
        # Summer 2026 internship availability
        # MUST explicitly mention May-August 2026 timeframe - no inference allowed
        # This is checked BEFORE generic 'availability' to prevent false matches
        ('available', 'may', 'august', '2026'): 'summer_2026_internship_availability',
        ('availability', 'may', 'august', '2026'): 'summer_2026_internship_availability',
    }
    
    # Try to match keywords
    matched_key = None
    for keywords, bank_key in select_mappings.items():
        if all(kw in normalized_label for kw in keywords):
            matched_key = bank_key
            break
    
    # Explicit eligibility check: ONLY allowed types
    # - Self-identification fields (with safe "Decline" option)
    # - Start date/notice period (discrete time offsets only)
    # - Education enrollment status (binary Yes/No only)
    # - Summer 2026 internship availability (May-August 2026 only, always Yes)
    eligible_types = ['gender', 'race', 'veteran_status', 'disability_status', 'start_date_notice_period', 'education_enrollment_status', 'summer_2026_internship_availability']
    if matched_key not in eligible_types:
        return (None, 'low', 'unsupported_dropdown_type')
    
    # Self-ID fields can have up to 15 options (to accommodate various formats)
    if option_count > 15:
        return (None, 'low', 'too_many_options')
    
    # At this point, we have a valid self-ID field type
    if matched_key and matched_key in ANSWER_BANK:
        expected_value = ANSWER_BANK[matched_key]
        
        # Handle self-identification fields (match by keyword in option text)
        if matched_key in ['gender', 'race', 'veteran_status', 'disability_status']:
            # Map answer bank value to option text keywords
            if matched_key == 'gender':
                gender_keywords = {
                    'male': ['male', 'man'],
                    'female': ['female', 'woman'],
                    'decline': ['decline', 'prefer not', 'rather not', "don't wish", "dont wish"],
                }
                if expected_value in gender_keywords:
                    for i, opt_text in enumerate(option_texts):
                        opt_normalized = normalize_option_text(opt_text)
                        # Use phrase matching for more precision
                        for kw in gender_keywords[expected_value]:
                            if normalize_option_text(kw) in opt_normalized:
                                return (i, 'high', matched_key)
                    # If no match found and it's decline, try last option
                    if expected_value == 'decline' and len(option_texts) > 0:
                        return (len(option_texts) - 1, 'medium', 'gender_last_option')
            
            elif matched_key == 'race':
                race_keywords = {
                    'white': ['white', 'caucasian'],
                    'black': ['black', 'african american', 'african-american'],
                    'hispanic': ['hispanic', 'latino', 'latina', 'latinx'],
                    'asian': ['asian', 'asian american', 'asian-american'],
                    'native_american': ['native american', 'american indian', 'alaska native', 'indigenous'],
                    'pacific_islander': ['pacific islander', 'native hawaiian'],
                    'two_or_more': ['two or more', 'multiple', 'multiracial'],
                    'decline': ['decline', 'prefer not', 'rather not', "don't wish", "dont wish"],
                }
                if expected_value in race_keywords:
                    for i, opt_text in enumerate(option_texts):
                        opt_normalized = normalize_option_text(opt_text)
                        for kw in race_keywords[expected_value]:
                            if normalize_option_text(kw) in opt_normalized:
                                return (i, 'high', matched_key)
                    # If no match and it's decline, try last option
                    if expected_value == 'decline' and len(option_texts) > 0:
                        return (len(option_texts) - 1, 'medium', 'race_last_option')
            
            elif matched_key == 'veteran_status':
                veteran_keywords = {
                    'veteran': ['protected veteran', 'i am', 'i identify', 'yes'],
                    'not_veteran': ['not a', 'not protected', 'i am not', 'no'],
                    'decline': ['decline', 'prefer not', 'rather not', "don't wish", "dont wish"],
                }
                if expected_value in veteran_keywords:
                    for i, opt_text in enumerate(option_texts):
                        opt_normalized = normalize_option_text(opt_text)
                        for kw in veteran_keywords[expected_value]:
                            if normalize_option_text(kw) in opt_normalized:
                                return (i, 'high', matched_key)
                    # If no match and it's decline, try last option
                    if expected_value == 'decline' and len(option_texts) > 0:
                        return (len(option_texts) - 1, 'medium', 'veteran_last_option')
            
            elif matched_key == 'disability_status':
                disability_keywords = {
                    'yes_disability': ['yes', 'i have', 'have a disability', 'have a'],
                    'no_disability': ['no', 'not have', "don't have", 'do not have'],
                    'decline': ['decline', 'prefer not', 'rather not', "don't wish", "dont wish"],
                }
                if expected_value in disability_keywords:
                    for i, opt_text in enumerate(option_texts):
                        opt_normalized = normalize_option_text(opt_text)
                        for kw in disability_keywords[expected_value]:
                            if normalize_option_text(kw) in opt_normalized:
                                return (i, 'high', matched_key)
                    # If no match and it's decline, try last option
                    if expected_value == 'decline' and len(option_texts) > 0:
                        return (len(option_texts) - 1, 'medium', 'disability_last_option')
            
            # If we got here, couldn't match self-identification option
            return (None, 'low', 'self_id_option_not_matched')
        
        # Handle start_date_notice_period - discrete time offsets only
        elif matched_key == 'start_date_notice_period':
            # Guard: Must have notice_period_weeks configured
            if 'notice_period_weeks' not in ANSWER_BANK:
                return (None, 'low', 'notice_period_not_configured')
            
            expected_weeks = str(ANSWER_BANK['notice_period_weeks']).strip()
            
            # Guard: Reject if any option contains calendar date patterns
            # This prevents matching dropdowns with specific dates like "January 15, 2025"
            date_patterns = ['2024', '2025', '2026', 'january', 'february', 'march', 'april', 'may', 'june',
                           'july', 'august', 'september', 'october', 'november', 'december',
                           'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
            for opt_text in option_texts:
                opt_lower = opt_text.lower()
                if any(pattern in opt_lower for pattern in date_patterns):
                    return (None, 'low', 'contains_calendar_dates')
            
            # Guard: Reject if any option suggests free-text or custom input
            reject_patterns = ['other', 'custom', 'specify', 'enter date', 'type in', 'select date']
            for opt_text in option_texts:
                opt_lower = opt_text.lower()
                if any(pattern in opt_lower for pattern in reject_patterns):
                    return (None, 'low', 'contains_freetext_option')
            
            # Attempt to match based on weeks value
            # Common patterns: "Immediately" (0), "2 weeks", "1 month" (4), "3 months" (12)
            time_offset_keywords = {
                '0': ['immediately', 'right away', 'asap', 'now', 'today'],
                '1': ['1 week', 'one week'],
                '2': ['2 weeks', '2 week', 'two weeks'],
                '3': ['3 weeks', 'three weeks'],
                '4': ['1 month', 'one month', '4 weeks'],
                '6': ['6 weeks', 'six weeks'],
                '8': ['2 months', 'two months', '8 weeks'],
                '12': ['3 months', 'three months', '12 weeks'],
                '16': ['4 months', 'four months'],
                '24': ['6 months', 'six months'],
            }
            
            # Try exact match first
            if expected_weeks in time_offset_keywords:
                for i, opt_text in enumerate(option_texts):
                    opt_normalized = normalize_option_text(opt_text)
                    for kw in time_offset_keywords[expected_weeks]:
                        if normalize_option_text(kw) in opt_normalized:
                            return (i, 'high', matched_key)
            
            # Fallback: Try to find numeric match in option text
            # Only if expected value appears explicitly (e.g., "2" in "2 weeks")
            for i, opt_text in enumerate(option_texts):
                opt_normalized = normalize_option_text(opt_text)
                # Check if expected number appears with "week" or "month" nearby
                if expected_weeks in opt_normalized and ('week' in opt_normalized or 'month' in opt_normalized):
                    return (i, 'high', matched_key)
            
            # No confident match found - do not guess
            return (None, 'low', 'no_matching_time_offset')
        
        # Handle education_enrollment_status - binary Yes/No only
        elif matched_key == 'education_enrollment_status':
            # Guard: Must have enrollment status configured
            if 'education_enrollment_status' not in ANSWER_BANK:
                return (None, 'low', 'enrollment_status_not_configured')
            
            # Guard: Must be strictly binary (2 real options, ignoring placeholders)
            # Reject if dropdown has more than 3 options (allowing for "Select an option" placeholder)
            if option_count > 3:
                return (None, 'low', 'not_binary_dropdown')
            
            # Guard: Reject if any option mentions date ranges
            # This prevents matching "What semester are you in?" type dropdowns
            date_range_patterns = ['2024', '2025', '2026', 'spring', 'fall', 'summer', 'winter', 
                                 'semester', 'quarter', 'academic year']
            for opt_text in option_texts:
                opt_lower = opt_text.lower()
                if any(pattern in opt_lower for pattern in date_range_patterns):
                    return (None, 'low', 'contains_date_ranges')
            
            # Guard: Reject if any option suggests non-binary choices
            # "Other", "Maybe", "Part-time", etc. indicate this is not a simple Yes/No
            non_binary_patterns = ['other', 'maybe', 'sometimes', 'part time', 'full time', 
                                  'online', 'in person', 'hybrid']
            for opt_text in option_texts:
                opt_lower = opt_text.lower()
                if any(pattern in opt_lower for pattern in non_binary_patterns):
                    return (None, 'low', 'contains_non_binary_options')
            
            # Get the user's enrollment status (True = Yes/currently enrolled, False = No/not enrolled)
            is_enrolled = ANSWER_BANK['education_enrollment_status']
            
            # Match based on Yes/No patterns in option text
            yes_patterns = ['yes', 'currently enrolled', 'i am', 'enrolled', 'pursuing']
            no_patterns = ['no', 'not enrolled', 'i am not', 'not currently', 'not pursuing']
            
            # Filter out placeholder options ("Select", "Choose", etc.)
            placeholder_patterns = ['select', 'choose', 'pick']
            
            for i, opt_text in enumerate(option_texts):
                opt_normalized = normalize_option_text(opt_text)
                
                # Skip placeholder options
                is_placeholder = any(p in opt_normalized for p in placeholder_patterns)
                if is_placeholder:
                    continue
                
                # Check if this is the Yes option
                # Use exact match for simple "yes" or substring match for longer phrases
                is_yes = (opt_normalized == 'yes' or 
                         any(p in opt_normalized for p in yes_patterns if len(p) > 3))
                if is_enrolled and is_yes:
                    return (i, 'high', matched_key)
                
                # Check if this is the No option
                # Use exact match for simple "no" or substring match for longer phrases
                is_no = (opt_normalized == 'no' or 
                        any(p in opt_normalized for p in no_patterns if len(p) > 3))
                if not is_enrolled and is_no:
                    return (i, 'high', matched_key)
            
            # No confident binary match found - do not guess
            return (None, 'low', 'no_binary_yes_no_match')
        
        # Handle summer_2026_internship_availability - May through August 2026 ONLY
        elif matched_key == 'summer_2026_internship_availability':
            # Guard: Must have availability configured (always True for this automation run)
            if 'summer_2026_internship_availability' not in ANSWER_BANK:
                return (None, 'low', 'summer_2026_availability_not_configured')
            
            # Guard: Must be strictly binary (2 real options, ignoring placeholders)
            # Reject if dropdown has more than 3 options (allowing for "Select an option" placeholder)
            if option_count > 3:
                return (None, 'low', 'not_binary_dropdown')
            
            # Guard: Reject if any option suggests free-text or conditional responses
            # "Other", "Maybe", "Depends" indicate this is not a simple Yes/No
            non_binary_patterns = ['other', 'maybe', 'depends', 'not sure', 'conditional']
            for opt_text in option_texts:
                opt_lower = opt_text.lower()
                if any(pattern in opt_lower for pattern in non_binary_patterns):
                    return (None, 'low', 'contains_non_binary_options')
            
            # Policy: User is assumed available for May-August 2026 internships
            # Always select "Yes" - no date parsing or inference logic
            is_available = ANSWER_BANK['summer_2026_internship_availability']  # Always True
            
            # Match "Yes" option
            yes_patterns = ['yes', 'available', 'i am available']
            placeholder_patterns = ['select', 'choose', 'pick']
            
            for i, opt_text in enumerate(option_texts):
                opt_normalized = normalize_option_text(opt_text)
                
                # Skip placeholder options
                is_placeholder = any(p in opt_normalized for p in placeholder_patterns)
                if is_placeholder:
                    continue
                
                # Check if this is the Yes option (exact match for simple "yes" or substring for phrases)
                is_yes = (opt_normalized == 'yes' or 
                         any(p in opt_normalized for p in yes_patterns if len(p) > 3))
                if is_available and is_yes:
                    return (i, 'high', matched_key)
            
            # No confident Yes option found - do not guess
            return (None, 'low', 'no_yes_option_match')
    
    # If matched_key exists but not in ANSWER_BANK, or no match at all
    return (None, 'low', 'unmatched')

