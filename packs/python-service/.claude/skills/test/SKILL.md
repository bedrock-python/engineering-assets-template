---
name: test
description: Run the project's tests, all of them or a subset, and explain the failures. Use after changing code, or when the user asks to run tests.
argument-hint: "[path, test name or marker]"
---

Run the tests. $ARGUMENTS

1. Use the "Test" command from `.agents/project.md`, narrowed to what was asked with the runner's own selection (for pytest: a path, `-k <expression>` or `-m <marker>`).
2. If the tests need infrastructure (containers, a test database, a broker) and the profile or the repository names the commands for it, check whether it is running first. It belongs to the machine, shared by every clone and worktree: if it runs and you did not start it, another agent may be testing on it, and two runs on one test database break each other, so ask before you run. If it is not running, ask before starting it; afterwards stop only what you started, unless the user asked to keep it for the next run.
3. For a long suite or many failures, hand the run to the `test-runner` subagent.
4. Report the totals, and whether you started or stopped the infrastructure. For each failure give the test, the error, and the likely cause in the code under test.
5. Do not change a test to make it pass unless the test itself is wrong; when you think it is, say why.
