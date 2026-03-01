"""
This module contains string utility functions.
"""

import re

def is_palindrome(text: str) -> bool:
    """
    Checks if a given string is a palindrome.

    This function removes non-alphanumeric characters from the input string,
    converts it to lowercase, and checks if it's a palindrome.

    Args:
        text (str): The input string.

    Returns:
        bool: True if the string is a palindrome, False otherwise.
    """
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned_text = re.sub(r'\W+', '', text).lower()
    
    # Check if the cleaned text is a palindrome
    return cleaned_text == cleaned_text[::-1]