# Contributing

How we write code, use git and work with pull requests, for people and coding agents alike. The details per area live in `.agents/guidelines/`, where the repository has them: read the one for the area you touch. The project's facts (its commands, its tracker, the languages of its pull requests and docs) are in `.agents/project.md`, and where it differs from this file, it wins.

This file comes from the `contributing` pack of your organisation's engineering-assets hub. A repository with rules of its own keeps them: change this file here, and the hub stops updating it.

## How we decide

- **Ask "why" first.** Before adding a class, parameter, flag, metric, test, script or document, answer: what real problem does this solve *now*? Who asked for it? "Might be useful later" is a reason not to add it. A metric or alert answers a question someone will ask of it; one added only for a launch is a stopgap and is marked as one (Code style).
- **Adding is easy, removing is hard.** Everything we ship we commit to support. Add the minimum; extend when a real use case arrives.
- **Start with the simplest explicit version.** Two plain functions beat an interface with one implementation; a loop beats a clever comprehension. Readability wins over micro-optimisation: optimise only with a measurement in hand.
- **Fail loudly.** Unexpected input or state: raise. A silent fallback, a swallowed exception, a default instead of missing data corrupts data in a way nobody notices.
- **Fix the cause, not the symptom.** When a fix needs an algorithm to work around bad data, stop and ask what produced that data.
- **Minimal, focused diffs.** Touch only what the task needs; adjacent improvements and second bugs go to their own pull request. When porting or copying code, change as little as possible.
- **Consistency over local preference.** Do it the way the neighbouring code does it.
- **Verify, don't argue.** Run it, `EXPLAIN` it, try it on a staging environment, read the upstream docs or SDK.

## Code style

- Concise, reusable logic; DRY, but a two-line duplicate is fine when a helper would make the call site less explicit.
- Organise by domain, not by technical category.
- Composition over inheritance (mixins are fine); an abstraction needs at least two real implementations.
- Readability over cleverness; small incremental changes.
- **No comments by default.** A comment stays only where the code cannot say it and the reader would be lost without it: why it is done this way (a library bug, a business rule, another system's quirk) or what breaks if it is changed. A comment that retells the code, the names or the history of the change is noise: delete it.
- A suppression names the rule and the reason: `# noqa: BLE001 - re-raised in the consumer`, `// eslint-disable-next-line no-console -- CLI output`.
- A TODO names its issue: `TODO(<issue>): <what is left>`. A stopgap, code that lives only until a condition is met (a limit goes away, a launch is validated), is marked so: a TODO with its issue and that condition.
- Comments and docstrings are in English, unless the profile says otherwise.

## Once and only once

Every decision, condition or piece of knowledge lives in exactly one place. If the same check appears at several levels, the decision should be encapsulated.

- Make the decision once, and let the rest of the code follow the outcome.
- Hide decisions behind objects or functions: callers should not know the condition exists.
- When a rule changes, you should only need to touch one place.
- The same applies to documentation: one source of truth, referenced everywhere else.

```python
# BAD: the same decision repeated at different levels
if settings.mode == "streaming":
    transport.use_stream()
# ... in another module ...
if settings.mode == "streaming":
    response.set_content_type("text/event-stream")

# GOOD: the decision made once, behaviour follows
handler = create_response_handler(settings.mode)
handler.send(data)        # already knows how to send
handler.content_type      # already correct
```

## Documentation

- Internal docs describe architecture and decisions for developers and agents; public docs are for users and never use internal vocabulary. Their languages, and where operational runbooks live, are in the profile.
- Update docs in the same pull request as the code they describe: a doc that contradicts the code is a bug.
- What does **not** go into the repository: agent-generated plans and summaries, roadmaps that duplicate the pull request description, one-off scripts, files from `local/`, generated artifacts. Context for a change is a few sentences in the pull request description or a page in the team's wiki.
- New tooling and "modern" replacements for working things are discussed first ("what problem does this solve?") and never ride along in a feature pull request.

## Git

### Branches

By the convention in the profile. Without one: `<type>/<issue>-<short-description>`, such as `fix/123-empty-email`, with the types below.

### Commits

By the convention in the profile. Without one, Conventional Commits: `<type>(<scope>): <description>`, with the issue as the scope where the project does that.

- `feat`: new functionality
- `fix`: a bug fix
- `perf`: a performance change (an optimisation is `perf`, not `feat`)
- `refactor`: restructuring without a behaviour change
- `test`: adding or updating tests
- `docs`: documentation
- `chore`: maintenance, dependencies, configuration; never for a change that belongs in release notes

Run the repository's formatter before every commit: the format command in the profile.

### Local files

`local/` holds what stays on one machine: experiments, one-off scripts and their output, specs, AI review records, notes. Its own `.gitignore` keeps everything in it out of git. Work that must not reach the repository goes there, not to the repository root or a folder of its own.

## Pull requests

- One pull request, one scope. Unrelated improvements, adjacent bug fixes, CI and tooling changes go to separate pull requests or the backlog. Keep the diff reviewable: thousands of lines is a split.
- The title follows the profile's format and language and names one main change, since release notes are built from it. The type is honest: `perf` for an optimisation, `feat` or `fix` for anything users see, `chore` only for what they do not.
- The description follows the repository's template and is short. The diff says what changed; the description says why: the problem in a sentence or two and one line per included change. A larger change adds the decisions the diff does not show and what was rejected; a claimed effect on speed, memory or cost adds measurements; a change clients or operators must react to, or a schema change, adds the rollout: what breaks, the migration, the deploy order. API changes include example requests and responses. No retelling of the diff, no linter output, no list of tests run; a check by hand the repository asks for is one line of what was verified.
- No tool attribution in commits and pull requests: no `Co-Authored-By` for an AI agent, no "Generated with" lines. The one who opens the pull request is its author and owns the change.
- Nothing accidental in the diff: no `local/` files, secrets, generated files, debugging leftovers, agent reports, unrelated formatting.
- Reply to every review thread in a sentence or two and leave it open: only its author resolves it, once satisfied that the change is in the branch. Push back with arguments, not labels.
- Where the repository has `.agents/review/`, the author runs the AI review before asking people to review, and the description carries its section: `.agents/review/README.md`.

## For AI assistants

### Communication

- Be concise; avoid over-explaining. Answer in the language the user writes in.
- A question gets an answer, not an edit: "why X?", "what do you think?" or "list the bugs" asks for an opinion or a list. Change code only when asked.
- Back every claim ("fixed", "nothing else calls it", "a test covers it") with code, a run or a source; mark a guess as a guess.
- Ask before git operations, installs or other side effects.

### Workflow

- A task in the code follows the `implement` skill, where the repository has it; otherwise: a TODO list before implementing, interface, then tests, then implementation when defining new behaviour.
- Findings outside the task go to the user as a list (their own pull request now, an issue for later, or leave them) and are never fixed silently in the task's branch.
- Read the guideline for the area you touch before writing code; before committing, check the diff against this file.
- Do not add comments that explain the code to the reviewer (see "No comments by default").
- Docs and code disagree: fix it within the task's scope; outside it, list it with the other findings. Duplicated docs: within the task's scope, move the content to one file and reference it everywhere; outside it, list it. A code pattern that takes repeated analysis to understand: propose a doc in `docs/`.
- Whether to run the tests locally or leave them to the pull request's CI is the developer's choice: ask once and remember the answer. Tests left to CI are read in the pipeline before the task is called done.

### Secrets and scripts

- Never hardcode API keys or secrets in scripts: read them from the environment (`os.getenv("KEY_NAME")` in Python, `process.env.KEY_NAME` in Node).
- Hardcoded placeholder values for keys, tokens or secrets: in the code the task touches, replace them with reads from the environment; elsewhere, tell the user at once.
- Never call production or third-party endpoints from local or test setups: use mocks, or the local services the tests start. Such a URL in tests or local configuration: stop and report.
