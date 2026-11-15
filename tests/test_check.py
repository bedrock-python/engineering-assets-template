"""
Tests of packs/ai-review/.agents/review/check.py on throwaway repositories: python -m unittest discover -s tests
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parents[1] / "packs" / "ai-review" / ".agents" / "review" / "check.py"
BRANCH = "feat/X-1__y"
LINES = "".join(f"{n}\n" for n in range(1, 10))
# not ASCII, and encodable in UTF-16 and cp1251: a record in cp1251 is then not valid UTF-8
MODEL = "test €"
# the developer's git config (signed commits, hooks, templates) stays out of the throwaway repositories
ISOLATED = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


class CheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.repo = root / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "master")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        self.git("config", "core.autocrlf", "false")
        self.write(".gitignore", "local/\n")
        self.write("a.txt", LINES)
        self.commit("init")
        self.git("init", "-q", "--bare", str(root / "remote.git"), cwd=root)
        self.git("remote", "add", "origin", str(root / "remote.git"))
        self.git("push", "-q", "origin", "master")
        self.git("remote", "set-head", "origin", "master")
        self.git("switch", "-q", "-c", BRANCH)
        self.write("a.txt", LINES.replace("5\n", "5b\n"))
        self.commit("five")
        self.record = self.repo / "local" / "reviews" / f"{BRANCH}.md"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = subprocess.run(["git", *args], cwd=cwd or self.repo, capture_output=True, text=True, check=True, env=ISOLATED)
        return result.stdout.strip()

    def write(self, name: str, text: str) -> None:
        (self.repo / name).write_bytes(text.encode())

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def head(self) -> str:
        return self.git("rev-parse", "HEAD")

    def write_record(self, commit: str, *, newline: str = "\n", encoding: str = "utf-8") -> None:
        self.record.parent.mkdir(parents=True, exist_ok=True)
        text = newline.join(["---", f"commit: {commit}", f"model: {MODEL}", "---", ""])
        self.record.write_bytes(text.encode(encoding))

    def check(self, *args: str, env: dict[str, str] | None = None) -> tuple[int, str]:
        clean = {k: v for k, v in ISOLATED.items() if not k.startswith("PRE_COMMIT_")}
        result = subprocess.run(
            [sys.executable, str(CHECK), *args], cwd=self.repo, capture_output=True, text=True, env={**clean, **(env or {})}
        )
        return result.returncode, result.stdout

    def change_master(self, name: str, text: str) -> None:
        self.git("switch", "-q", "master")
        self.write(name, text)
        self.commit(f"master changes {name}")
        self.git("push", "-q", "origin", "master")
        self.git("switch", "-q", BRANCH)

    def test_no_record_is_reported_and_fails_only_strict(self) -> None:
        code, out = self.check("--strict")
        self.assertEqual(code, 1)
        self.assertIn(f"AI review of {BRANCH}: not run yet", out)
        self.assertEqual(self.check(), (0, out))

    def test_record_at_head_is_reviewed(self) -> None:
        self.write_record(self.head())
        self.assertEqual(self.check("--strict")[0], 0)

    def test_new_commit_after_the_review_is_behind(self) -> None:
        self.write_record(self.head())
        self.write("b.txt", "b\n")
        self.commit("b")
        code, out = self.check("--strict")
        self.assertEqual(code, 1)
        self.assertIn("1 file(s) changed", out)

    def test_rebase_keeping_the_changes_is_reviewed_and_refresh_moves_only_the_commit(self) -> None:
        for newline, encoding in (("\n", "utf-8"), ("\r\n", "utf-8"), ("\n", "utf-16")):
            with self.subTest(newline=newline, encoding=encoding):
                self.tearDown()
                self.setUp()
                self.write_record(self.head(), newline=newline, encoding=encoding)
                self.change_master("m.txt", "m\n")
                self.git("rebase", "-q", "origin/master")
                self.assertEqual(self.check("--strict")[0], 0)
                self.assertEqual(self.check("--strict", "--refresh")[0], 0)
                expected = newline.join(["---", f"commit: {self.head()}", f"model: {MODEL}", "---", ""])
                self.assertEqual(self.record.read_bytes().decode(encoding), expected)

    def test_rebase_onto_a_change_next_to_the_hunk_is_behind(self) -> None:
        self.write_record(self.head())
        self.change_master("a.txt", LINES.replace("3\n", "3m\n"))
        self.git("rebase", "-q", "origin/master")
        self.assertEqual(self.check("--strict")[0], 1)

    def test_reindented_or_moved_line_after_the_review_is_behind(self) -> None:
        self.write_record(self.head())
        reviewed = self.head()
        changed = {
            "indent": LINES.replace("5\n", "    5b\n"),
            "line ending": LINES.replace("5\n", "5b\r\n"),
            "move": LINES.replace("5\n", "").replace("8\n", "8\n5b\n"),
        }
        for name, text in changed.items():
            with self.subTest(name):
                self.git("reset", "-q", "--hard", reviewed)
                self.write("a.txt", text)
                self.commit(name)
                self.assertEqual(self.check("--strict")[0], 1)
                self.git("reset", "-q", "--soft", "HEAD~2")
                self.commit(f"{name}, rewritten")
                self.assertEqual(self.check("--strict")[0], 1)

    def test_rebase_with_other_changes_is_behind_and_leaves_the_record(self) -> None:
        self.write_record(self.head())
        before = self.record.read_bytes()
        self.git("reset", "-q", "--soft", "HEAD~1")
        self.write("a.txt", LINES.replace("5\n", "5c\n"))
        self.commit("five again")
        self.assertEqual(self.check("--strict", "--refresh")[0], 1)
        self.assertEqual(self.record.read_bytes(), before)

    def test_merge_of_the_base_is_reviewed_until_an_own_file_changes(self) -> None:
        self.write_record(self.head())
        self.git("switch", "-q", "master")
        self.write("m.txt", "m\n")
        self.commit("m")
        self.git("push", "-q", "origin", "master")
        self.git("switch", "-q", BRANCH)
        self.git("merge", "-q", "--no-edit", "origin/master")
        self.assertEqual(self.check("--strict")[0], 0)
        self.write("a.txt", LINES.replace("5\n", "5d\n"))
        self.commit("own")
        self.assertEqual(self.check("--strict")[0], 1)

    def test_record_not_in_utf8_is_read_and_never_rewritten(self) -> None:
        self.write_record(self.head(), encoding="cp1251")
        before = self.record.read_bytes()
        self.change_master("m.txt", "m\n")
        self.git("rebase", "-q", "origin/master")
        self.assertEqual(self.check("--strict", "--refresh")[0], 0)
        self.assertEqual(self.record.read_bytes(), before)

    def test_push_of_head_checks_the_checked_out_branch(self) -> None:
        env = {"PRE_COMMIT_LOCAL_BRANCH": "HEAD", "PRE_COMMIT_TO_REF": self.head()}
        code, out = self.check("--strict", env=env)
        self.assertEqual(code, 1)
        self.assertIn(BRANCH, out)

    def test_push_of_another_branch_checks_that_branch(self) -> None:
        self.git("branch", "feat/other")
        self.git("switch", "-q", "master")
        env = {"PRE_COMMIT_LOCAL_BRANCH": "refs/heads/feat/other", "PRE_COMMIT_TO_REF": self.git("rev-parse", "feat/other")}
        code, out = self.check("--strict", env=env)
        self.assertEqual(code, 1)
        self.assertIn("feat/other", out)

    def test_default_branch_and_detached_head_are_skipped_but_fail_strict(self) -> None:
        self.git("switch", "-q", "master")
        self.assertEqual(self.check(), (0, ""))
        self.assertEqual(self.check("--strict")[0], 1)
        self.git("switch", "-q", "--detach", BRANCH)
        self.assertEqual(self.check(), (0, ""))
        self.assertEqual(self.check("--strict")[0], 1)

    def test_a_review_behind_never_blocks_a_push(self) -> None:
        self.write_record(self.git("rev-parse", "HEAD~1"))
        self.assertEqual(self.check()[0], 0)


if __name__ == "__main__":
    unittest.main()
