# Python guidelines for services

This is a service: callers reach it over the network, so its contract is the API, the events and the data it keeps, not its Python modules. Optimise for code the on-call engineer can read at three in the morning.

## Code

- Type-annotate public functions and anything that crosses a module boundary, and keep the type checker clean. Prefer precise types to `Any` and to dicts passed around as records: use dataclasses or the project's model library.
- Keep functions small and side effects at the edges: parse and validate input at the boundary (HTTP handler, consumer, CLI), work with typed objects inside, and do I/O in thin adapters you can replace in tests.
- Read configuration once at startup, validate it, and fail fast with a clear message. Never read environment variables deep inside the code.
- Do not swallow exceptions. Catch what you can handle, add context, and let the rest reach the error handler that logs and reports it. Never use a bare `except:`.
- Every call over the network has a timeout. Retry only idempotent operations, with backoff and a limit.
- Use `async` only where the framework is async, and never block the event loop: no synchronous I/O, sleeps or CPU-heavy work inside a coroutine.
- Name things after what they mean in the domain, not after their type.

## Logging and observability

- Log events, not narration: one line per meaningful event, with structured fields such as identifiers and durations, in the project's logging setup.
- Never log secrets, tokens or personal data. Mask them at the source.
- Errors that need a person get logged at error level once, where they are handled.
- Expose the health checks and metrics the platform expects, and keep them cheap.

## Dependencies

- Add a dependency only when it saves real work, is maintained, and has a licence the project accepts. Pin versions through the project's lock file.
- Keep the dependency tree small: prefer the standard library for small tasks.

## Changes that reach users

- Keep API changes backwards compatible. When you must break one, version it and give clients time to move.
- Put risky changes behind a configuration switch so they can be turned off without a deploy, when the project has such switches.
- Write migrations and rollouts so that the old and the new version can run side by side during a deploy.
