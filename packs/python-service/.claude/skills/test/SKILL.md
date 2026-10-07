---
name: test
description: Run the project's tests, all of them or a subset, and explain the failures. Use after changing code, or when the user asks to run tests.
argument-hint: "[path, test name or marker]"
---

Run the tests. $ARGUMENTS

1. Use the "Test" command from `.agents/project.md`, narrowed to what was asked with the runner's own selection (for pytest: a path, `-k <expression>` or `-m <marker>`).
2. For a long suite or many failures, hand the run to the `test-runner` subagent.
3. Report the totals. For each failure give the test, the error, and the likely cause in the code under test.
4. Do not change a test to make it pass unless the test itself is wrong; when you think it is, say why.
