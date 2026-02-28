# Security-Guard — Dangerous Patterns

## SECRETS (exit code 2 → HALT)

| Pattern | Example | Label |
|------|---------|-------|
| `AIza[35 characters]` | `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` | Google API Key |
| `gsk_[32+ characters]` | `gsk_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` | Groq API Key |
| `github_pat_[36+ characters]` | `github_pat_XXXX...` | GitHub PAT |
| `sk-[32+ characters]` | `sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` | OpenAI Key |
| `password = "..."` | `password = "mypassword123"` | Hardcoded password |
| `-----BEGIN PRIVATE KEY-----` | full block | Private key |

## WARNINGS (log, do not block)

| Pattern | Example | Risk |
|------|---------|--------|
| `eval(...)` | `eval(user_input)` | Code injection |
| `exec(...)` | `exec(dynamic_code)` | Code injection |
| `pickle.load(...)` | `pickle.loads(data)` | Arbitrary code exec |
| `shell=True` | `subprocess.run(cmd, shell=True)` | Shell injection |

## EXCLUSIONS (false positives)

- Lines with `_CHANGE_ME` → placeholder, not a real secret
- Lines with `example` or `test` in a comment
- `.env.example` file → template, not a secret
- `tests/` directory for `password` patterns → test data