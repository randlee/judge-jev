"""judge_jev_paths: the repository name and the central per-user log root."""
import datetime
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from clock_support import FIXED_UTC, utc_clock

from jev_support import SCRIPTS  # noqa: F401 - puts the installed scripts on sys.path
import judge_jev_paths as paths  # noqa: E402


class RepositoryNameTests(unittest.TestCase):
    def setUp(self):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        self.d = Path(td.name).resolve()
        self.home = self.d / "home"
        self.home.mkdir()

    def test_a_main_checkout_is_named_by_its_folder_from_any_depth(self):
        repo = self.d / "sc-runtime"
        (repo / ".git").mkdir(parents=True)
        (repo / "docs" / "deep").mkdir(parents=True)
        self.assertEqual(paths.repository_name(repo, self.home), "sc-runtime")
        self.assertEqual(paths.repository_name(repo / "docs" / "deep", self.home), "sc-runtime")

    def test_a_linked_worktree_is_named_by_its_main_checkout(self):
        main, tree = self.d / "sc-runtime", self.d / "tmp" / "wt-req-0001"
        (main / ".git" / "worktrees" / "wt-req-0001").mkdir(parents=True)
        tree.mkdir(parents=True)
        (tree / ".git").write_text(f"gitdir: {main / '.git' / 'worktrees' / 'wt-req-0001'}\n", encoding="utf-8")
        self.assertEqual(paths.repository_name(tree, self.home), "sc-runtime")

    def test_no_repository_names_the_start_folder_and_unsafe_characters_become_underscores(self):
        plain = self.d / "my notes (v2)"
        plain.mkdir()
        self.assertEqual(paths.repository_name(plain, self.home), "my_notes__v2_")

    def test_an_unreadable_gitdir_pointer_falls_back_to_the_worktree_folder(self):
        tree = self.d / "odd"
        tree.mkdir()
        (tree / ".git").write_text("not a gitdir line\n", encoding="utf-8")
        self.assertEqual(paths.repository_name(tree, self.home), "odd")


class CentralLogRootTests(RepositoryNameTests):
    def test_the_root_is_home_judge_jev_repository_and_date(self):
        repo = self.d / "sc-runtime"
        (repo / ".git").mkdir(parents=True)
        day = datetime.date(2026, 11, 13)
        self.assertEqual(paths.central_log_root(repo, self.home, day), self.home / ".judge-jev" / "sc-runtime" / "2026-11-13")

    def test_the_default_date_is_today_in_utc(self):
        clock = utc_clock()
        with mock.patch.object(paths, "_dt", clock):
            root = paths.central_log_root(self.d, self.home)
        self.assertEqual(root.name, FIXED_UTC.date().isoformat())
        clock.datetime.now.assert_called_once_with(datetime.timezone.utc)


if __name__ == "__main__":
    unittest.main()
