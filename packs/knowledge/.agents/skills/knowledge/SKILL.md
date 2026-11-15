---
name: knowledge
description: Read, verify and record this repository's knowledge in .agents/knowledge - what agents learned here and would otherwise ask again - which services, resources and other teams are for what and whom to go to, how to reach the environments and act there, the team's conventions, decisions, work in progress, silent traps. Use at the start of work on a topic, when an entry turns out wrong, and when the user told something an agent could not have found by itself.
---

# Knowledge

The rules live in [.agents/knowledge/README.md](../../knowledge/README.md): read it in full first. This skill only runs its protocol. Work from the repository root, the directory that holds `.agents/`. The request names a topic, `record` or `stale`; `python` below is `python3` where `python` is not on the path.

- **A topic** (the default): read `.agents/knowledge/INDEX.md` and the personal `local.md` whose path `python .agents/knowledge/index.py --local` prints, if it exists, then the `INDEX.md` of the topic's group and the entries the task needs. Run `python .agents/knowledge/index.py --stale <those entries>` and verify the ones it lists the way their `verify` says: set `verified` to today when an entry holds, fix it when it does not. Leave the other entries alone. Report what the entries say for the task and what was verified or fixed.
- **`record`**: go through this session for what passes the README's test "What is worth an entry", above all what the user told; skip whatever was found in the code or fixed in passing. For each item, find the entry it belongs to through the indexes and update it, or create one from `TEMPLATE.md` in its group, keeping the groups as the README's "Groups" says; what holds only for this user goes to `local.md`. Then run `python .agents/knowledge/index.py` and show the user the entries added or changed, one line each.
- **`stale`**, only when the user asks for a sweep: run `python .agents/knowledge/index.py --stale` (a group's path narrows it), verify each listed entry, update or fix it, rebuild the indexes and report what changed.

Never put a secret or its value into an entry, nor command output, environment variables or configuration as they are: write where the secret is kept, as the README's "Secrets" says. When `index.py` says a line looks like a secret, remove the value; mark the line `pragma: allowlist secret` only when it surely is none. Show the changes and commit them only after the user's yes, as the README's protocol says; never open a pull request on your own.
