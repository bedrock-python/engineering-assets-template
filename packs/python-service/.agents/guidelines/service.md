# Service guidelines

How a service's code is layered, how its configuration is built and how risky changes ship. Python details are in `python.md`, tests in `testing.md`, the database in `database.md`. Where `.agents/project.md`, the repository's architecture doc or the surrounding code settle a convention differently, follow them.

## A service, not a library

We ship a service: its contract is the API, the events and the data it keeps. No abstractions "for reuse", no compatibility shims for internal renames, no settings nobody will tune. Internal code can be renamed freely; what clients see cannot.

## Layers

- Dependencies point one way: shared utilities, then the domain, then integrations with other systems, then delivery (HTTP, consumers, CLI). The domain never imports an integration; the delivery layer never names a concrete external system. The repository's architecture doc names its layers.
- No import inside a function to break a cycle: a cycle means a module sits on the wrong level.
- Code shared by integrations lives in a shared module, not copied between them; what is specific to one integration lives in its package.
- An operation of the domain has one entry point. New behaviour is a new operation, or a composition of operations at the endpoint, never a boolean parameter on an existing one.
- Constants live next to the code that uses them. Interfaces and implementations are separate files; helpers shared by several modules go to a module of their own (a `utils` module is fine while it stays small), and a module's private helpers stay in it, below the code that uses them.
- Wiring: clients that hold connections are created once for the process, everything else per use. Configuration is passed in, never read from a module-level global. What has a lifecycle (pools, background tasks) is opened and closed by whoever created it, as a context manager.

## Feature flags

Where the project has a way to switch behaviour without a deploy:

- **A flag is for a risky change**, one we want to turn off in production without a redeploy: it changes the core of the domain or the path every request takes (what is written to the database, what is charged or limited, what goes to clients and other services), and a failure there is costly. It ships with the old behaviour as the default.
- Every other change ships without a flag: a new endpoint or field, an admin screen, a fix, a refactoring. Its rollback is a revert and a redeploy; a flag would only add a second code path to keep and test.
- The pull request says why a change to the core of the domain needs no flag; when it is unclear whether a change is risky, ask.
- A flag is temporary: once the change has proven itself in production, the flag and the old path are deleted in a follow-up pull request. A flag left in place long after its change proved itself is a defect.
- A flag switches one behaviour. It is no place for tunables: timeouts, batch sizes and retry counts are constants, and a setting exists only because someone will set it differently per environment.

## Configuration

- A configuration describes; the object built from it behaves. A choice of implementation is resolved once, in a factory, into the object: variants with fields of their own are a tagged union (a discriminated union in pydantic), and the factory's `match` ends with `case _: assert_never(config)`.
- Settings models hold and validate values: no validator or post-init hook that builds objects or does I/O. Values derived from the fields are fine.
- Settings are read and checked once at startup (`python.md`, "Code"). Secrets have a type that keeps them out of logs and reprs (`SecretStr` in pydantic). An optional integration is `None` by default, so the service starts locally without it.

## Tests

Behaviour is verified through the service's interfaces with the external systems faked; unit tests cover pure logic with many cases. The rules are in `testing.md`.
