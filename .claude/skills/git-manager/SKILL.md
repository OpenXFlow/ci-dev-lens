# Git-Manager Skill
## Purpose
Manages the branch lifecycle, code pushing (push), and communication with GitHub Actions.

## Scripts (scripts/)
1. `push.sh`: Creates a local branch and pushes it to origin.
2. `pr_create.sh`: Creates a Pull Request using the `gh` CLI.
3. `gha_status.sh`: Checks the status of the last cloud run.

## Rules
- Always use branches named according to `references/branch-naming.md`.
- Never push directly to `main`.
- Before creating a PR, ensure that local tests are green (passing).