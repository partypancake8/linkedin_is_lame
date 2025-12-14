"""Text normalization utilities"""

import string


def normalize_text(text):
    """Normalize text for keyword matching - lowercase, strip punctuation"""
    if not text:
        return ""
    # Lowercase and remove punctuation
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Collapse whitespace
    return ' '.join(text.split())


def normalize_option_text(text):
    """Normalize dropdown option text for matching - removes filler words"""
    if not text:
        return ""
    # Lowercase
    text = text.lower()
    # Remove punctuation
    text = text.translate(str.maketrans('', '', string.punctuation))
    # Collapse whitespace
    text = ' '.join(text.split())
    # Remove filler words
    filler_words = ['weeks', 'months', 'please select', 'select one', 'choose', 'pick']
    for filler in filler_words:
        text = text.replace(filler, '')
    # Re-collapse whitespace after removals
    return ' '.join(text.split())
