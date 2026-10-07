---
name: fmt
description: Format and lint the code with the project's tools and fix what the linter reports. Use before committing.
argument-hint: "[paths]"
---

Format and lint $ARGUMENTS. With nothing named, take the files changed on this branch.

1. Use the "Format" and "Lint and type-check" commands from `.agents/project.md`. If it names none, use the tools configured in `pyproject.toml` (for example `ruff format` and `ruff check`) and say which ones you used.
2. Run the formatter, then the linter's safe fixes. Fix the remaining findings by hand where the fix is clear, and list the rest.
3. Do not change the formatter's or linter's configuration, or add suppression comments, to silence a finding unless the user agrees.
