"""Validate Renovate and extract real public dependencies in an isolated checkout."""

import os
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
        subprocess.run(
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
            check=True,
        )


if __name__ == "__main__":
    main()
