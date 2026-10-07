# Engineering Assets

> Your organisation's engineering standard, delivered to every repository as pull requests: agent instructions, review prompts, merge request templates and shared CI files.

This is a template. Create your own **hub** from it, put the files your teams share into packs, and list the repositories they belong to. Every change to a pack then arrives in those repositories as a pull request (a merge request on GitLab) that a person reviews and merges.

The work is done by [touchmark](https://github.com/bedrock-python/touchmark) ([documentation](https://bedrock-python.github.io/touchmark/)). It only ever touches files it can prove it shipped: a file a team has changed stays theirs.

*Waiting for touchmark's first release. Until v0.1.0 is out, the workflows pin touchmark to a placeholder marked `TODO(release)`, and a hub created from this template cannot run yet. Watch [touchmark's releases](https://github.com/bedrock-python/touchmark/releases).*

```
your-org/engineering-assets                 this hub: packs/, hub.yml, targets.yml
        │  one pull request per repository on every change to a pack
        ▼
your-org/billing, your-org/sdk-python, …    opted in, or subscribed by the hub
```

## What's inside

```
packs/                                  the files you deliver, one directory per pack
  agents/                               AGENTS.md, a project profile to fill in, review and refactoring prompts
  claude/                               Claude Code instructions, skills, a reviewer subagent, settings
  python-service/                       guidelines for Python services; skills to run, test and format
  python-library/                       guidelines for Python libraries and their public API
  gitlab/                               merge request and issue templates
hub.yml                                 hub id, write account, security settings, pack descriptions and dependencies
targets.yml                             which repositories to visit and which packs they get (empty)
.touchmark/operations.yml               one-off operations, reviewed like any other change (empty)
.github/workflows/engineering-assets.yml   GitHub Actions: check and plan on pull requests, distribute and doctor
.github/dependabot.yml                  updates the pinned actions, touchmark among them
.github/CODEOWNERS                      who reviews changes to the hub, on GitHub
.gitlab-ci.yml                          the same jobs on GitLab CI
.gitlab/CODEOWNERS                      code owners on GitLab
.gitea/workflows/                       the same jobs on Gitea and Forgejo Actions
.gitea/CODEOWNERS                       code owners on Gitea and Forgejo
renovate.json                           updates the pinned touchmark image (GitLab, Gitea, Forgejo)
scripts/validate.sh                     runs touchmark check and actionlint before you push
LICENSE                                 MIT-0
```

Only `packs/` is delivered; everything else configures the hub. The starter packs are yours: edit them, delete them, add your own. Nothing in the hub updates itself from upstream. Only the touchmark engine does, through a Dependabot or Renovate pull request that you review.

The CI files of all platforms ship together, and each platform reads only its own. You may delete the ones you don't use, with their CODEOWNERS.

## Set up your hub

### On GitHub

`touchmark setup github`, run from a clone of the hub with an administrator's token, does most of steps 2 to 4: it creates both Apps, the environment and the ruleset, and prints the commands that store the keys. You install the Apps. See [Set up a hub's platform](https://bedrock-python.github.io/touchmark/guide/setup/).

1. **Create the hub.** Click **Use this template** and create `your-org/engineering-assets`. It can be private, but see [Security](#security) for GitHub Free. Don't fork: forks of public repositories are always public.
2. **Create two GitHub Apps** in your organisation, and install both on the repositories you will target, not on the hub:
   - *reader*, with Metadata, Contents and Pull requests read-only;
   - *writer*, with Metadata read-only, and Contents, Pull requests and Workflows read and write. touchmark asks for Workflows only for a target that needs it.
3. **Store the keys.**
   - Reader: the repository variable `TOUCHMARK_READ_APP_ID` (the App ID) and the repository secret `TOUCHMARK_READ_APP_KEY` (its private key).
   - Writer: create an environment named `touchmark-distribute`. Set its Deployment branches and tags to *Selected branches and tags*, with your default branch only. Store the variable `TOUCHMARK_WRITE_APP_ID` and the secret `TOUCHMARK_WRITE_APP_KEY` in that environment, and nowhere else. Don't choose *Protected branches only*: with no protection rules, every branch qualifies.

   The workflow's `probe` job stops `distribute` if the write key is also visible as a repository or organisation secret, and touchmark itself checks the environment's branch policy before it writes.
4. **Protect the hub.** Add a ruleset for the default branch that requires a pull request with an approving review and a review from Code Owners. Replace `@acme/hub-maintainers` in `.github/CODEOWNERS` with your team.
5. **Describe your hub.** In `hub.yml` set `id`, and `writer` to the writer App's bot name, like `acme-assets-write[bot]`. List your repositories in `targets.yml`.
6. **Open a pull request.** The `check` job validates the hub; the `plan` job reports what each repository would receive and keeps the report in a comment. Write access is checked when `distribute` runs, and every week by `doctor`.
7. **Merge it.** The `distribute` job opens a pull request in every repository that has opted in. It runs again every day and on every merge; **Run workflow** runs `distribute` and `doctor` at once. The workflow starts on pushes to `main` and `master`: if your default branch has another name, add it under `push: branches:`.

The jobs run on `ubuntu-latest`. On self-hosted runners, the touchmark Action needs Linux with Docker, `docker buildx` and the GitHub CLI (`gh`), which it uses to check the image's build provenance, and HTTPS access to `ghcr.io` and to the Sigstore trust roots `gh` fetches for that check (`tuf-repo-cdn.sigstore.dev` and `tuf-repo.github.com`).

### On GitLab (gitlab.com or self-managed)

`touchmark setup gitlab --group <your group>`, run from a clone of the hub with the token of a Maintainer of the hub who owns that group, does steps 2 to 4 through the API. See [Set up a hub's platform](https://bedrock-python.github.io/touchmark/guide/setup/).

1. **Create the hub.** Choose New project → Import project → Repository by URL and give this repository's URL, `https://github.com/bedrock-python/engineering-assets-template.git`.
2. **Create two service accounts** and add them to the groups that own your repositories. On instances without service accounts, use group access tokens. Keep the hub out of those groups: put it in a group or subgroup the accounts don't belong to, and add the accounts, or create the group access tokens, only on groups that hold targets and not the hub. A member of a group inherits its projects, and a group access token is a member of its group, so a writer on a group that holds the hub could push to it; `touchmark setup gitlab` refuses that layout, and `doctor` fails on it.
   - The *reader* has the role Reporter and a token with `read_api` and `read_repository`. Store it as the variable `TOUCHMARK_READ_TOKEN`, masked but not protected: merge request pipelines need it.
   - The *writer* has the role Developer and a token with `api` and `write_repository`. Store it as `TOUCHMARK_WRITE_TOKEN`: Protected, Masked and hidden, environment scope `touchmark-distribute`. Don't add the writer to the hub project.
3. **Lock down the hub.**
   - Protect only the default branch (Allowed to push: No one) and don't create protected tags.
   - Set *Minimum role to use pipeline variables* to *No one allowed*, and keep *Allow merge request pipelines to access protected variables* off.
   - The `probe` job fails a merge request pipeline that can see the write token. Run `touchmark doctor --hub-token` once with a Maintainer token to check the variable's settings.
   - Replace `@acme/hub-maintainers` in `.gitlab/CODEOWNERS` with your group. Requiring code owner approval needs Premium.
   - Every job runs in the touchmark image, so the hub's runners must honor `image:`: GitLab.com's hosted runners do, and so do the Docker, Docker Autoscaler and Kubernetes executors. The Shell executor ignores `image:`, and the jobs fail.
   - If your runners can't pull from ghcr.io, change the image in `.gitlab-ci.yml` in a reviewed merge request. The image is pinned by digest on purpose: an overridable variable could leak the token.
4. **Schedule the runs.** Under Build → Pipeline schedules, create two schedules for the default branch: a daily one described `touchmark distribute` and a weekly one described `touchmark doctor`. The `doctor` job runs in schedules whose description contains "doctor"; every other schedule runs `distribute`.
5. **Describe your hub.** In `hub.yml` set `id`, and `writer` to the writer's username. For a self-managed instance, describe it under `providers` instead, with its `url` and `writer`, so that touchmark also knows it outside CI. List your repositories in `targets.yml`.
6. **In your target projects,** turn on the CI/CD job token allowlist (*Limit access to this project*). Sync pipelines run as the writer, so their job token carries the writer's access to your other projects. Use a separate writer for groups you trust differently.
7. **Open a merge request** and check the `check`, `plan` and `probe` jobs. The plan report is attached to the merge request.
8. **Merge it.** The `distribute` job opens a merge request in every project that has opted in. **Run pipeline** on the default branch runs `distribute` and `doctor`.

### On Gitea or Forgejo

Gitea and Forgejo Actions can't limit a secret to the default branch, so touchmark won't use their CI with `security.write_isolation: platform`. Pick one:
- run the hub's CI on GitHub or GitLab, and deliver to Gitea or Forgejo from there: add them as `providers` in `hub.yml` and their keys next to the others;
- host the hub on Gitea or Forgejo, set `security.write_isolation: none` with a `reason`, and protect every branch (`*`) so that only maintainers can push. Contributors then work from forks, which receive no secrets.

For a hub on Gitea or Forgejo:
1. **Create the hub** by migrating this repository.
2. **Create two bot users:** a reader in a team with read access and a writer in a team with write access to your repositories. Give the teams your target repositories one by one, not *all repositories* of the organisation, which would include the hub. Reader token: `read:repository, read:issue, read:organization, read:user`. Writer token: `write:repository, write:issue, read:organization, read:user`. Never use an admin token. Store them as the Actions secrets `TOUCHMARK_READ_TOKEN` and `TOUCHMARK_WRITE_TOKEN`.
3. **Check the runner label.** The workflows in `.gitea/workflows/` run on `ubuntu-latest`, the label of Gitea's default runners. If your runners are registered with other labels, change `runs-on`. Every job runs in the touchmark image and clones the hub with git, so it needs no actions from github.com or a mirror. The report is in the job's log, and on Gitea 1.27 with runner 2.0 in its summary.
4. **Protect the hub** as above, and replace `@acme/hub-maintainers` in `.gitea/CODEOWNERS` with your team.
5. **Describe your hub.** Set `id` and `writer` in `hub.yml`, then open a pull request and merge it. `distribute` runs on every merge to `main` or `master` (add your default branch under `push: branches:` if it has another name) and every day; `doctor` every Monday, from `.gitea/workflows/engineering-assets-doctor.yml`.

## Opt a repository in

Nothing happens to a repository until it has `.engineering-assets.yml` at its root, unless the hub subscribes it (below). The file can be empty: its presence is the consent. It can also ask for more packs and keep some paths for itself, or say `enabled: false` to opt out:

```yaml
version: 1
packs: [claude]                 # in addition to what the hub assigns
ignore:
  - .claude/settings.json       # we keep our own
  - docs/guidelines/**
```

Editing `packs` or `ignore` in this file is also how a team changes its mind: content it declined by closing a sync pull request is proposed again after the change. Comments and formatting don't count.

The hub decides the minimum every target gets in `targets.yml`. A repository can add packs and ignore paths, but it can't remove a pack the hub assigns.

```yaml
# targets.yml
version: 1
defaults:
  packs: [agents]
targets:
  - repo: your-org/billing
    packs: [python-service]
  - org: your-org               # on GitLab: group: your-org/platform
    topics: [python-library]
    packs: [python-library]
  - repo: corp:platform/api     # a repository on another provider from hub.yml
  - repo: https://gitlab.example.com/platform/web   # or its web URL
  - org: your-org
    match: [your-org/svc-*]     # only the repositories whose path matches
    opt_in: assumed             # subscribed by the hub: no opt-in file needed
exclude:
  - your-org/*-archive          # * within a segment, ** across segments, ? one character
  - corp:platform/legacy/**
```

A web URL names a repository or a namespace of the provider in `hub.yml` whose `url` it lies under; reports name every target `<provider>:<path>`.

**When the hub subscribes.** An entry with `opt_in: assumed` (or `defaults.opt_in: assumed`) makes the repositories it selects count as opted in without the file: they get the packs of `targets.yml`, and their first sync pull request says the hub subscribed them. Closing it is a decline, remembered as for any target. A team chooses packs or ignores files by adding `.engineering-assets.yml`, and opts out with `enabled: false` in it; deleting the file of a subscribed repository returns it to the hub's subscription.

## The starter packs

| Pack | What a repository gets | Needs |
|---|---|---|
| `agents` | `AGENTS.md`, the instructions every coding agent reads; `.agents/project.md`, a project profile for the team to fill in; `.agents/prompts/review.md` and `.agents/prompts/refactor-check.md` | — |
| `claude` | `CLAUDE.md`, which imports `AGENTS.md` and the profile; `.claude/settings.json`, which only denies reading secrets; the skills `/review-change`, `/spec`, `/new-branch`, `/commit` and `/pr`; the `reviewer` subagent | `agents` |
| `python-service` | `docs/guidelines/python.md`, `testing.md` and `database.md`; the skills `/app-start`, `/app-stop`, `/test` and `/fmt`; the `test-runner` subagent | `agents` |
| `python-library` | `docs/guidelines/python.md`, `testing.md` and `public-api.md` | `agents` |
| `gitlab` | `.gitlab/merge_request_templates/Default.md`, `.gitlab/issue_templates/Bug.md` and `Feature.md` | — |

How they fit together:
- **Shared instructions, local facts.** The shared files never name a tracker, a branch pattern or a build command. They tell agents to read `.agents/project.md`, where each team writes those facts. The profile ships as a skeleton: once a team edits it, it belongs to the repository.
- **One source for every agent.** Codex, Cursor, Copilot and Claude Code read `AGENTS.md`; `CLAUDE.md` imports it for Claude Code. The review checklist lives once in `.agents/prompts/review.md`, and the Claude skill and subagent follow it.
- **Skills with side effects wait to be asked.** `/new-branch`, `/commit`, `/pr`, `/spec`, `/app-start` and `/app-stop` run only when you invoke them. Skill names avoid Claude Code's built-in commands, such as `/review` and `/branch`.
- **No hooks, no extra permissions.** `.claude/settings.json` holds deny rules only.
- `python-service` and `python-library` both ship `docs/guidelines/python.md` and `testing.md`, with different content: give a repository one of them.

GitHub reads pull request and issue templates, `CODE_OF_CONDUCT.md` and `SECURITY.md` from your organisation's `.github` repository when a repository has none, so there is no GitHub pack. Add one if those files must live in every repository.

## Write packs

- **Layout.** A pack is a directory in `packs/`, laid out like the target repository: `packs/agents/AGENTS.md` becomes `AGENTS.md`. Every file in it is delivered, so describe a pack in `hub.yml`, not in a README inside it.
- **Order.** Packs apply in order; if two ship the same path, the later one wins. Declare dependencies under `packs:` in `hub.yml` with `requires`, and touchmark orders the packs for you.
- **Renames.** When you rename a pack, list its old name under `formerly` in `hub.yml`, so files the old name shipped stay managed.
- **Size.** Every file must be at least 64 bytes: smaller content can't prove where it came from.
- **Reserved file.** Don't ship `.engineering-assets.yml`. It belongs to each repository.
- **Seed files.** A file that a team is expected to fill in, like `.agents/project.md`, can ship as a skeleton. Once edited, it belongs to the repository and is never touched again.
- **Project facts.** Keep tracker keys, branch patterns, the pull request language and build commands out of shared files. They belong in the project profile, which the shared instructions tell agents to read.
- **Commit first.** touchmark ships what is committed on the default branch, not your working tree.

## Day to day

| To… | Do this |
|---|---|
| change a shared file everywhere | edit it in the pack, open a pull request in the hub, check `plan`, merge |
| let one repository keep its own version | edit the file in that repository (it becomes local), or add it to `ignore` |
| bring a diverged file back under the hub | run `touchmark apply --adopt <path>` in that repository and open a pull request there |
| retire a file | delete it from the pack; repositories that never changed it get a pull request deleting it |
| add a repository | add it to `targets.yml`; the next run visits it once it has opted in, or at once with `opt_in: assumed` |
| undo a closed sync pull request | reopen it, or tick *Propose this content again* in its description |
| resume a sync branch someone pushed to | tick *Rebuild this branch* in the pull request, or add a `recreate` entry with the branch head to `.touchmark/operations.yml` |
| move a target to another provider on the same host | add the old write account to `known_authors` in `hub.yml` |
| check the write account | read the weekly `doctor` job, or run the workflow by hand |
| upgrade touchmark | read the release notes, then merge the Dependabot or Renovate pull request. Dependabot's `plan` gets no secrets and shows the hub's side only; Renovate opens its merge request once you approve it on the Dependency Dashboard, and its `plan` checks the targets |

## Validate locally

`scripts/validate.sh` runs what the CI runs, before you push:

```sh
bash scripts/validate.sh             # touchmark check, then actionlint on .github and .gitea workflows
bash scripts/validate.sh --release   # also fail unless touchmark is pinned to a published release
```

It checks a fresh copy of your working tree, committed or not, as a hub created from it would look. It needs `touchmark` on your `PATH`, or the command that runs it in `TOUCHMARK`, and `actionlint` or Docker. The GitLab CI file is checked by GitLab itself: use CI Lint in the project.

## Security

A hub can open pull requests in every repository it targets, so treat it as the root of your supply chain:

- A merge into the hub runs code in your targets' CI: a sync pull request runs the target's workflows with its secrets before anyone reviews it. Protect the default branch, require review, and keep CODEOWNERS on `packs/`, `hub.yml`, `targets.yml`, `.touchmark/` and the CI files.
- Keep the write account on the default branch only: the `touchmark-distribute` environment on GitHub, a protected, environment-scoped variable on GitLab. The probe checks that no other job can see the key, and `distribute` refuses to run otherwise, unless `hub.yml` sets `security.write_isolation` to `external`, or to `none` with a reason. A private hub on GitHub Free can't pass: make the hub public, use the Team plan, or release the key from an external secret store through OIDC.
- The hub's maintainers hold the write account on every platform: they can change the variables, the environments and the workflows. Choose them accordingly.
- One-off operations that override a safeguard live in `.touchmark/operations.yml` and go through review. The workflows take no inputs, and touchmark refuses those flags in CI.
- The read account can read every target, and anyone who can push a branch to the hub can use it. Keep hub write access tight.
- touchmark is pinned, and upgraded through review: the Action by commit, and the image by digest on GitLab, Gitea and Forgejo. The Action runs the image of its own release, by digest, and only after `gh attestation verify` has shown that touchmark's publish workflow built it. Dependabot's pull requests get no secrets, so their `plan` checks no target: it shows the hub's side, warns, and passes. Read the release notes, and run `plan` with the read key yourself before you merge. Renovate waits a week for other updates, but GHCR gives no release dates, so for the touchmark image it waits for your approval on its Dependency Dashboard instead.
- Read the ⚠ section of every sync pull request. It lists changes to workflows, CI configuration, agent settings, skills and subagents, and CODEOWNERS.
- In a public repository, GitHub disables scheduled workflows after 60 days without activity. Push to the hub or re-enable the workflow if the daily run stops. On GitLab, a schedule stops when its owner loses access: give it to an account that stays.
- A public hub skips private targets and prints only how many, because anyone can read its CI logs.

touchmark never merges. It never overwrites or deletes a file a repository has changed.

## License

The template and its starter packs are released under [MIT-0](LICENSE): use and change them without attribution. touchmark itself is Apache-2.0.
