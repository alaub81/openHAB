"""Validate Renovate and extract real public dependencies in an isolated checkout."""

import os
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from lint import ROOT, project_files

IMAGE = "ghcr.io/renovatebot/renovate:44.252.8"


def main():
    with tempfile.TemporaryDirectory(prefix="openhab-renovate-") as directory:
        stage = Path(directory)
        for name in project_files():
            if name in {
                "renovate.json",
                "lint-tools.json",
                ".node-version",
                ".env.advanced.example",
                "tests/dependency-check.py",
                "tools/requirements.txt",
            } or (
                name.startswith((".github/workflows/", "tests/requirements-", "docker-compose"))
                and name.endswith((".yml", ".txt", ".example"))
            ):
                target = stage / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / name, target)
        for args in (
            ["init", "--quiet"],
            ["add", "."],
            [
                "-c",
                "user.name=Dependency test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "Public dependency fixtures",
            ],
        ):
            subprocess.run(["git", *args], cwd=stage, check=True)
        tracked = subprocess.check_output(["git", "ls-files"], cwd=stage, text=True).splitlines()
        if ".env.advanced.example" not in tracked:
            raise RuntimeError("Public Advanced template is missing from the Git fixture")
        base = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "-v",
            f"{stage}:/work",
            "-w",
            "/work",
            "-e",
            "HOME=/tmp",
            "-e",
            "RENOVATE_BASE_DIR=/tmp/renovate",
            "-e",
            "LOG_LEVEL=debug",
        ]
        subprocess.run(
            [
                *base,
                "--entrypoint",
                "renovate-config-validator",
                IMAGE,
                "--strict",
                "renovate.json",
            ],
            check=True,
        )
        extraction = subprocess.run(
            [
                *base,
                "-e",
                "RENOVATE_CONFIG_FILE=/work/renovate.json",
                "--entrypoint",
                "renovate",
                IMAGE,
                "--platform=local",
                "--dry-run=extract",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if extraction.returncode:
            print(extraction.stdout)
            print(extraction.stderr)
            extraction.check_returncode()
        output = extraction.stdout + extraction.stderr
        marker = '"packageFiles":'
        if marker not in output:
            raise RuntimeError("Renovate did not report extracted dependencies")
        files, _ = json.JSONDecoder().raw_decode(output.split(marker, 1)[1].lstrip())
        dependencies = [
            dict(dep, packageFile=entry["packageFile"])
            for entries in files.values()
            for entry in entries
            for dep in entry["deps"]
        ]
        expected = {
            (".env.advanced.example", "ghcr.io/alaub81/sma-mqtt-bridge"),
            (".env.advanced.example", "ghcr.io/alaub81/bmw-mqtt-bridge"),
            ("tools/requirements.txt", "requests"),
        }
        found = {
            (d["packageFile"], d.get("depName")) for d in dependencies if not d.get("skipReason")
        }
        if expected - found:
            print(output)
            for dep in dependencies:
                if dep["packageFile"] in {path for path, _ in expected}:
                    print("Extracted dependency diagnostic:", dep)
            raise RuntimeError(
                "Renovate skipped required dependencies: " + str(sorted(expected - found))
            )
        reported = set()
        for dep in dependencies:
            key = (dep["packageFile"], dep.get("depName"))
            if key in expected and key not in reported:
                reported.add(key)
                print(
                    f"PASS Renovate extraction: {dep['packageFile']}: {dep['depName']} {dep['currentValue']}"
                )


if __name__ == "__main__":
    main()
