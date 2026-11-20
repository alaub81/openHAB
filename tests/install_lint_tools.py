#!/usr/bin/env python3
"""Install pinned native linters into .lint-tools without changing system packages."""

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / ".lint-tools"
BIN = TOOLS / "bin"


def has_version(binary, specification):
    try:
        result = subprocess.run(
            [str(binary), specification.get("versionFlag", "--version")],
            text=True,
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return bool(
        re.search(
            r"(?<![\d.])" + re.escape(specification["version"]) + r"(?![\d.])",
            result.stdout + result.stderr,
        )
    )


def download(url, checksum, destination):
    print(f"Downloading {destination.name}", flush=True)
    urllib.request.urlretrieve(url, destination)
    if hashlib.sha256(destination.read_bytes()).hexdigest() != checksum:
        destination.unlink()
        raise ValueError(f"Checksum mismatch: {url}")


def tool_version(specification):
    """Reject partially updated manifests before installing any platform asset."""
    versions = {asset["version"] for asset in specification["assets"].values()}
    if len(versions) != 1:
        raise ValueError(f"Expected one version for all assets of {specification['repository']}")
    tag = versions.pop()
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError(f"Invalid release tag: {tag}")
    return tag[1:]


def install_binary(name, specification, target_platform):
    version = tool_version(specification)
    specification = {**specification, "version": version}
    destination = BIN / name
    if destination.exists() and has_version(destination, specification):
        return
    system_binary = shutil.which(name)
    if system_binary and has_version(system_binary, specification):
        # Reuse a matching system installation, including Homebrew on macOS.
        if destination.is_symlink():
            destination.unlink()
        shutil.copyfile(system_binary, destination)
    else:
        asset = specification["assets"].get(target_platform)
        if asset is None:
            raise ValueError(
                f"Install {name} {specification['version']} on PATH first; no asset for {target_platform}"
            )
        filename = asset["filenameTemplate"].format(version=version)
        checksum = asset["sha256"]
        release_base = f"https://github.com/{specification['repository']}/releases/download/{asset['version']}/"
        archive_path = TOOLS / filename
        download(release_base + filename, checksum, archive_path)
        if filename.endswith(".tar.gz"):
            with tarfile.open(archive_path) as archive:
                candidates = [
                    m for m in archive.getmembers() if m.isfile() and Path(m.name).name == name
                ]
                if len(candidates) != 1:
                    raise ValueError(f"Expected one {name} executable in {filename}")
                with archive.extractfile(candidates[0]) as binary:
                    destination.write_bytes(binary.read())
        else:
            shutil.copyfile(archive_path, destination)
    destination.chmod(0o755)
    if not has_version(destination, specification):
        raise ValueError(f"Unexpected {name} version")


def main():
    BIN.mkdir(parents=True, exist_ok=True)
    machine = {"aarch64": "arm64", "AMD64": "x86_64"}.get(platform.machine(), platform.machine())
    target_platform = f"{sys.platform}-{machine}"
    specifications = json.loads((ROOT / "lint-tools.json").read_text())
    # Validate every tool before changing any installed binary.
    for specification in specifications.values():
        tool_version(specification)
    names = sys.argv[1:] or ["shellcheck", "actionlint"]
    if any(name not in specifications for name in names):
        raise ValueError("Unknown tool requested")
    for name in names:
        install_binary(name, specifications[name], target_platform)
        print(f"Ready: {name} {tool_version(specifications[name])}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, tarfile.TarError, subprocess.CalledProcessError) as error:
        print(f"Lint tool installation failed: {error}", file=sys.stderr)
        sys.exit(1)
