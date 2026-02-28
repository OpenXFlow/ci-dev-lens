# Testing-Pro — Mocking Patterns

## Basic Rule
Tests must run **without internet, without DB, without API**.
Everything external = mock.

## Mocking API calls

```python
from unittest.mock import MagicMock, patch

# Mock HTTP request
with patch("urllib.request.urlopen") as mock_urlopen:
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"result": "ok"}'
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    result = my_function_that_calls_api()
    assert result == "ok"
```

## Mocking the File System

```python
from unittest.mock import patch, mock_open

# Mock file reading
with patch("builtins.open", mock_open(read_data="file content")):
    result = my_function_that_reads_file()
    assert "content" in result
```

## Mocking pathlib.Path

```python
from unittest.mock import patch, MagicMock

# Mock file existence
with patch.object(Path, "exists", return_value=True):
    result = my_function_that_checks_file()
    assert result is True
```

## Mocking subprocess

```python
from unittest.mock import patch, MagicMock

# Mock subprocess.run
with patch("subprocess.run") as mock_run:
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="test output",
        stderr=""
    )
    result = my_function_that_runs_command()
    assert result["success"] is True
```

## pytest fixtures — patterns

```python
import pytest
from pathlib import Path

@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Temporary project structure."""
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "__init__.py").touch()
    return tmp_path

@pytest.fixture
def mock_env() -> dict:
    """Mock environment variables."""
    return {
        "GOOGLE_API_KEY": "AIzaSy_TEST",
        "GROQ_API_KEY": "gsk_TEST",
        "GITHUB_TOKEN": "github_pat_TEST",
    }
```

## Parameterized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input: str, expected: str) -> None:
    assert input.upper() == expected
```

## Testing Exceptions

```python
import pytest

def test_division_by_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        result = 10 / 0

def test_value_error_message() -> None:
    with pytest.raises(ValueError, match="invalid value"):
        raise ValueError("invalid value")
```