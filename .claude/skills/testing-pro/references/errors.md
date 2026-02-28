# Testing-Pro — Solutions for Common Failures

## ImportError: No module named 'src'

**Cause:** Missing `__init__.py` or Python does not recognize `src/` as a module.

**Solution:**
```bash
# Check for existence
ls src/__init__.py
ls tests/__init__.py

# If missing, create them
touch src/__init__.py
touch tests/__init__.py
```


## fixture 'xxx' not found

**Cause:** The fixture is defined in another file without using `conftest.py`.

**Solution:** Move shared fixtures to `tests/conftest.py`:
```python
# tests/conftest.py
import pytest

@pytest.fixture
def shared_fixture():
    return {"key": "value"}
```


## ModuleNotFoundError during import

**Cause:** The test is running outside of the virtual environment.

**Solution:** Always run tests using `uv run`:
```bash
# ❌ Incorrect
python -m pytest

# ✅ Correct
uv run pytest
```


## pytest-json-report is not installed

**Solution:** Add it to `pyproject.toml`:
```toml
[tool.uv]
dev-dependencies = [
    "pytest",
    "pytest-json-report",
    "pytest-cov",
    "ruff",
    "mypy"
]
```
Then run: `uv sync`


## Coverage is 0% even though tests passed

**Cause:** The `--cov` parameter is pointing to the wrong module.

**Solution:**
```bash
# Correct — point to src/ instead of tests/
uv run pytest --cov=src/ tests/
```


## Test hangs (timeout)

**Cause:** The test is waiting for a network call or an external process.

**Solution:** Add a mock for external calls (see `patterns.md`).
The pipeline limit is **120 seconds**.


## AssertionError without a message

**Cause:** An `assert` statement without a descriptive message.

**Best Practice:**
```python
# ❌ Without message
assert result == expected

# ✅ With message
assert result == expected, f"Expected {expected}, but got {result}"
