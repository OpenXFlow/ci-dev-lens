"""
This module provides a utility function to check if a given string is a palindrome.
"""

def is_palindrome(text: str) -> bool:
    """
    Checks if a given string is a palindrome, ignoring case and non-alphanumeric characters.

    Args:
        text (str): The input string to check.

    Returns:
        bool: True if the string is a palindrome, False otherwise.
    """
    # Remove non-alphanumeric characters and convert to lowercase
    cleaned_text = ''.join(char.lower() for char in text if char.isalnum())
    
    # Compare the cleaned text with its reverse
    return cleaned_text == cleaned_text[::-1]
