"""Static answer bank - known facts only, no job-specific data"""

# Static answer bank - known facts only, no job-specific data
ANSWER_BANK = {
    # Numeric answers
    'years_experience': '1',
    'years_of_experience': '1',
    'total_experience': '1',
    'work_experience': '1',
    'notice_period': '2',
    'notice_period_weeks': '2',
    'gpa': '3.5',
    
    # Text answers
    'linkedin_url': 'https://linkedin.com/in/yourprofile',
    'portfolio_url': 'https://yourportfolio.com',
    'github_url': 'https://github.com/yourusername',
    'website': 'https://yourwebsite.com',
    
    # Tier-1 text fields (always safe - explicit, unambiguous)
    'applicant_full_name': 'Sawyer Smith',
    'current_date_mm_dd_yyyy': None,  # Dynamically generated
    'applicant_city_location': 'Birmingham',
    
    # Tier-2 text fields (usually safe - contact information)
    'applicant_email': 'sawyer.i.smith@gmail.com',
    'applicant_phone_number': '248-550-8616',
    'applicant_college_university': 'University of Michigan College of Engineering',
    
    # Short text responses (safe, generic)
    'skills_summary': 'Strong background in software development with focus on automation and testing.',
    'why_interested': 'Interested in contributing to innovative projects and growing technical skills.',
    
    # Boolean answers for radio buttons (True = Yes, False = No)
    'authorized_to_work': True,
    'requires_sponsorship': False,
    'willing_to_relocate': False,
    'background_check_consent': True,
    'drug_test_consent': True,
    'over_18': True,
    'legally_eligible': True,
    'education_enrollment_status': False,  # Currently enrolled in degree program
    'summer_2026_internship_availability': True,  # Available May-August 2026 (assumed true)
    'reasonable_accommodation_essential_functions': True,  # Can perform essential functions with/without accommodation
    'drivers_license_proof': True,  # Can provide proof of valid driver's license if required
    
    # Tier-1 radio fields (citizenship / employment eligibility)
    # Options: 'us_citizen', 'permanent_resident', 'us_citizen_or_permanent_resident', 'work_visa', 'not_authorized'
    'work_authorization_us': 'us_citizen_or_permanent_resident',
    
    # Tier-2 radio fields (employer-specific work authorization)
    # Options: 'any_employer', 'current_employer_only', 'seeking_authorization'
    'work_authorization_employer_specific': 'any_employer',
    
    # Self-identification answers (voluntary disclosure)
    # Gender: 'male', 'female', 'decline'
    'gender': 'male',
    
    # Race/Ethnicity: Options vary, common ones include:
    # 'white', 'black', 'hispanic', 'asian', 'native_american', 'pacific_islander', 'two_or_more', 'decline'
    'race': 'white',
    
    # Veteran status: 'veteran', 'not_veteran', 'decline'
    'veteran_status': 'not_veteran',
    
    # Disability status: 'yes_disability', 'no_disability', 'decline'
    'disability_status': 'no_disability',
    
    # Language proficiency levels
    # Options: 'native', 'fluent', 'advanced', 'intermediate', 'beginner'
    # Used for questions like "Select your English level" or "Language proficiency"
    'language_proficiency': 'native',  # For English or primary language
    
    # Job referral source (how did you hear about us)
    # Options: 'linkedin', 'indeed', 'monster', 'ziprecruiter', 'glassdoor', 
    #          'company_website', 'referral', 'recruiter', 'job_board', 'other'
    'referral_source': 'linkedin',
    
    # Education level completed (highest degree achieved)
    # Options: 'high_school', 'ged', 'some_college', 'associate', 'bachelor', 
    #          'master', 'doctorate', 'vocational'
    'education_level': 'some_college',
}

# ========================================
# TIER-2 USER ASSERTIONS
# ========================================
# Safety-critical: These expand automation coverage by allowing the bot
# to repeat explicit user-asserted global truths.
#
# NON-NEGOTIABLE RULES:
# - If config key is missing → SKIP field
# - No fallback values allowed
# - No inference from other fields
# - Must be logged as Tier-2 user-asserted
#
# These fields resolve ONLY if explicitly defined below.
# Remove any key to make the bot skip that field type.

USER_ASSERTIONS = {
    # Education
    "education_completed_bachelors": True,  # bool - Completed bachelor's degree
    
    # Work & location preferences
    "assume_commute_ok": True,              # bool - Comfortable commuting to office
    "assume_onsite_ok": True,               # bool - Comfortable working onsite
    
    # Legal / employment (note: this is different from 'requires_sponsorship' in ANSWER_BANK)
    # This specifically answers "Do you require sponsorship?" questions
    # while ANSWER_BANK['requires_sponsorship'] answers "Will you require sponsorship?"
    "requires_sponsorship": False,          # bool - Requires work visa sponsorship
}
