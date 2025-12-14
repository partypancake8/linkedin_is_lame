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
    
    # Self-identification answers (voluntary disclosure)
    # Gender: 'male', 'female', 'decline'
    'gender': 'male',
    
    # Race/Ethnicity: Options vary, common ones include:
    # 'white', 'black', 'hispanic', 'asian', 'native_american', 'pacific_islander', 'two_or_more', 'decline'
    'race': 'black',
    
    # Veteran status: 'veteran', 'not_veteran', 'decline'
    'veteran_status': 'not_veteran',
    
    # Disability status: 'yes_disability', 'no_disability', 'decline'
    'disability_status': 'no_disability',
}
