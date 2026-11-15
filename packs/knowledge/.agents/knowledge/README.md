# Repository knowledge

What agents learned while working here and would otherwise have to ask again: which services and
other teams are responsible for what and whom to go to when something breaks, which resources to go to
and why, how to reach the environments and act there, the team's conventions, the decisions taken, the
work in progress, the traps that fail silently. It is not documentation: docs and guides say how the
code works and how to work on it; knowledge is what saves the user from answering the same
questions. Any agent session - Claude Code, OpenCode, Cursor, Codex - reads it, verifies what it relies
on and records what it was told, so that the next session starts from it and nothing leaves with a
person or a chat.

This file, [`TEMPLATE.md`](TEMPLATE.md), [`index.py`](index.py) and `.gitignore` come from the
engineering-assets hub. The entries and the `INDEX.md` files are this repository's own: the hub never
touches them. `local.md` is one person's own and is never committed (see [Personal](#personal)).

## What goes where

| Knowledge | Place |
| --- | --- |
| true because of the code, changes with it | the repository's docs and its own instructions for agents, in the pull request that changes the code |
| what an agent has to be told (below) | an entry here |
| rules for every repository | `AGENTS.md`, `CONTRIBUTING.md` and `.agents/guidelines/` from the hub |
| what is true only on one person's machine, their own preferences | `local.md` |

An entry links to the docs instead of retelling them. A fact several repositories need is recorded in
each of them with its own specifics.

## What is worth an entry

The test: would an agent find it on its own - in the code, the docs, `--help`, an error message - or fix
it on its own when a first attempt fails? Then it is no entry. An entry is what it would get wrong, or
not know to look for, without being told:

- what a service, a resource or an environment is for, and where it is: which cluster and namespace,
  which paths in the secret store, which database and how to connect to it, which internal API answers what;
- which team owns a neighbouring system and where to reach it when that system breaks;
- how the team does things here: where one-off scripts go (a gitignored folder), what is done by hand
  and by whom, what needs the user's yes;
- a decision and its why, so that it is not undone by the next session;
- the state of work in progress: what is done, what is next, what blocks it;
- a trap that fails silently or misleads: a wrong result without an error, a failure that looks like
  the change's fault.

Not an entry: a command that needs another form on this machine, a missing dependency, a flag an error
message names - anything the agent sees and fixes in passing.

## Groups

Entries live in groups: directories right under `.agents/knowledge/`, each named by the topic of its
entries (`infra`, `services`, `process`, ...). There is no fixed list: the agent that records an entry
keeps the groups in shape, in the same commit, and the review of the pull request sees it.

- **Indexes.** The top `INDEX.md` has one row per group: its name and the names of its entries. The
  `INDEX.md` of a group lists every entry with its kind, verification date and summary. The top index
  stays one row per group however much knowledge there is; an agent reads a group's index for its
  topic.
- **Create** a group when a new entry fits none of the existing ones, together with that entry.
- **Split** a group when it passes about 20 entries or its entries are on two topics.
- **Merge or rename** groups when two hold the same topic or a name no longer tells what is inside:
  `git mv` the entries and fix the links `index.py` names as broken, in one commit.
- **Delete**: a group goes with its last entry - `index.py` removes the `INDEX.md` of a group left
  without entries.
- **Archive**: finished work moves to `archive/` inside its group, the outcome in a few lines; the
  group's index lists it under Archive and it is never due for verification.
- A group is one level deep: `index.py` refuses an entry anywhere else than `<group>/<entry>.md` or
  `<group>/archive/<entry>.md` (a rare entry with no group may lie right in `.agents/knowledge/`).

## An entry

One topic per file, under about 80 lines, in English unless `.agents/project.md` names another
language for them, from [`TEMPLATE.md`](TEMPLATE.md):

| Field | Meaning |
| --- | --- |
| `summary` | one line; it becomes the entry's line in its group's `INDEX.md` |
| `kind` | what the entry is, see below |
| `verified` | `YYYY-MM-DD`: when it was last checked against reality |
| `verify` | how to check it: a command, or a link when no command can |
| `sources` | where it was learned: pull requests, issues, docs, people |

| `kind` | For | Example |
| --- | --- | --- |
| `fact` | how things are around the repository: what a system, a resource or a team is, where it is, who owns it | which database staging and production use and how each is reached |
| `how-to` | the steps of doing something here that neither the code nor the docs give | rolling out an image by hand |
| `trap` | only a place where things go wrong silently or misleadingly, and how to recognise and avoid it; an error that names its cause is no entry at all | the database session's time zone moves dates near midnight to the next day |
| `decision` | a choice the team or the user made, its why and what was rejected, so that it is not undone | alert noise is fought without raising thresholds |
| `state` | work in progress: what is done, what is next, what blocks it | a migration done on staging, not yet on production |

An entry has one kind, that of most of its text: a `how-to` keeps its own Traps section rather than
becoming a `trap`. When unsure, it is a `fact`.

- No retelling of code or docs: a link and a line on why to look there.
- Nothing that differs from one person to another: no paths on a workstation (`C:\Users\...`,
  `/home/...`, where a key file or a clone lies), no personal logins as the way in. Write how anyone gets
  the access; the rest goes to `local.md`. `index.py` refuses a line with a path in a home directory.

## Verification

`verified` tells how far an entry can be trusted without a check: a `state` for 14 days, the rest for
90; an entry in `archive/` always. Nobody sweeps the whole knowledge on a schedule, and nobody has to:

- an entry is checked when it is used - before an agent relies on it, it asks
  `python .agents/knowledge/index.py --stale <entry>`; past its term, it verifies the entry the way
  `verify` says first;
- an entry nobody uses misleads nobody; it is checked when a task needs it again;
- an entry found wrong is fixed at once, whatever its date.

An agent verifies only the entries its task uses. `index.py --stale` without a path lists every entry
past its term: that is for a deliberate sweep the user asks for, never part of a task.

## Secrets

Never a secret in an entry: no token, password, key, DSN, connection string with a password, cookie or
private key, not even an expired or a stage one. Write where it is kept and who grants access -
`` `API_TOKEN`: in the secret store at `<path>`, issued by ... `` - and a placeholder such as
`<token>` wherever a command needs the value.

- Do not paste command output, environment variables, config files or logs into an entry as they are:
  retell them, leaving the values out.
- `index.py` refuses an entry with a line that looks like a secret - known token formats, credentials
  in a URL, a value assigned to a secret's name, a long random string - and names only the line, never
  the value. A line that is surely no secret (a documented example) gets `pragma: allowlist secret`
  at its end.
- A secret that reached a commit stays in the git history after the entry is fixed: tell the user
  at once, so that it is revoked and reissued.

## Personal

`local.md` next to this file holds what is true for one person only: where their keys, kubeconfig or
clones lie on their machine, their own accounts, how they want the agent to work in this repository.
Free form, no frontmatter, never committed (`.gitignore` here), not in any index; still no secret
values in it.

There is one such file per repository, in its main clone: a worktree has none of its own.
`python .agents/knowledge/index.py --local` prints the path of the main clone's file from the clone
and from any of its worktrees.

## Protocol

1. **Start.** Read the top `INDEX.md` and the file `index.py --local` names, if it exists. Before
   working on a topic, read the `INDEX.md` of its group and the entries the task needs; if the task
   touches work in progress (`kind: state`), read that entry first and keep it current.
2. **Rely, then verify.** Before acting on an entry, run `index.py --stale <entry>`. Within its term,
   rely on it; past it, check it the way `verify` says first. It holds - set `verified` to today. It
   does not - fix the entry and add where the new knowledge came from.
3. **Record** what passes the test above, above all what the user told: a correction ("we do it
   differently here"), where a resource is and what it is for, a decision and its why, the new state
   of the work in progress; what holds only for this user goes to `local.md`. Do not record what
   the code shows, what an agent fixes in passing, or what will not happen again.
4. **When.** Entries go into the pull request of the task they were learned in - an entry about what
   it changes, and knowledge learned on the way as a separate commit - and are
   reviewed with it. A pull request of its own only when there is no task branch, e.g. after work on
   an environment. Tell the user in one line what was added or fixed.
5. **Conflict.** An entry that disagrees with the code or the docs is wrong: fix or delete it.
6. **Index.** After adding, moving or deleting an entry or changing its frontmatter, run
   `python .agents/knowledge/index.py`; the pre-commit hook below fails a commit whose indexes are
   behind.

## Wiring

Once per repository:

- `.pre-commit-config.yaml` - the hook that keeps the indexes and the entries' format right and secrets
  out. On a commit it runs only when `.agents/knowledge/` changes; the pre-commit job in CI runs every
  hook on all files, so it also catches an entry whose link into the code broke when the code moved:

  ```yaml
  - repo: local
    hooks:
      - id: knowledge-index
        name: knowledge index
        entry: python .agents/knowledge/index.py
        language: python
        pass_filenames: false
        files: ^\.agents/knowledge/
  ```

- `AGENTS.md` from the hub tells every agent to start here when the repository has this directory;
  `CLAUDE.md` of the `claude` pack imports `AGENTS.md` for Claude Code.
- Run `python .agents/knowledge/index.py` once to create the indexes and commit them.
