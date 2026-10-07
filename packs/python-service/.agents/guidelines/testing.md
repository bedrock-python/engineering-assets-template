# Testing guidelines for services

Tests are how we change the service without fear. A test earns its place when it fails for a real bug and passes for a correct refactoring.

## What to test

- Test behaviour through the service's interfaces: handlers, consumers, public functions of a module. Avoid asserting on private helpers and call order.
- Every bug fix comes with a test that fails without the fix.
- Cover the unhappy paths: invalid input, missing data, timeouts and errors from dependencies, retries, duplicate messages.
- Keep a few end-to-end tests of the main flows; most tests are faster and closer to the code.

## Kinds of tests

- **Unit**: no network, no database, no clock you do not control. Milliseconds each.
- **Integration**: against real dependencies such as the database or a broker, started for the test run (for example in containers). Use them for queries, migrations and serialisation, where mocks would lie.
- **Contract**: for APIs and events other teams rely on, check the schema you publish against what you produce.

## How to write them

- Arrange, act, assert: one behaviour per test, named after what it checks (`test_refund_fails_when_order_is_shipped`).
- Build test data with small factories or fixtures; avoid large shared fixtures that every test depends on.
- Fake what you own at its boundary; for third-party services, use a recorded or local stand-in rather than mocking their client library call by call.
- Control time and randomness: inject a clock, seed generators.
- Tests must pass in any order and in parallel. Each test cleans up after itself or runs in a transaction that is rolled back.

## Flaky tests

A flaky test is a bug. Fix it or quarantine it with a linked issue the same day; never retry it until it passes.
