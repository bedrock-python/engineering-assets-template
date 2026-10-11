# Testing guidelines for services

Tests are how we change the service without fear. A test earns its place when it fails for a real bug and passes for a correct refactoring. Where `.agents/project.md` or the existing tests settle a convention differently (layout, naming, fixtures, tools), follow them.

## What to test

- Test behaviour through the service's interfaces: handlers, consumers, public functions of a module. Avoid asserting on private helpers and call order.
- Every bug fix comes with a test that fails without the fix.
- Cover the unhappy paths: invalid input, missing data, timeouts and errors from dependencies, retries, duplicate messages.
- When a value is passed on to another system, capture the outgoing request and check the whole payload, so a field that silently stops reaching it fails a test.
- Keep a few end-to-end tests of the main flows; most tests are faster and closer to the code.
- Do not test the libraries and frameworks themselves, or states the code cannot reach.

## Kinds of tests

- **Unit**: no network, no database, no clock you do not control. Milliseconds each.
- **Integration**: against real dependencies such as the database or a broker, started for the test run (for example in containers). Use them for queries, migrations and serialisation, where mocks would lie.
- **Contract**: for APIs and events other teams rely on, check the schema you publish against what you produce.

## How to write them

- Arrange, act, assert: one behaviour per test, named after what it checks (`test_refund_fails_when_order_is_shipped`).
- No logic in a test: no `if`, loops over cases, `try`, or skipping depending on the environment. A test has one expected outcome; to cover several inputs, parametrise it or write another test.
- Put the setup in fixtures or small factories, so the test body reads as "call, then check". Look for an existing fixture before you write one; avoid large shared fixtures that every test depends on.
- Build expected values by hand. A test that computes them with the code under test proves nothing.
- Assert exact values and whole structures (`assert response == expected`), not fragments (`> 0`, `in`, a substring of the JSON). Compare parsed data, not strings. Floats compare with a tolerance (`pytest.approx`), and fields that differ on every run, such as generated ids and timestamps, with a matcher that pins their type or format.
- Assert error codes and types, not the wording of messages users see; test the wording where the message is built.
- Fake what you own at its boundary, preferably by injecting the fake; for third-party services, use a recorded or local stand-in rather than mocking their client library call by call.
- Control time and randomness: inject a clock, seed generators.
- Tests must pass in any order and in parallel. Each test cleans up after itself or runs in a transaction that is rolled back.

## Flaky tests

A flaky test is a bug. Fix it or quarantine it with a linked issue the same day; never retry it until it passes.
