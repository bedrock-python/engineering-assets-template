# Python guidelines for services

This is a service: callers reach it over the network, so its contract is the API, the events and the data it keeps, not its Python modules. Optimise for code the on-call engineer can read at three in the morning. Where `.agents/project.md` or the surrounding code settles a convention differently (naming, layout, libraries), follow them.

## Code

- Type-annotate public functions and anything that crosses a module boundary, and keep the type checker clean. Prefer precise types to `Any` and to dicts passed around as records: use dataclasses or the project's model library, frozen where the value does not change.
- Give closed sets of values an `Enum`, and identifiers their own type (`NewType`) where mixing them up is a real risk. A tuple whose meaning depends on position becomes a named type.
- Keep functions small and side effects at the edges: parse and validate input at the boundary (HTTP handler, consumer, CLI), work with typed objects inside, and do I/O in thin adapters you can replace in tests.
- Do not change the arguments a function receives; return new values. Builders and accumulators whose job is to be changed are the exception.
- A boolean parameter that switches between two behaviours is usually two functions; let the caller pick one.
- Read configuration once at startup, validate it, and fail fast with a clear message. Reject unknown keys in configuration files, and unknown environment variables with the service's prefix, so a misspelt setting stops the service instead of being ignored. Never read environment variables deep inside the code.
- Every call over the network has a timeout. Retry only idempotent operations, with backoff and a limit.
- Use `async` only where the framework is async, and never block the event loop: no synchronous I/O, sleeps or CPU-heavy work inside a coroutine. Catch `CancelledError` only to clean up and re-raise.
- Name things after what they mean in the domain, not after their type or transport, and put units in names (`timeout_seconds`, `size_bytes`). Use one word for one concept across the code base.
- Give every number with a meaning a named constant and a reason. Leave no dead code: unused functions and parameters, commented-out code, TODOs without an issue.

## Errors

- Raise on input or state you did not expect. End a chain of known cases with an `else` that raises (`typing.assert_never` lets the type checker prove every case is handled), so an unknown value never falls through to a default.
- Data from other systems is the exception where the contract says to tolerate what you do not know, such as unknown fields or new enum values in messages: skip them on purpose, and log or count them, so a producer can deploy before you.
- Raise specific errors where the problem is found. Do not catch `KeyError`, `TypeError` or `AttributeError` far from where they happen as a stand-in for a domain condition: any library can raise them.
- Do not swallow exceptions. Catch what you can handle, add context, and let the rest reach the error handler that logs and reports it. Never use a bare `except:`, and never hide a failure behind a `None` return or a warning nobody reads.
- Wrap the errors of an external system into the service's own errors inside its adapter, and map the service's errors to responses once, at the edge (HTTP handler, consumer).
- Messages that reach users say what they can do about the problem and carry no internals: no exception text, stack traces or names of internal systems. The details go to the log.
- Reuse an existing error code when it means the same thing, rather than adding one: every code is a promise to clients.

## Logging and observability

- Log events, not narration: one line per meaningful event, with structured fields such as identifiers, counts and durations, in the project's logging setup.
- Never log secrets, tokens, personal data or request and response bodies. Mask them at the source.
- Log an error that needs a person once, where it is handled, at error level; expected failures, such as invalid input from a client, go to a lower level. Use `logger.exception` only inside an `except` block.
- Keep metric labels bounded: no user ids, free text or URLs with ids in them.
- Expose the health checks and metrics the platform expects, and keep them cheap.

## Dependencies

- Add a dependency only when it saves real work, is maintained, and has a licence the project accepts. Pin versions through the project's lock file.
- Prefer the standard library and the dependencies you already have; check that they do not already solve the problem before you write a helper.

## Changes that reach users

- Keep API changes backwards compatible. When you must break one, version it and give clients time to move.
- Put risky changes behind a configuration switch so they can be turned off without a deploy, when the project has such switches. Remove the switch and the old path once the change has proven itself.
- Write migrations and rollouts so that the old and the new version can run side by side during a deploy.
