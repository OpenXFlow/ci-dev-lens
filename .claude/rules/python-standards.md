# PYTHON STANDARDS

## 1. TOOLCHAIN
- Use `uv` exclusively for all operations.
- ❌ `pip install`, `python -m venv`
- ✅ `uv add`, `uv run pytest`, `uv run python`

## 2. TYPING & LINTING
- Code must pass `ruff check` (Rules: E, F, I).
- Explicit Type Hints are mandatory for all functions.
- `mypy` runs in `strict=false` mode.
- Focus on logical type errors, not pedantic ones (e.g., `Any` is acceptable in test files).

## 3. FILE STRUCTURE
- Every package/module must contain an `__init__.py` file.
- Individual files must not exceed 200 lines of code. If they do -> Refactor.
- The `tests/` directory must mirror the structure of the `src/` directory.

## 4. DOCUMENTATION STANDARDS (MANDATORY)
- Use **Google Style Docstrings** for ALL functions and methods (including tests).
- Every docstring must include `Args:`, `Returns:`, and `Raises:` sections if applicable.
- Even test functions must have a one-line docstring explaining the scenario.

## 5. TESTING STANDARDS
- Test functions MUST have type hints for any helper variables.
- Use descriptive names and maintain the same typing discipline as in `src/`.