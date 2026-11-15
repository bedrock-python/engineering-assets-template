"""
Tests of packs/knowledge/.agents/knowledge/index.py on throwaway repositories: python -m unittest discover -s tests
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INDEX_PY = Path(__file__).resolve().parents[1] / "packs" / "knowledge" / ".agents" / "knowledge" / "index.py"
# the developer's git config (signed commits, hooks, templates) stays out of the throwaway repositories
ISOLATED = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
TODAY = dt.date.today()


class IndexTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.knowledge = self.repo / ".agents" / "knowledge"
        self.knowledge.mkdir(parents=True)
        shutil.copy(INDEX_PY, self.knowledge / "index.py")
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True, env=ISOLATED)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def entry(self, name: str, *, kind: str = "fact", verified: dt.date = TODAY, body: str = "Text.\n") -> None:
        path = self.knowledge / name
        path.parent.mkdir(parents=True, exist_ok=True)
        front = f"---\nsummary: About {path.stem}\nkind: {kind}\nverified: {verified}\nverify: a command\n---\n\n"
        path.write_text(front + body, encoding="utf-8", newline="\n")

    def run_index(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.knowledge / "index.py"), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            env=ISOLATED,
        )

    def test_indexes_are_written_once_and_then_up_to_date(self) -> None:
        self.entry("infra/database.md")
        self.assertEqual(self.run_index().returncode, 1)
        top = (self.knowledge / "INDEX.md").read_text(encoding="utf-8")
        group = (self.knowledge / "infra" / "INDEX.md").read_text(encoding="utf-8")
        self.assertIn("infra", top)
        self.assertIn("(fact, verified", group)
        self.assertIn("About database", group)
        self.assertEqual(self.run_index().returncode, 0)
        self.assertEqual(self.run_index("--check").returncode, 0)

    def test_check_writes_nothing(self) -> None:
        self.entry("infra/database.md")
        self.assertEqual(self.run_index("--check").returncode, 1)
        self.assertFalse((self.knowledge / "INDEX.md").exists())

    def test_secret_is_refused_without_its_value(self) -> None:
        token = "ghp_" + "a1B2c3D4e5" * 4
        self.entry("infra/token.md", body=f"The token is {token}\n")
        result = self.run_index()
        self.assertEqual(result.returncode, 1)
        self.assertIn("looks like a GitHub token", result.stderr)
        self.assertNotIn(token, result.stdout + result.stderr)

    def test_allowlisted_line_passes(self) -> None:
        self.entry("infra/example.md", body="An example: ghp_" + "x1Y2" * 9 + " pragma: allowlist secret\n")
        self.run_index()
        self.assertEqual(self.run_index().returncode, 0)

    def test_home_path_and_bad_frontmatter_are_refused(self) -> None:
        self.entry("infra/path.md", body="The key is in /home/someone/.ssh\n")
        self.entry("infra/kind.md", kind="opinion")
        result = self.run_index()
        self.assertEqual(result.returncode, 1)
        self.assertIn("path on one person's machine", result.stderr)
        self.assertIn("`kind: opinion` is none of", result.stderr)

    def test_where_a_secret_is_kept_is_no_secret(self) -> None:
        self.entry(
            "infra/secrets.md",
            body=(
                "password: kv/data/billing/prod/db\n"
                "DSN=postgresql://<user>:<password>@db.example.com:5432/app\n"
                "dsn: postgresql://app@db.example.com:5432/app\n"
            ),
        )
        self.run_index()
        result = self.run_index()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_password_value_and_credentials_in_a_url_are_refused(self) -> None:
        self.entry("infra/a.md", body="password: Xk9mQ2vL7pR4tZ\n")
        self.entry("infra/b.md", body="postgresql://app:Xk9mQ2vL7pR4@db.example.com/app\n")
        err = self.run_index().stderr
        self.assertIn("infra/a.md: line 8 looks like a secret assigned to a name", err)
        self.assertIn("infra/b.md: line 8 looks like credentials in a URL", err)

    def test_future_date_is_refused_and_today_is_not(self) -> None:
        self.entry("infra/future.md", verified=TODAY + dt.timedelta(days=1))
        self.entry("infra/today.md")
        err = self.run_index().stderr
        self.assertIn("infra/future.md: `verified:", err)
        self.assertNotIn("infra/today.md:", err)

    def test_broken_link_is_refused_and_root_links_resolve(self) -> None:
        (self.repo / "docs").mkdir()
        (self.repo / "docs" / "a.md").write_text("a\n", encoding="utf-8")
        self.entry("infra/links.md", body="[ok](/docs/a.md) [ok](../../../docs/a.md) [gone](../../../docs/b.md)\n")
        err = self.run_index().stderr
        self.assertIn("the link to `../../../docs/b.md` leads nowhere", err)
        self.assertNotIn("docs/a.md` leads nowhere", err)

    def test_index_of_an_emptied_group_is_removed(self) -> None:
        self.entry("infra/database.md")
        self.run_index()
        (self.knowledge / "infra" / "database.md").unlink()
        self.assertEqual(self.run_index().returncode, 1)
        self.assertFalse((self.knowledge / "infra" / "INDEX.md").exists())

    def test_too_deep_entry_is_refused(self) -> None:
        self.entry("infra/db/postgres.md")
        self.assertIn("too deep", self.run_index().stderr)

    def test_stale_names_entries_past_their_term(self) -> None:
        self.entry("work/migration.md", kind="state", verified=TODAY - dt.timedelta(days=20))
        self.entry("work/archive/done.md", kind="state", verified=TODAY - dt.timedelta(days=200))
        self.entry("infra/database.md", verified=TODAY - dt.timedelta(days=20))
        out = self.run_index("--stale").stdout
        self.assertIn("work/migration.md: verified 20 days ago", out)
        self.assertNotIn("done.md", out)
        self.assertNotIn("database.md", out)
        narrowed = self.run_index("--stale", ".agents/knowledge/infra").stdout
        self.assertEqual(narrowed.strip(), "No entry is due for verification.")

    def test_local_file_is_in_the_main_clone_from_a_worktree_too(self) -> None:
        out = self.run_index("--local").stdout.strip()
        self.assertEqual(Path(out).resolve(), (self.knowledge / "local.md").resolve())
        git = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run([*git, "add", "-A"], cwd=self.repo, check=True, env=ISOLATED)
        subprocess.run([*git, "commit", "-q", "-m", "init"], cwd=self.repo, check=True, env=ISOLATED)
        tree = Path(self.tmp.name) / "tree"
        subprocess.run(["git", "worktree", "add", "-q", str(tree)], cwd=self.repo, check=True, env=ISOLATED)
        result = subprocess.run(
            [sys.executable, str(tree / ".agents" / "knowledge" / "index.py"), "--local"],
            cwd=tree,
            capture_output=True,
            text=True,
            env=ISOLATED,
        )
        self.assertEqual(Path(result.stdout.strip()).resolve(), (self.knowledge / "local.md").resolve())


if __name__ == "__main__":
    unittest.main()
