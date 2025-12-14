"""Radio button resolution logic"""

from linkedin_easy_apply.data.answer_bank import ANSWER_BANK
from linkedin_easy_apply.reasoning.normalize import normalize_text


def resolve_radio_question(page, group_name, question_text, option_count, option_labels=None):
    """
    Resolve radio question to answer index or bool, or None.
    Supports:
    - Binary yes/no questions (True/False)
    - Multi-option self-identification (gender, race, veteran, disability)
    - Tier-1: Citizenship/employment eligibility questions
    - Tier-2: Employer-specific work authorization questions
    - Tier-1 EEO: Always decline EEO/self-identification fields
    
    Returns: (answer: bool|int|None, confidence: str, matched_key: str)
    """
    normalized = normalize_text(question_text)
    option_labels = option_labels or []
    
    # TIER-1 EEO HANDLING: Always select "Decline to answer" for EEO fields
    # This runs FIRST to ensure safe, deterministic handling of voluntary disclosure fields
    # EEO fields are identified by keywords in the question text OR by option patterns
    eeo_keywords = ['gender', 'sex', 'race', 'ethnicity', 'ethnic', 'veteran', 'military', 
                    'disability', 'disabled', 'impairment', 'voluntary self identification',
                    'equal opportunity', 'affirmative action']
    
    is_eeo_field = any(kw in normalized for kw in eeo_keywords)
    
    # Also detect EEO by option patterns (e.g., Male/Female indicates gender)
    if not is_eeo_field and option_labels:
        # Check if options match common EEO patterns
        options_normalized = [normalize_text(opt) for opt in option_labels]
        options_str = ' '.join(options_normalized)
        
        # Gender: Male + Female present
        if 'male' in options_str and 'female' in options_str:
            is_eeo_field = True
        # Race: common race options
        elif any(race in options_str for race in ['white', 'black', 'asian', 'hispanic', 'african american']):
            is_eeo_field = True
        # Veteran: protected veteran language
        elif 'protected veteran' in options_str or ('veteran' in options_str and 'not a veteran' in options_str):
            is_eeo_field = True
        # Disability: disability language
        elif 'disability' in options_str:
            is_eeo_field = True
    
    if is_eeo_field and option_labels:
        # Search for decline option (case-insensitive, substring match)
        decline_patterns = ['decline', 'prefer not', 'do not wish', 'don\'t wish', 'dont wish']
        
        for i, opt_label in enumerate(option_labels):
            opt_normalized = normalize_text(opt_label)
            for pattern in decline_patterns:
                if normalize_text(pattern) in opt_normalized:
                    # Found decline option - select it deterministically
                    return (i, 'high', 'eeo_decline_selected')
        
        # No decline option found - this is unusual for EEO fields
        # Fall through to existing logic which may match specific answers or pause
    
    # BINARY QUESTIONS (2 options only) - Boolean True/False
    if option_count == 2:
        # Keyword mappings for boolean questions
        # Format: (keywords_tuple): answer_bank_key
        # Patterns are ordered from most specific to least specific
        # Each pattern should uniquely identify the question type to avoid false matches
        boolean_mappings = [
            # Work authorization - require both keywords to avoid matching unrelated "work" questions
            (('authorized', 'work'), 'authorized_to_work'),
            (('legally', 'authorized'), 'authorized_to_work'),
            (('legal', 'right', 'work'), 'authorized_to_work'),
            (('work', 'authorization'), 'authorized_to_work'),
            
            # Sponsorship - "require" + "sponsorship" is highly specific
            # "now or future" pattern catches common phrasing variations
            (('require', 'sponsorship'), 'requires_sponsorship'),
            (('need', 'sponsorship'), 'requires_sponsorship'),
            (('visa', 'sponsorship'), 'requires_sponsorship'),
            (('sponsorship', 'now', 'future'), 'requires_sponsorship'),
            
            # Relocation - "willing" is key discriminator
            (('willing', 'relocate'), 'willing_to_relocate'),
            (('open', 'relocation'), 'willing_to_relocate'),
            (('willing', 'move'), 'willing_to_relocate'),
            
            # Background check - both words required to avoid false match
            (('background', 'check'), 'background_check_consent'),
            (('criminal', 'background'), 'background_check_consent'),
            (('background', 'screening'), 'background_check_consent'),
            
            # Drug test - both words required
            (('drug', 'test'), 'drug_test_consent'),
            (('drug', 'screen'), 'drug_test_consent'),
            
            # Age / legal eligibility - specific age or explicit "legal age"
            (('over', '18'), 'over_18'),
            (('18', 'years'), 'over_18'),
            (('legal', 'age'), 'over_18'),
            (('legally', 'eligible', 'work'), 'legally_eligible'),
        ]
        
        # Try to match keywords - first match wins (most specific first)
        matched_key = None
        for keywords, bank_key in boolean_mappings:
            if all(kw in normalized for kw in keywords):
                matched_key = bank_key
                break
        
        if matched_key and matched_key in ANSWER_BANK:
            answer = ANSWER_BANK[matched_key]
            if isinstance(answer, bool):
                return (answer, 'high', matched_key)
    
    # TIER-1 & TIER-2: Citizenship / Work Authorization Questions (3+ options)
    # These run BEFORE generic multi-option to ensure proper classification
    if option_count >= 3:
        # TIER-1: work_authorization_us - Citizenship / Employment Eligibility
        # Eligible ONLY if: mentions citizenship/employment eligibility, has standard options
        # Anti-patterns: sponsorship timing, visa questions
        citizenship_keywords = ['citizenship', 'employment eligibility', 'legally authorized', 'work authorization']
        sponsorship_keywords = ['sponsorship', 'visa', 'h1b', 'when', 'timeline']
        
        has_citizenship = any(kw in normalized for kw in citizenship_keywords)
        has_sponsorship = any(kw in normalized for kw in sponsorship_keywords)
        
        if has_citizenship and not has_sponsorship:
            if 'work_authorization_us' in ANSWER_BANK:
                target_status = ANSWER_BANK['work_authorization_us'].lower()
                
                # Map answer bank values to option text patterns
                status_patterns = {
                    'us_citizen': ['u.s. citizen', 'us citizen', 'united states citizen', 'citizen of the united states'],
                    'permanent_resident': ['permanent resident', 'green card', 'lawful permanent resident'],
                    'us_citizen_or_permanent_resident': ['u.s. citizen or permanent resident', 'us citizen/permanent resident', 'citizen/permanent resident'],
                    'work_visa': ['work visa', 'h1b', 'employment visa', 'temporary work authorization'],
                    'not_authorized': ['not authorized', 'not legally authorized', 'no work authorization'],
                }
                
                if target_status in status_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in status_patterns[target_status]:
                            if normalize_text(pattern) in opt_normalized:
                                return (i, 'high', 'work_authorization_us')
                    
                    # No confident match - pause
                    return (None, 'low', 'work_auth_us_no_option_match')
        
        # TIER-2: work_authorization_employer_specific - Employer-Specific Authorization
        # Eligible ONLY if: explicitly distinguishes "any employer" vs "current employer"
        # Anti-patterns: free-text, "Other", conditional follow-ups
        employer_keywords = ['any employer', 'current employer', 'employer']
        other_keywords = ['other', 'specify', 'explain']
        
        has_employer = any(kw in normalized for kw in employer_keywords)
        has_other = any(kw in normalized for kw in other_keywords)
        
        if has_employer and not has_other:
            if 'work_authorization_employer_specific' in ANSWER_BANK:
                target_scope = ANSWER_BANK['work_authorization_employer_specific'].lower()
                
                # Map answer bank values to option text patterns
                scope_patterns = {
                    'any_employer': ['any employer', 'work for any employer', 'allowed to work for any employer'],
                    'current_employer_only': ['current employer', 'current employer only', 'only current employer'],
                    'seeking_authorization': ['seeking', 'will require', 'need authorization', 'not yet authorized'],
                }
                
                if target_scope in scope_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in scope_patterns[target_scope]:
                            if normalize_text(pattern) in opt_normalized:
                                return (i, 'high', 'work_authorization_employer_specific')
                    
                    # No confident match - pause
                    return (None, 'low', 'work_auth_employer_no_option_match')
    
    # MULTI-OPTION QUESTIONS (3+ options) - Self-identification
    # These run AFTER Tier-1/Tier-2 citizenship questions
    if option_count >= 3:
        # Gender question (typically 3 options: Male, Female, Decline)
        if any(kw in normalized for kw in ['gender', 'sex']):
            if 'gender' in ANSWER_BANK:
                gender_pref = ANSWER_BANK['gender'].lower()
                
                # Map answer bank values to option text patterns
                gender_patterns = {
                    'male': ['male'],
                    'female': ['female'],
                    'decline': ['decline', 'prefer not to answer', 'i don\'t wish to answer', 'decline to answer'],
                }
                
                if gender_pref in gender_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in gender_patterns[gender_pref]:
                            if normalize_text(pattern) == opt_normalized:
                                return (i, 'high', 'gender')
                    
                    # No confident match - pause
                    return (None, 'low', 'gender_no_option_match')
        
        # Race/Ethnicity question
        if any(kw in normalized for kw in ['race', 'ethnicity', 'ethnic']):
            if 'race' in ANSWER_BANK:
                race_pref = ANSWER_BANK['race'].lower()
                
                # Map answer bank values to option text patterns
                race_patterns = {
                    'white': ['white', 'caucasian'],
                    'black': ['black', 'african american', 'african-american'],
                    'hispanic': ['hispanic', 'latino', 'latina', 'latinx'],
                    'asian': ['asian'],
                    'native_american': ['native american', 'american indian', 'alaska native'],
                    'pacific_islander': ['pacific islander', 'native hawaiian'],
                    'two_or_more': ['two or more', 'two or more races', 'multiracial'],
                    'decline': ['decline', 'prefer not to answer', 'i don\'t wish to answer', 'decline to answer'],
                }
                
                if race_pref in race_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in race_patterns[race_pref]:
                            if normalize_text(pattern) in opt_normalized:
                                return (i, 'high', 'race')
                    
                    # No confident match - pause
                    return (None, 'low', 'race_no_option_match')
        
        # Veteran status question
        if any(kw in normalized for kw in ['veteran', 'military', 'armed forces']):
            if 'veteran_status' in ANSWER_BANK:
                veteran_pref = ANSWER_BANK['veteran_status'].lower()
                
                # Map answer bank values to option text patterns
                veteran_patterns = {
                    'veteran': ['i identify as one or more', 'i am a veteran', 'yes, i am a veteran', 'protected veteran'],
                    'not_veteran': ['i am not a protected veteran', 'i am not a veteran', 'no, i am not a veteran', 'not a protected veteran'],
                    'decline': ['decline', 'prefer not to answer', 'i don\'t wish to answer', 'i do not wish to answer', 'decline to self identify'],
                }
                
                if veteran_pref in veteran_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in veteran_patterns[veteran_pref]:
                            if normalize_text(pattern) in opt_normalized:
                                return (i, 'high', 'veteran_status')
                    
                    # No confident match - pause
                    return (None, 'low', 'veteran_status_no_option_match')
        
        # Disability status question
        if any(kw in normalized for kw in ['disability', 'disabled', 'impairment']):
            if 'disability_status' in ANSWER_BANK:
                disability_pref = ANSWER_BANK['disability_status'].lower()
                
                # Map answer bank values to option text patterns
                disability_patterns = {
                    'yes_disability': ['yes, i have a disability', 'yes i have', 'i have a disability'],
                    'no_disability': ['no, i don\'t have a disability', 'no i do not', 'i do not have a disability', 'no disability'],
                    'decline': ['decline', 'prefer not to answer', 'i don\'t wish to answer', 'decline to self identify'],
                }
                
                if disability_pref in disability_patterns:
                    # Try to match option by text pattern
                    for i, opt_label in enumerate(option_labels):
                        opt_normalized = normalize_text(opt_label)
                        for pattern in disability_patterns[disability_pref]:
                            if normalize_text(pattern) in opt_normalized:
                                return (i, 'high', 'disability_status')
                    
                    # No confident match - pause
                    return (None, 'low', 'disability_status_no_option_match')
    
    # No confident match
    return (None, 'low', 'unmatched')
