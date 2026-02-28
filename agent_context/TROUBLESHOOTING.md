# Agent-CI-Lens Knowledge Base

This file contains known solutions for common problems. 

### @W292
Ruff error W292 (no newline at end of file): The agent must add a single empty newline character at the very end of the file.

### @ImportError: No module named
You forgot to create an `__init__.py` file in the respective directory. If you are writing tests, ensure that `tests/__init__.py` exists.

### @fixture 'tmp_project' not found
This fixture is located in `agent_tests/conftest.py`. Remember that application tests belong in the `tests/` directory, while framework kernel tests belong in `agent_tests/`.


### @Missing return statement
Mypy logic error: When creating class or function skeletons with type hints like `-> float`, you cannot use just `pass`. You MUST return a dummy value (e.g., `return 0.0` or `return ""`) to satisfy Mypy until the real logic is implemented.

### @F821
Ruff error F821 (undefined name): You are trying to use a variable, function, or class that has not been defined or imported. Check your imports at the top of the file.

