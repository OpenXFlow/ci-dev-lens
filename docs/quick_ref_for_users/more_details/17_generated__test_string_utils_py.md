"""
Tests for the string_utils module.
"""

import pytest
from src.string_utils import is_palindrome

def test_empty_string():
    assert is_palindrome("") == True

def test_single_character():
    assert is_palindrome("a") == True

def test_palindrome_with_mixed_characters():
    assert is_palindrome("A man, a plan, a canal: Panama") == True

def test_non_palindrome():
    assert is_palindrome("hello") == False

def test_palindrome_with_numbers():
    assert is_palindrome("12321") == True

def test_palindrome_with_special_characters():
    assert is_palindrome("Was it a car or a cat I saw?") == True
