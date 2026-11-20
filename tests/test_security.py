"""Exercise fail-closed scan orchestration with synthetic reports and Git history."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ImageGateTests(unittest.TestCase):
    def test_complete_evidence_and_fixable_gate_with_continued_scanning(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            binary = work / "trivy"
            binary.write_text(
                f"#!{sys.executable}\n"
                + r"""
import json, os, pathlib, sys
args = sys.argv[1:]
with open(os.environ['COMMAND_LOG'], 'a') as output:
    output.write(json.dumps(args) + '\n')
target = pathlib.Path(args[args.index('--output') + 1]) if '--output' in args else None
if args[0] == 'image':
    if args[-1] == 'broken:test': sys.exit(1)
    target.write_text(pathlib.Path(os.environ['FIXTURE']).read_text())
else:
    report = json.loads(pathlib.Path(args[-1]).read_text())
    findings = report['Results'][0]['Vulnerabilities']
    if target:
        target.write_text(json.dumps({'runs':[{'results':findings}]}))
    elif any(v['Severity'] in ('HIGH','CRITICAL') for v in findings):
        sys.exit(1)
"""
            )
            binary.chmod(0o755)
            fixture = work / "fixture.json"
            log = work / "commands.jsonl"
            raw = {
                "SchemaVersion": 2,
                "ArtifactName": "synthetic",
                "Results": [
                    {
                        "Vulnerabilities": [
                            {"Severity": "CRITICAL", "FixedVersion": ""},
                            {"Severity": "LOW", "FixedVersion": "1.2"},
                        ]
                    }
                ],
            }
            env = dict(
                os.environ,
                PATH=f"{work}:{os.environ['PATH']}",
                FIXTURE=str(fixture),
                COMMAND_LOG=str(log),
                SCAN_CATEGORY="amd64",
            )
            for fixed_high, expected in ((False, 0), (True, 1)):
                fixture_data = json.loads(json.dumps(raw))
                if fixed_high:
                    fixture_data["Results"][0]["Vulnerabilities"].append(
                        {"Severity": "HIGH", "FixedVersion": "2.1"}
                    )
                fixture.write_text(json.dumps(fixture_data))
                reports = work / f"reports-{fixed_high}"
                result = subprocess.run(
                    [
                        "bash",
                        str(ROOT / "tests/scan-images.sh"),
                        str(reports),
                        "first=synthetic:test",
                        "second=synthetic:test",
                    ],
                    env=env,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, expected, result.stderr)
                self.assertEqual(json.loads((reports / "first.json").read_text()), fixture_data)
                sarif = json.loads((reports / "second.sarif").read_text())
                self.assertEqual(len(sarif["runs"][0]["results"]), 3 if fixed_high else 2)
                self.assertEqual(sarif["runs"][0]["automationDetails"]["id"], "second-amd64/")
                gate = json.loads((reports / "first.gate.json").read_text())
                self.assertTrue(
                    all(v["FixedVersion"] for v in gate["Results"][0]["Vulnerabilities"])
                )
            reports = work / "scan-error"
            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "tests/scan-images.sh"),
                    str(reports),
                    "broken=broken:test",
                    "last=synthetic:test",
                ],
                env=env,
                check=False,
            )
            self.assertEqual(result.returncode, 1)
            self.assertTrue((reports / "last.sarif").exists())
            commands = [json.loads(line) for line in log.read_text().splitlines()]
            for args in commands:
                self.assertIn("/dev/null", args)
                if args[0] == "image":
                    self.assertIn("--ignore-unfixed=false", args)
                    self.assertIn("UNKNOWN,LOW,MEDIUM,HIGH,CRITICAL", args)


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
