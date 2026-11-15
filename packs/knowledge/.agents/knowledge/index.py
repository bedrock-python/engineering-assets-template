"""
Builds the indexes of this repository's knowledge from the entries' frontmatter and checks the entries:
their frontmatter, their place in the groups, their links, and that no line looks like a secret or a path
on one person's machine.

The top INDEX.md lists the groups and the names of their entries; the INDEX.md of each group lists its
entries with their kind, verification date and summary.

    index.py                write the INDEX.md files; exit 1 if one changed or an entry is invalid
    index.py --check        write nothing; exit 1 if an INDEX.md is out of date or an entry is invalid
    index.py --stale PATH   tell whether the entries or groups given are past their verification term
    index.py --stale        the same for every entry: for a deliberate sweep only
    index.py --local        print the path of this person's local.md in the main clone, from a worktree too

Only the standard library: it runs from pre-commit in a repository of any language.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

ROOT = Path(__file__).resolve().parent
SCRIPT = Path(__file__).name
INDEX = "INDEX.md"
LOCAL = "local.md"
NOT_ENTRIES = {"README.md", INDEX, "TEMPLATE.md", LOCAL}
ARCHIVE = "archive"
KINDS = ("fact", "how-to", "trap", "decision", "state")
REQUIRED = ("summary", "kind", "verified", "verify")
# a state goes out of date with the work it describes, the rest with the systems around it
DUE_AFTER_DAYS = {"state": 14}
DEFAULT_DUE_AFTER_DAYS = 90

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
EXTERNAL = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)

ALLOWLIST_MARK = "pragma: allowlist secret"
SECRETS = {
    "a private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "a GitLab token": re.compile(r"\bgl(?:pat|cbt|dt|rt|ptt|ft|soat|agent)-[0-9A-Za-z_-]{16,}"),
    "a GitHub token": re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}"),
    "a Vault token": re.compile(r"\bhv[sbr]\.[0-9A-Za-z_-]{20,}"),
    "an AWS access key": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "a Slack token": re.compile(r"\bxox[abposr]-[0-9A-Za-z-]{10,}"),
    "an API key": re.compile(r"\bsk-[0-9A-Za-z_-]{20,}"),
    "a JWT": re.compile(r"\beyJ[0-9A-Za-z_-]{10,}\.eyJ[0-9A-Za-z_-]{10,}\.[0-9A-Za-z_-]{10,}"),
    "credentials in a URL": re.compile(r"\b[a-z][a-z0-9+.-]*://[^\s/:@<>{}]+:[^\s/@<>{}]+@", re.IGNORECASE),
    "a secret assigned to a name": re.compile(
        r"(?i)(?<![a-z])(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|private[_-]?key|client[_-]?secret)"
        r"\w*[\"']?\s*[:=]\s*[\"']?(?=[^\s\"'`<>{}$*/:]*\d)(?=[^\s\"'`<>{}$*/:]*[A-Za-z])[^\s\"'`<>{}$*/:]{12,}(?=[\s\"'`]|$)"
    ),
}
# hashes and digests are hex, names break on `-`, `_` or `.`, paths on `/` into short pieces: a long run
# of mixed-case letters with digits is what keys and passwords look like
LONG_RANDOM = re.compile(
    r"(?<![0-9A-Za-z+/=])(?=[0-9A-Za-z+/=]*[a-z])(?=[0-9A-Za-z+/=]*[A-Z])(?=[0-9A-Za-z+/=]*\d)[0-9A-Za-z+/=]{32,}"
)
PATH_PIECE = 20
HOME_PATH = re.compile(r"(?:\b[A-Za-z]:[\\/]+(?i:users|documents and settings)|(?<![\w.~])/(?:home|Users))[\\/]+[\w.-]")


@dataclass
class Entry:
    path: Path
    fields: dict[str, str]

    @property
    def parts(self) -> tuple[str, ...]:
        return self.path.relative_to(ROOT).parts

    @property
    def name(self) -> str:
        return "/".join(self.parts)

    @property
    def group(self) -> str:
        return self.parts[0] if len(self.parts) > 1 else ""

    @property
    def archived(self) -> bool:
        return ARCHIVE in self.parts[:-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="write nothing; exit 1 if an INDEX.md is out of date or an entry is invalid",
    )
    mode.add_argument(
        "--stale",
        nargs="*",
        metavar="PATH",
        help="tell whether the entries or groups given (all, without a path) are past their verification term",
    )
    mode.add_argument(
        "--local",
        action="store_true",
        help="print the path of this person's local.md in the main clone, from a worktree too",
    )
    args = parser.parse_args()

    if args.local:
        say(str(local_file()), sys.stdout)
        return 0

    entries, errors = read_entries()
    if args.stale is not None:
        report_stale(select(entries, args.stale))
        return 0

    for error in errors:
        say(error)
    behind = sync_indexes(render_indexes(entries), write=not args.check)
    return 1 if errors or behind else 0


def read_entries() -> tuple[list[Entry], list[str]]:
    entries: list[Entry] = []
    errors: list[str] = []
    for path in sorted(ROOT.rglob("*.md")):
        if path.name == INDEX or (path.parent == ROOT and path.name in NOT_ENTRIES):
            continue
        text = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        entry = Entry(path, parse_frontmatter(text))
        errors += [f"{entry.name}: {problem}" for problem in problems_of(entry, text)]
        entries.append(entry)
    return entries, errors


def parse_frontmatter(text: str) -> dict[str, str]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, colon, value = line.partition(":")
        if colon and key.strip() and not key.startswith((" ", "#")):
            fields[key.strip()] = unquote(value.strip())
    return {}


def unquote(value: str) -> str:
    quote = value[:1]
    if quote in {'"', "'"} and value.endswith(quote) and len(value) > 1:
        return value[1:-1]
    return value


def local_file() -> Path:
    # the main clone's file serves its worktrees too: their common git directory is the main clone's .git
    common = git("rev-parse", "--git-common-dir")
    top = git("rev-parse", "--show-toplevel")
    if not common or not top:
        return ROOT / LOCAL
    # git prints the common directory relative to the directory it runs in, here ROOT
    return (ROOT / common).resolve().parent / ROOT.relative_to(Path(top).resolve()) / LOCAL


def git(*args: str) -> str | None:
    executable = shutil.which("git")
    if not executable:
        return None
    result = subprocess.run([executable, *args], cwd=ROOT, capture_output=True, text=True, check=False)  # noqa: S603
    return result.stdout.strip() if result.returncode == 0 else None


def home_paths_in(text: str) -> list[str]:
    return [
        f"line {number} has a path on one person's machine: move it to {LOCAL}"
        for number, line in enumerate(text.split("\n"), start=1)
        if HOME_PATH.search(line)
    ]


def secrets_in(text: str) -> list[str]:
    found = []
    for number, line in enumerate(text.split("\n"), start=1):
        if ALLOWLIST_MARK in line:
            continue
        found += [f"line {number} looks like {what}" for what, pattern in SECRETS.items() if pattern.search(line)]
        if any(is_random(match.group()) for match in LONG_RANDOM.finditer(line)):
            found.append(f"line {number} looks like a long random string")
    return found


def is_random(run: str) -> bool:
    return max(len(piece) for piece in run.split("/")) >= PATH_PIECE


def problems_of(entry: Entry, text: str) -> list[str]:
    problems = [f"{problem}: write where it is kept instead" for problem in secrets_in(text)]
    problems += home_paths_in(text) + placement_problems(entry)
    if not entry.fields:
        return [*problems, "no frontmatter between two `---` lines at the top"]
    return problems + frontmatter_problems(entry.fields) + link_problems(entry, text)


def placement_problems(entry: Entry) -> list[str]:
    parts = entry.parts
    if parts[0] == ARCHIVE:
        return [f"`{ARCHIVE}/` belongs inside a group"]
    if len(parts) > 3 or (len(parts) == 3 and parts[1] != ARCHIVE):  # noqa: PLR2004
        return [f"too deep: a group is one directory, with only an optional `{ARCHIVE}/` inside"]
    return []


def frontmatter_problems(fields: dict[str, str]) -> list[str]:
    problems = [f"`{key}` is missing" for key in REQUIRED if not fields.get(key)]
    kind = fields.get("kind")
    if kind and kind not in KINDS:
        problems.append(f"`kind: {kind}` is none of {', '.join(KINDS)}")
    verified = fields.get("verified")
    if not verified:
        return problems
    try:
        if dt.date.fromisoformat(verified) > today():
            problems.append(f"`verified: {verified}` is in the future")
    except ValueError:
        problems.append(f"`verified: {verified}` is not a YYYY-MM-DD date")
    return problems


def link_problems(entry: Entry, text: str) -> list[str]:
    return [
        f"the link to `{target}` leads nowhere"
        for target in LINK.findall(text)
        if not EXTERNAL.match(target)
        and not target.startswith("#")
        and not link_base(entry, target).joinpath(target.split("#", 1)[0].lstrip("/")).exists()
    ]


def link_base(entry: Entry, target: str) -> Path:
    return ROOT.parent.parent if target.startswith("/") else entry.path.parent


def render_indexes(entries: list[Entry]) -> dict[Path, str]:
    groups: dict[str, list[Entry]] = {}
    for entry in entries:
        groups.setdefault(entry.group, []).append(entry)
    ungrouped = groups.pop("", [])
    indexes = {ROOT / INDEX: render_top(groups, ungrouped)}
    for group, members in groups.items():
        indexes[ROOT / group / INDEX] = render_group(group, members)
    return indexes


def render_top(groups: dict[str, list[Entry]], ungrouped: list[Entry]) -> str:
    lines = [
        "# Knowledge index",
        "",
        f"Built by `{SCRIPT}` from the entries: do not edit by hand. How to read, verify and record entries:",
        "[README.md](README.md). Before working on a topic, read the `INDEX.md` of its group: each entry there",
        "has its kind, verification date and summary.",
        "",
    ]
    if not groups and not ungrouped:
        return "\n".join([*lines, "No entries yet.", ""])
    if groups:
        lines += ["| Group | Entries |", "| --- | --- |"]
        lines += [f"| [{group}]({group}/{INDEX}) | {entry_names(groups[group])} |" for group in sorted(groups)]
        lines.append("")
    if ungrouped:
        lines += ["## Not in a group", "", *[entry_line(entry, entry.name) for entry in ungrouped], ""]
    return "\n".join(lines)


def entry_names(members: list[Entry]) -> str:
    current = ", ".join(entry.path.stem for entry in members if not entry.archived)
    archived = sum(entry.archived for entry in members)
    return ", ".join(filter(None, [current, f"+{archived} in {ARCHIVE}" if archived else ""]))


def render_group(group: str, members: list[Entry]) -> str:
    lines = [
        f"# Knowledge: {group}",
        "",
        f"Built by `{SCRIPT}` from the entries' frontmatter: do not edit by hand. All groups: [{INDEX}](../{INDEX}).",
        "",
    ]
    base = ROOT / group
    lines += [entry_line(entry, entry.path.relative_to(base).as_posix()) for entry in members if not entry.archived]
    archived = [entry for entry in members if entry.archived]
    if archived:
        lines += [
            "",
            "## Archive",
            "",
            *[entry_line(entry, entry.path.relative_to(base).as_posix()) for entry in archived],
        ]
    lines.append("")
    return "\n".join(lines)


def entry_line(entry: Entry, link: str) -> str:
    summary = entry.fields.get("summary", "").strip() or "(no summary)"
    kind = entry.fields.get("kind", "?")
    verified = entry.fields.get("verified", "?")
    return f"- [{link}]({link}) ({kind}, verified {verified}) - {summary}"


def sync_indexes(indexes: dict[Path, str], *, write: bool) -> list[Path]:
    """Writes the indexes that changed and removes those of groups left without entries; returns them all."""
    changed = [path for path, text in indexes.items() if read_index(path) != text]
    orphaned = [path for path in sorted(ROOT.glob(f"*/{INDEX}")) if path not in indexes]
    for path in changed:
        if write:
            path.write_text(indexes[path], encoding="utf-8", newline="\n")
        say(f"{shown(path)} {'rewritten' if write else f'is out of date: run {SCRIPT}'}")
    for path in orphaned:
        if write:
            path.unlink()
        say(f"{shown(path)} {'removed: its group has no entries' if write else f'has no entries: run {SCRIPT}'}")
    return changed + orphaned


def read_index(path: Path) -> str | None:
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n") if path.exists() else None


def shown(path: Path) -> str:
    return path.relative_to(ROOT.parent.parent).as_posix()


def select(entries: list[Entry], paths: list[str]) -> list[Entry]:
    if not paths:
        return entries
    chosen: list[Entry] = []
    for given in paths:
        target = locate(given)
        matching = [entry for entry in entries if target in (entry.path, *entry.path.parents)]
        if not matching:
            say(f"{given}: no entry or group there", sys.stdout)
        chosen += [entry for entry in matching if entry not in chosen]
    return chosen


def locate(given: str) -> Path:
    for base in (Path.cwd(), ROOT):
        candidate = (base / given).resolve()
        if candidate.exists():
            return candidate
    return (ROOT / given).resolve()


def report_stale(entries: list[Entry]) -> None:
    due = [(entry, why) for entry in entries if (why := why_due(entry))]
    for entry, why in due:
        say(f"{entry.name}: {why}; verify: {entry.fields.get('verify', '(no way given)')}", sys.stdout)
    if not due:
        say("No entry is due for verification.", sys.stdout)


def why_due(entry: Entry) -> str | None:
    if entry.archived:
        return None
    try:
        verified = dt.date.fromisoformat(entry.fields.get("verified", ""))
    except ValueError:
        return "never verified"
    age = (today() - verified).days
    if age > DUE_AFTER_DAYS.get(entry.fields.get("kind", ""), DEFAULT_DUE_AFTER_DAYS):
        return f"verified {age} days ago"
    return None


def say(message: str, stream: TextIO = sys.stderr) -> None:
    stream.write(message + "\n")


def today() -> dt.date:
    return dt.date.today()


if __name__ == "__main__":
    sys.exit(main())
