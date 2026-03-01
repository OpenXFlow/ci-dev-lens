"""
This module contains tests for the string utility functions.
"""

import pytest
from src.string_utils import is_palindrome

def test_is_palindrome_simple():
    """Test standard palindrome word."""
    assert is_palindrome("madam") is True

def test_is_palindrome_case_insensitive():
    """Test palindrome with mixed case."""
    assert is_palindrome("Madam") is True

def test_is_palindrome_non_alphanumeric():
    """Test palindrome with spaces and punctuation."""
    assert is_palindrome("A man, a plan, a canal: Panama") is True

def test_is_palindrome_not_palindrome():
    """Test standard non-palindrome word."""
    assert is_palindrome("hello") is False

def test_is_palindrome_edge_cases():
    """Test empty string and single character."""
    assert is_palindrome("") is True
    assert is_palindrome("a") is True
    assert is_palindrome("ab") is False