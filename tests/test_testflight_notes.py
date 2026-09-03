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


if __name__ == "__main__":
    unittest.main()
