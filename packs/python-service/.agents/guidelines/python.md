# Python guidelines for services

This is a service: callers reach it over the network, so its contract is the API, the events and the data it keeps, not its Python modules. Optimise for code the on-call engineer can read at three in the morning. Where `.agents/project.md` or the surrounding code settles a convention differently (naming, layout, libraries), follow them.

## Code

- Type-annotate public functions and anything that crosses a module boundary, and keep the type checker clean. Prefer precise types to `Any` and to dicts passed around as records: use dataclasses or the project's model library, frozen where the value does not change.
- Give closed sets of values an `Enum`, and identifiers their own type (`NewType`) where mixing them up is a real risk. A tuple whose meaning depends on position becomes a named type.
- Keep functions small and side effects at the edges: parse and validate input at the boundary (HTTP handler, consumer, CLI), work with typed objects inside, and do I/O in thin adapters you can replace in tests.
- Arrange a module like a newspaper: the public, high-level functions at the top, the private helpers below, so the reader sees what the module is for without scrolling. A function body reads as a list of high-level steps; walking dicts, grouping and formatting go to helpers.
- `__init__` only assigns its arguments, and the object is complete after it. Complex assembly goes to a factory function or a classmethod.
- A function or a constructor takes only the values it uses. A dependency an object holds only to hand it to another object is given to that other object instead.
- Data the service interprets (a request, a configuration, a stored row, another system's response) is validated once, at the edge, and trusted inside. What the service passes on without interpreting stays as it was received.
- `X | None = None` only where `None` is a real state with defined behaviour, not "just in case". Two scenarios are two explicit code paths, not one path full of `if x is None`.
- Do not guess what a value is from its keys or shape: the caller says which case it is, or a validated union says it by its variant. A union in another system's contract without a tag is told apart once, where it is converted.
- What opens a resource closes it. Code that receives a client, a session or a unit of work never closes it; a function that opens a resource for its caller returns something the caller closes with `with` or `async with`.
- Use an explicit `if` rather than `try`/`except` for control flow. Do not use `getattr`, `setattr` or `hasattr` on the project's own objects.
- Do not change the arguments a function receives; return new values. Builders and accumulators whose job is to be changed are the exception.
- A boolean parameter that switches between two behaviours is usually two functions; let the caller pick one.
- Read configuration once at startup, validate it, and fail fast with a clear message. Reject unknown keys in configuration files, and unknown environment variables with the service's prefix, so a misspelt setting stops the service instead of being ignored. Never read environment variables deep inside the code.
- Every call over the network has a timeout. Retry only idempotent operations, with backoff and a limit.
- Use `async` only where the framework is async, and never block the event loop: no synchronous I/O, sleeps or CPU-heavy work inside a coroutine. Catch `CancelledError` only to clean up and re-raise.
- Give every number with a meaning a named constant and a reason. Leave no dead code: unused functions and parameters, commented-out code, TODOs without an issue.

## Naming

- Name things after what they mean in the domain, not after their type or transport: `ORDER_CHECKOUT_DURATION`, not `HTTP_POST_DURATION`. Put units in names (`timeout_seconds`, `size_bytes`).
- A name is exactly as broad as what it covers: `retry_on_timeout`, not `retry`, for code that retries only timeouts.
- No prefix the module already implies, no two names of the same words in another order (`OrderItem` and `ItemOrder`), no adjective without its noun (`prepared` what?). Two names that read alike (`LogsConfig` and `LoggingConfig`) are a defect.
- One word for one concept across the code base. Name configuration classes by their role, not by the technology behind them.
- A helper used from outside its module is public: a leading underscore is not a namespace.

## Comments and docstrings

- No comments by default. A comment says only what the code cannot: why it is done this way (a library bug, a business rule, another system's quirk) or what breaks if it changes. A comment that retells the code, or describes behaviour that has since changed, is a defect.
- No docstrings by default: only on public functions and classes others call, protocols, and classes whose responsibility the name does not make obvious. None on `__init__` and none at the top of every module.
- A docstring says what the thing is for and any contract that is not obvious (what the keys of a dict mean, the SQL a builder produces). It does not narrate the implementation.

## Errors

- Raise on input or state you did not expect. End a chain of known cases with an `else` that raises (`typing.assert_never` lets the type checker prove every case is handled), so an unknown value never falls through to a default.
- Data from other systems is the exception where the contract says to tolerate what you do not know, such as unknown fields or new enum values in messages: skip them on purpose, and log or count them, so a producer can deploy before you.
- An exception that reports a failure has a message: a full sentence for whoever reads the log, naming the offending value (`f"Unknown currency ({currency}). Add it to SUPPORTED_CURRENCIES first."`), and how to fix it when the caller can. A secret, personal data or a payload is named by its id, type or length instead. An exception whose class says it all needs no message.
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
- Where the project has feature flags, put a risky change behind one, and only a risky change; `service.md` says which changes are risky and how long a flag lives.
- Write migrations and rollouts so that the old and the new version can run side by side during a deploy.
