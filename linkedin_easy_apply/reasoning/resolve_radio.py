"""Radio button resolution logic"""

from linkedin_easy_apply.data.answer_bank import ANSWER_BANK
from linkedin_easy_apply.reasoning.normalize import normalize_text


def resolve_radio_question(page, group_name, question_text, option_count):
    """
    Resolve boolean radio question to True/False or None.
    Also handles multi-option self-identification questions (gender, race, veteran, disability).
    
    Returns: (answer: bool|int|None, confidence: str, matched_key: str)
    """
    normalized = normalize_text(question_text)
    
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
    
    # MULTI-OPTION QUESTIONS (3+ options) - Self-identification
    elif option_count >= 3:
        # Gender question (typically 3 options: Male, Female, Decline)
        if any(kw in normalized for kw in ['gender', 'sex']):
            if 'gender' in ANSWER_BANK:
                gender_pref = ANSWER_BANK['gender'].lower()
                # Map answer to option index
                # Typical order: Male (0), Female (1), Decline (2)
                gender_map = {
                    'male': 0,
                    'female': 1,
                    'decline': 2,
                }
                if gender_pref in gender_map:
                    return (gender_map[gender_pref], 'high', 'gender')
        
        # Race/Ethnicity question
        if any(kw in normalized for kw in ['race', 'ethnicity', 'ethnic']):
            if 'race' in ANSWER_BANK:
                race_pref = ANSWER_BANK['race'].lower()
                # Common pattern: last option is "Decline to answer"
                if race_pref == 'decline':
                    # Select last option (typically "Decline to answer")
                    return (option_count - 1, 'high', 'race')
                else:
                    # If specific race selected, would need option matching
                    # For now, default to decline if not explicitly "decline"
                    return (option_count - 1, 'high', 'race')
        
        # Veteran status question
        if any(kw in normalized for kw in ['veteran', 'military', 'armed forces']):
            if 'veteran_status' in ANSWER_BANK:
                veteran_pref = ANSWER_BANK['veteran_status'].lower()
                # Typical order: I am a veteran (0), I am not a veteran (1), Decline (2)
                veteran_map = {
                    'veteran': 0,
                    'not_veteran': 1,
                    'decline': 2,
                }
                if veteran_pref in veteran_map:
                    return (veteran_map[veteran_pref], 'high', 'veteran_status')
        
        # Disability status question
        if any(kw in normalized for kw in ['disability', 'disabled', 'impairment']):
            if 'disability_status' in ANSWER_BANK:
                disability_pref = ANSWER_BANK['disability_status'].lower()
                # Typical order: Yes I have disability (0), No disability (1), Decline (2)
                disability_map = {
                    'yes_disability': 0,
                    'no_disability': 1,
                    'decline': 2,
                }
                if disability_pref in disability_map:
                    return (disability_map[disability_pref], 'high', 'disability_status')
    
    # No confident match
    return (None, 'low', 'unmatched')
