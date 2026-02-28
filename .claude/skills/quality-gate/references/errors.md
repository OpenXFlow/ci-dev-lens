# Quality Gate — Solutions for Common Errors

## Ruff Errors

### E401 — Multiple imports on one line
```python
# ❌ Incorrect
import os, sys

# ✅ Correct
import os
import sys
```
**Fix:** `autofix.sh` will fix this automatically.

### E501 — Line too long
```python
# ❌ Incorrect
very_long_variable_name = some_function(argument_one, argument_two, argument_three, argument_four)

# ✅ Correct
very_long_variable_name = some_function(
    argument_one, argument_two,
    argument_three, argument_four
)
```
**Fix:** `autofix.sh` will fix this automatically.

### F401 — Imported but unused
```python
# ❌ Incorrect
import os  # unused

# ✅ Correct — remove unused import
```
**Fix:** `autofix.sh` will fix this automatically.

### I001 — Import order
```python
# ❌ Incorrect (stdlib before third-party rule not followed)
import requests
import os

# ✅ Correct
import os
import requests
```
**Fix:** `autofix.sh` will fix this automatically.

---

## Mypy Errors (DO NOT FIX — return to Developer)

### Incompatible types
```
error: Argument 1 to "process" has incompatible type "str"; expected "int"
```
**Action:** Return the error to the Developer. This is a logic error, not a cosmetic one.

### Missing return type
```
error: Function is missing a return type annotation
```
**Action:** Return to Developer — they must add a type hint.

### Module not found
```
error: Cannot find implementation or library stub for module named "xyz"
```
**Action:** Check `pyproject.toml` — a dependency might be missing.
If `ignore_missing_imports = true` is set in the mypy configuration, this error will not appear.

---

## When to use `# noqa` (NEVER on your own)
Only a Developer or operator can add `# noqa` after a conscious decision.
The Pedant (Linter) **must not** add `# noqa` without explicit instruction.