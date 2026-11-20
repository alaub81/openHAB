"""Skip behavior tests only for a known, exclusively documentary diff."""

import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def needs_tests(files):
    if not files:
        return True
    return any(not (name.endswith(".md") or name == "LICENSE") for name in files)


def needs_dependency_check(files):
    # Dependency declarations and their extraction rules are checked together.
    # Unknown inputs conservatively keep the validator enabled.
    if not files:
        return True
    known_sources = (
        "data/openhab/conf/",
        "scripts/",
        "certs/",
        "tools/state-alarms/",
        "tools/humidity-alarms/",
        "tools/battery-widget/",
        "tools/humidity-widget/",
        "tools/window-widget/",
        "tools/dwd-messages/",
        "tools/heatpump-daily/",
    )
    return any(
        not (name.endswith(".md") or name == "LICENSE" or name.startswith(known_sources))
        for name in files
    )


def changed_files(base):
    if not re.fullmatch(r"[0-9a-fA-F]{40,64}", base or "") or set(base) == {"0"}:
        return None
    try:
        result = subprocess.run(
            ["git", "diff", "--no-renames", "--name-only", "-z", base, "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [name for name in result.stdout.decode().split("\0") if name]


def main():
    files = changed_files(os.environ.get("BASE_SHA"))
    required = needs_tests(files)
    value = "true" if required else "false"
    print(f"Behavior tests required: {value}; repository lint always runs")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"tests={value}\n")
            output.write(f"dependencies={'true' if needs_dependency_check(files) else 'false'}\n")


if __name__ == "__main__":
    main()
