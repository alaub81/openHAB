"""Run pinned source linters on public repository inputs only."""

import shutil
import subprocess
import sys
from pathlib import Path

from lint import ROOT, project_files
from source_checks import hygiene, is_text, markdown_links, markdown_examples


def main():
    files = [Path(name) for name in project_files()]
    failures = []
    for path in files:
        if is_text(path):
            text = (ROOT / path).read_bytes().decode("utf-8")
            failures.extend(f"{path}: {error}" for error in hygiene(text))
        if path.suffix == ".md":
            failures.extend(f"{path}: {error}" for error in markdown_links(ROOT / path, ROOT))
            failures.extend(
                f"{path}: {error}" for error in markdown_examples((ROOT / path).read_text())
            )
    for failure in failures:
        print("FAIL " + failure)
    commands = []
    python = [str(p) for p in files if p.suffix == ".py"]
    shell = [str(p) for p in files if p.suffix == ".sh"]
    javascript = [str(p) for p in files if p.suffix in {".js", ".cjs"}]
    commands.extend(
        [
            [sys.executable, "-m", "ruff", "check", "--config", "ruff.toml", "--no-cache", *python],
            [
                sys.executable,
                "-m",
                "ruff",
                "format",
                "--config",
                "ruff.toml",
                "--no-cache",
                "--check",
                *python,
            ],
            ["shellcheck", "--external-sources", "--", *shell],
            ["actionlint", "-color"],
        ]
    )
    for name in javascript:
        commands.append(["node", "--check", name])
    for command in commands:
        if not shutil.which(command[0]):
            print("FAIL Missing dependency: " + command[0], file=sys.stderr)
            return 1
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            failures.append(command[0])
    if failures:
        return 1
    print(
        "PASS Source hygiene, local Markdown links, Ruff, ShellCheck, Actionlint and JavaScript syntax"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
