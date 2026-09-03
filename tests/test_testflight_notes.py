#!/usr/bin/env python3
"""Behavior tests for the TestFlight Git evidence collector."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "testflight-notes" / "scripts" / "collect-evidence.sh"


class EvidenceCollectorTests(unittest.TestCase):
    def git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def init_repo(self, directory: Path) -> Path:
        repo = directory / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "config", "user.name", "Test User")
        self.git(repo, "config", "user.email", "test@example.com")
        self.git(repo, "config", "core.hooksPath", "/dev/null")
        return repo

    def commit_file(self, repo: Path, relative: str, contents: str, message: str) -> str:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        self.git(repo, "add", "--", relative)
        self.git(repo, "commit", "-q", "-m", message)
        return self.git(repo, "rev-parse", "HEAD")

    def collect(
        self,
        repo: Path,
        *args: str,
        temp_root: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        environment = os.environ.copy()
        if temp_root is not None:
            environment["TMPDIR"] = str(temp_root)
        return subprocess.run(
            ["bash", str(SCRIPT), "--repo", str(repo), *args],
            capture_output=True,
            text=True,
            env=environment,
        )

    def successful_evidence(self, result: subprocess.CompletedProcess[str]) -> Path:
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = Path(result.stdout.strip())
        self.assertTrue(evidence.is_dir())
        self.addCleanup(shutil.rmtree, evidence, True)
        return evidence

    def test_rejects_shallow_history_without_leaving_a_partial_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = self.init_repo(root)
            self.commit_file(source, "one.txt", "one\n", "one")
            self.commit_file(source, "two.txt", "two\n", "two")
            shallow = root / "shallow"
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", source.as_uri(), str(shallow)],
                check=True,
            )
            temp_root = root / "tmp"
            temp_root.mkdir()

            result = self.collect(shallow, temp_root=temp_root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("shallow", result.stderr.lower())
            self.assertEqual(list(temp_root.glob("testflight-evidence.*")), [])

    def test_initializes_ref_timeframe_and_default_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self.init_repo(root)
            tagged = self.commit_file(repo, "base.txt", "base\n", "base")
            self.git(repo, "tag", "build-1", tagged)
            head = self.commit_file(repo, "next.txt", "next\n", "next")

            default_evidence = self.successful_evidence(self.collect(repo))
            ref_evidence = self.successful_evidence(
                self.collect(repo, "--start", "build-1")
            )
            cutoff = int(self.git(repo, "show", "-s", "--format=%ct", head)) - 1
            time_evidence = self.successful_evidence(
                self.collect(repo, "--cutoff-epoch", str(cutoff))
            )

            self.assertEqual(
                (default_evidence / "selection").read_text(encoding="utf-8"),
                f"start\trefs/tags/build-1\t{tagged}\n",
            )
            self.assertEqual(
                (ref_evidence / "selection").read_text(encoding="utf-8"),
                f"start\trefs/tags/build-1\t{tagged}\n",
            )
            self.assertEqual(
                (time_evidence / "selection").read_text(encoding="utf-8"),
                f"cutoff\t{cutoff}\n",
            )
            self.assertIn(head, (time_evidence / "oids").read_text(encoding="ascii"))

            no_tag = root / "no-tag"
            no_tag.mkdir()
            self.git(no_tag, "init", "-q", "-b", "main")
            self.git(no_tag, "config", "user.name", "Test User")
            self.git(no_tag, "config", "user.email", "test@example.com")
            self.commit_file(no_tag, "only.txt", "only\n", "only")
            no_tag_evidence = self.successful_evidence(self.collect(no_tag))
            self.assertTrue(
                (no_tag_evidence / "selection")
                .read_text(encoding="utf-8")
                .startswith("cutoff\t")
            )

    def test_merge_commit_paths_compare_with_first_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            self.commit_file(repo, "base.txt", "base\n", "base")
            self.git(repo, "checkout", "-q", "-b", "feature")
            self.commit_file(repo, "feature.txt", "feature\n", "feature")
            self.git(repo, "checkout", "-q", "main")
            main_tip = self.commit_file(repo, "main.txt", "main\n", "main")
            self.git(repo, "merge", "-q", "--no-ff", "feature", "-m", "merge feature")
            merge_oid = self.git(repo, "rev-parse", "HEAD")

            evidence = self.successful_evidence(
                self.collect(repo, "--start", main_tip)
            )

            paths = (evidence / "commits" / merge_oid / "paths.z").read_bytes()
            self.assertIn(b"feature.txt\0", paths)

    def test_git_read_failure_aborts_and_removes_partial_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self.init_repo(root)
            base = self.commit_file(repo, "base.txt", "base\n", "base")
            self.commit_file(repo, "broken.txt", "missing blob\n", "broken")
            blob = self.git(repo, "rev-parse", "HEAD:broken.txt")
            object_path = repo / ".git" / "objects" / blob[:2] / blob[2:]
            object_path.unlink()
            temp_root = root / "tmp"
            temp_root.mkdir()

            result = self.collect(
                repo,
                "--start",
                base,
                temp_root=temp_root,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("evidence collection failed", result.stderr.lower())
            self.assertEqual(list(temp_root.glob("testflight-evidence.*")), [])

    def test_nul_paths_are_bound_to_their_literal_patches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            base = self.commit_file(repo, "base.txt", "base\n", "base")
            odd_path = "-odd name\npart.txt"
            (repo / odd_path).write_text("odd-only-marker\n", encoding="utf-8")
            (repo / "other.txt").write_text("other-only-marker\n", encoding="utf-8")
            self.git(repo, "add", "--", odd_path, "other.txt")
            self.git(repo, "commit", "-q", "-m", "odd paths")
            head = self.git(repo, "rev-parse", "HEAD")

            evidence = self.successful_evidence(
                self.collect(repo, "--start", base)
            )
            commit_dir = evidence / "commits" / head
            paths = [item for item in (commit_dir / "paths.z").read_bytes().split(b"\0") if item]

            self.assertIn(odd_path.encode(), paths)
            odd_patch: bytes | None = None
            for path_file in commit_dir.glob("path-*"):
                if path_file.read_bytes() == odd_path.encode():
                    odd_patch = (commit_dir / path_file.name.replace("path-", "patch-")).read_bytes()
                    break
            self.assertIsNotNone(odd_patch)
            self.assertIn(b"odd-only-marker", odd_patch)
            self.assertNotIn(b"other-only-marker", odd_patch)

    def test_default_selection_propagates_corrupt_tag_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self.init_repo(root)
            self.commit_file(repo, "base.txt", "base\n", "base")
            self.git(repo, "tag", "-a", "build-1", "-m", "build")
            tag_object = self.git(repo, "rev-parse", "build-1^{tag}")
            (repo / ".git" / "objects" / tag_object[:2] / tag_object[2:]).unlink()
            temp_root = root / "tmp"
            temp_root.mkdir()

            result = self.collect(repo, temp_root=temp_root)

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(list(temp_root.glob("testflight-evidence.*")), [])

    def test_default_selection_ignores_valid_noncommit_tags(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            self.commit_file(repo, "base.txt", "base\n", "base")
            blob = self.git(repo, "rev-parse", "HEAD:base.txt")
            tree = self.git(repo, "rev-parse", "HEAD^{tree}")
            self.git(repo, "tag", "blob-build", blob)
            self.git(repo, "tag", "tree-build", tree)
            self.commit_file(repo, "next.txt", "next\n", "next")

            evidence = self.successful_evidence(self.collect(repo))

            self.assertTrue(
                (evidence / "selection").read_text(encoding="utf-8").startswith("cutoff\t")
            )

    def test_default_selection_uses_frozen_tags_after_live_move(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repo = self.init_repo(root)
            base = self.commit_file(repo, "base.txt", "base\n", "base")
            self.git(repo, "tag", "build-1", base)
            head = self.commit_file(repo, "next.txt", "next\n", "next")
            temp_root = root / "tmp"
            temp_root.mkdir()
            bin_path = root / "bin"
            bin_path.mkdir()
            marker = root / "moved"
            real_git = shutil.which("git")
            self.assertIsNotNone(real_git)
            wrapper = bin_path / "git"
            wrapper.write_text(
                "#!/usr/bin/env bash\n"
                "set -euo pipefail\n"
                "if [[ $* == *' describe --tags --abbrev=0 '* && ! -e $RACE_MARKER ]]; then\n"
                "  : > \"$RACE_MARKER\"\n"
                "  \"$REAL_GIT\" -C \"$RACE_REPO\" tag -f build-1 \"$RACE_NEW_OID\" >/dev/null\n"
                "fi\n"
                "exec \"$REAL_GIT\" \"$@\"\n"
            )
            wrapper.chmod(wrapper.stat().st_mode | 0o100)
            environment = os.environ.copy()
            environment["PATH"] = f"{bin_path}:{environment['PATH']}"
            environment["TMPDIR"] = str(temp_root)
            environment["REAL_GIT"] = real_git
            environment["RACE_MARKER"] = str(marker)
            environment["RACE_REPO"] = str(repo)
            environment["RACE_NEW_OID"] = head

            result = subprocess.run(
                ["bash", str(SCRIPT), "--repo", str(repo)],
                capture_output=True,
                text=True,
                env=environment,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = Path(result.stdout.strip())
            self.addCleanup(shutil.rmtree, evidence, True)
            self.assertEqual(
                (evidence / "selection").read_text(encoding="utf-8"),
                f"start\trefs/tags/build-1\t{base}\n",
            )
            self.assertEqual(self.git(repo, "rev-parse", "build-1"), head)

    def test_commit_messages_are_normalized_to_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            base = self.commit_file(repo, "base.txt", "base\n", "base")
            (repo / "legacy.txt").write_text("legacy\n", encoding="utf-8")
            self.git(repo, "add", "--", "legacy.txt")
            self.git(repo, "config", "i18n.commitEncoding", "ISO-8859-1")
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-F", "-"],
                input=b"caf\xe9\n",
                check=True,
            )
            head = self.git(repo, "rev-parse", "HEAD")

            evidence = self.successful_evidence(self.collect(repo, "--start", base))
            message = (evidence / "commits" / head / "message.z").read_bytes()

            self.assertIn("café".encode("utf-8"), message)
            self.assertNotIn(b"caf\xe9", message)

    def test_root_diff_does_not_write_the_empty_tree_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            self.commit_file(repo, "root.txt", "root\n", "root")
            before = self.git(repo, "count-objects", "-v")

            self.successful_evidence(self.collect(repo, "--cutoff-epoch", "1"))

            self.assertEqual(self.git(repo, "count-objects", "-v"), before)

    def test_message_records_end_with_nul_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            base = self.commit_file(repo, "base.txt", "base\n", "base")
            head = self.commit_file(repo, "next.txt", "next\n", "subject\n\nbody")

            evidence = self.successful_evidence(self.collect(repo, "--start", base))
            message = (evidence / "commits" / head / "message.z").read_bytes()

            self.assertTrue(message.endswith(b"\0"))
            self.assertEqual(len(message.split(b"\0")), 4)

    def test_rename_ledger_retains_both_paths_and_one_rename_patch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            old_path = "ios/Feature.txt"
            new_path = "macos/Feature.txt"
            base = self.commit_file(repo, old_path, "feature\n", "base")
            (repo / new_path).parent.mkdir()
            self.git(repo, "mv", old_path, new_path)
            self.git(repo, "commit", "-q", "-m", "move feature")
            head = self.git(repo, "rev-parse", "HEAD")

            evidence = self.successful_evidence(self.collect(repo, "--start", base))
            commit_dir = evidence / "commits" / head

            changes = (commit_dir / "changes.z").read_bytes().split(b"\0")
            self.assertTrue(changes[0].startswith(b"R"))
            self.assertEqual(changes[1:3], [old_path.encode(), new_path.encode()])
            patch = (commit_dir / "patch-000001").read_bytes()
            self.assertIn(f"rename from {old_path}".encode(), patch)
            self.assertIn(f"rename to {new_path}".encode(), patch)

    def test_submodule_changes_ignore_hiding_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            self.commit_file(repo, "base.txt", "base\n", "base")
            first = "1" * 40
            second = "2" * 40
            self.git(repo, "update-index", "--add", "--cacheinfo", f"160000,{first},vendor/sub")
            self.git(repo, "commit", "-q", "-m", "add submodule pointer")
            base = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "update-index", "--cacheinfo", f"160000,{second},vendor/sub")
            self.git(repo, "commit", "-q", "-m", "update submodule pointer")
            head = self.git(repo, "rev-parse", "HEAD")
            self.git(repo, "config", "diff.ignoreSubmodules", "all")

            evidence = self.successful_evidence(self.collect(repo, "--start", base))

            paths = (evidence / "commits" / head / "paths.z").read_bytes()
            self.assertIn(b"vendor/sub\0", paths)

    def test_patch_attributes_come_only_from_the_pinned_head(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = self.init_repo(Path(directory))
            base = self.commit_file(repo, "visible.txt", "before\n", "base")
            head = self.commit_file(repo, "visible.txt", "after-marker\n", "change")
            (repo / ".gitattributes").write_text("*.txt binary\n", encoding="utf-8")
            info_attributes = repo / ".git" / "info" / "attributes"
            info_attributes.write_text("*.txt binary\n", encoding="utf-8")

            evidence = self.successful_evidence(self.collect(repo, "--start", base))
            patch = next((evidence / "commits" / head).glob("patch-*")).read_bytes()

            self.assertIn(b"after-marker", patch)
            self.assertNotIn(b"Binary files", patch)


if __name__ == "__main__":
    unittest.main()
