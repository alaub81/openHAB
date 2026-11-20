"""Exercise secret scan ranges and failures with isolated Git history."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SecretRangeTests(unittest.TestCase):
    def test_ranges_fallback_and_scanner_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tools").mkdir()
            (root / "tests").mkdir()
            (root / ".lint-tools/bin").mkdir(parents=True)
            shutil.copyfile(ROOT / "tools/secret-check.sh", root / "tools/secret-check.sh")
            (root / "tests/install_lint_tools.py").write_text("# Test installer double\n")
            scanner = root / ".lint-tools/bin/gitleaks"
            scanner.write_text(
                f"#!{sys.executable}\nimport os,json,sys\n"
                "print(json.dumps(sys.argv[1:]))\n"
                "sys.exit(int(os.environ.get('SCAN_FAILURE','0')))\n"
            )
            scanner.chmod(0o755)

            def git(*args):
                return subprocess.check_output(["git", *args], cwd=root).decode().strip()

            git("init", "--quiet")
            git("add", ".")
            git(
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "fixture",
            )
            base = git("rev-parse", "HEAD")

            def run(**values):
                env = {k: v for k, v in os.environ.items() if k not in {"BASE_SHA", "HEAD_SHA"}}
                return subprocess.run(
                    ["bash", "tools/secret-check.sh"],
                    cwd=root,
                    env=dict(env, **values),
                    capture_output=True,
                    text=True,
                    check=False,
                )

            scoped = run(BASE_SHA=base)
            self.assertEqual(scoped.returncode, 0, scoped.stderr)
            self.assertIn(f"--log-opts={base}..HEAD", json.loads(scoped.stdout))
            for value in ("", "0" * 40, "f" * 40, "--help"):
                result = run(BASE_SHA=value)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(any(a.startswith("--log-opts") for a in json.loads(result.stdout)))
            self.assertEqual(run(BASE_SHA=base, SCAN_FAILURE="1").returncode, 1)
            (root / ".git/shallow").write_text(base + "\n")
            self.assertEqual(run(BASE_SHA=base).returncode, 1)


if __name__ == "__main__":
    unittest.main()
