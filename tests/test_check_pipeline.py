"""Check documentation links and conservative CI planning using temporary inputs."""

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from change_plan import changed_files, needs_tests, needs_dependency_check
from source_checks import hygiene, markdown_links, markdown_examples
from lint import ROOT, load_yaml


class ChangePlanTests(unittest.TestCase):
    def test_ci_required_rejects_failures_cancellations_and_unplanned_skips(self):
        workflow = load_yaml((ROOT / ".github/workflows/lint.yml").read_text())
        script = workflow["jobs"]["required"]["steps"][0]["run"]
        self.assertEqual(workflow["jobs"]["required"]["if"], "always()")
        for lint in ("success", "failure", "cancelled", "skipped"):
            for tests in ("success", "failure", "cancelled", "skipped"):
                for required in ("true", "false", ""):
                    with self.subTest(lint=lint, tests=tests, required=required):
                        result = subprocess.run(
                            ["bash", "-e", "-c", script],
                            check=False,
                            env={
                                "LINT_RESULT": lint,
                                "TEST_RESULT": tests,
                                "TESTS_REQUIRED": required,
                                "SECRET_RESULT": "success",
                            },
                        )
                        accepted = lint == "success" and (
                            (required == "true" and tests == "success")
                            or (required == "false" and tests == "skipped")
                        )
                        self.assertEqual(result.returncode == 0, accepted)

    def test_secret_job_cannot_fail_or_skip_silently(self):
        workflow = load_yaml((ROOT / ".github/workflows/lint.yml").read_text())
        script = workflow["jobs"]["required"]["steps"][0]["run"]
        for secret in ("success", "failure", "cancelled", "skipped"):
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                check=False,
                env={
                    "LINT_RESULT": "success",
                    "TEST_RESULT": "success",
                    "TESTS_REQUIRED": "true",
                    "SECRET_RESULT": secret,
                },
            )
            self.assertEqual(result.returncode == 0, secret == "success")

    def test_dependency_validation_covers_manifests_and_policies(self):
        for name in (
            "renovate.json",
            "docker-compose.yml",
            "tests/requirements-lint.txt",
            "lint-tools.json",
            ".github/dependabot.yml",
            ".node-version",
        ):
            self.assertTrue(needs_dependency_check([name]), name)
        self.assertFalse(needs_dependency_check(["README.md"]))

    def test_only_known_documentation_skips_behavior_tests(self):
        self.assertFalse(needs_tests(["README.md", "docs/setup.md", "LICENSE"]))
        for files in (
            None,
            [],
            ["new-file"],
            ["README.md", "tests/test_lint.py"],
            [".github/workflows/lint.yml"],
            ["docker-compose.yml"],
            ["data/openhab/conf/yaml/widgets/example.yml"],
            ["lint-tools.json"],
        ):
            with self.subTest(files=files):
                self.assertTrue(needs_tests(files))

    def test_missing_invalid_and_zero_bases_require_full_checks(self):
        for base in (None, "", "0" * 40, "--bad-option", "not-a-commit"):
            self.assertIsNone(changed_files(base))

    def test_unavailable_diff_requires_full_checks(self):
        with patch(
            "change_plan.subprocess.run", side_effect=subprocess.CalledProcessError(1, "git")
        ):
            self.assertTrue(needs_tests(changed_files("a" * 40)))

    def test_renames_include_both_paths_and_deleted_files_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root).decode().strip()

            git("init", "--quiet")
            (root / "runtime.js").write_text("// runtime\n")
            git("add", ".")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "initial",
            )
            base = git("rev-parse", "HEAD")
            git("mv", "runtime.js", "runtime.md")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "rename",
            )
            with patch("change_plan.ROOT", root):
                files = changed_files(base)
            self.assertEqual(set(files), {"runtime.js", "runtime.md"})
            self.assertTrue(needs_tests(files))


class SourceCheckTests(unittest.TestCase):
    def test_documented_commands_are_parsed_without_running_them(self):
        self.assertEqual(markdown_examples("```bash\nexit 99\n```\n"), [])
        for language, code in (
            ("bash", "if"),
            ("yaml", "key: 1\nkey: 2"),
            ("json", '{"key":1,"key":2}'),
            ("python", "def broken("),
        ):
            with self.subTest(language=language):
                self.assertTrue(markdown_examples(f"```{language}\n{code}\n```\n"))

    def test_hygiene_preserves_markdown_hard_breaks(self):
        self.assertEqual(hygiene("line  \nnext\n"), [])
        for text in ("no newline", "trailing \n", "tab\t\n", "crlf\r\n", "nul\0\n"):
            self.assertTrue(hygiene(text))

    def test_links_and_fragments_with_code_fences_and_reference_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target file.md"
            target.write_text("# A `heading`\n\n# A heading\n")
            source = root / "README.md"
            source.write_text(
                "[valid](target%20file.md#a-heading-1)\n"
                "[reference][target]\n\n[target]: <target file.md#a-heading>\n\n"
                "```md\n[example](absent.md)\n```\n"
            )
            self.assertEqual(markdown_links(source, root), [])
            source.write_text(
                "[bad](missing.md)\n[fragment](target%20file.md#absent)\n"
                "[escape](../private.md)\n[external](https://example.invalid/)\n"
            )
            errors = markdown_links(source, root)
            self.assertEqual(len(errors), 3)


if __name__ == "__main__":
    unittest.main()
