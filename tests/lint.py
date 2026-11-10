#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Check repository syntax and configuration without executing application code."""

import ast
import copy
from itertools import combinations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
YAML_ROOT = Path("data/openhab/conf/yaml")
PROFILE_SERVICES = {
    "mqtt": {"mosquitto"},
    "influxdb": {"influxdb"},
    "grafana": {"grafana", "postgres", "renderer"},
}


class ConfigLoader(yaml.SafeLoader):
    """Keep on/off keys as strings, matching openHAB and Compose YAML semantics."""

    yaml_implicit_resolvers = copy.deepcopy(yaml.SafeLoader.yaml_implicit_resolvers)


for initial, resolvers in ConfigLoader.yaml_implicit_resolvers.items():
    ConfigLoader.yaml_implicit_resolvers[initial] = [
        entry for entry in resolvers if entry[0] != "tag:yaml.org,2002:bool"
    ]
ConfigLoader.add_implicit_resolver(
    "tag:yaml.org,2002:bool", re.compile(r"^(?:true|false)$", re.IGNORECASE), list("tTfF")
)


def unique_mapping(loader, node):
    """Reject duplicate keys before a parser silently overwrites their values."""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"duplicate YAML key at line {key_node.start_mark.line + 1}")
        result[key] = loader.construct_object(value_node)
    return result


ConfigLoader.add_constructor("tag:yaml.org,2002:map", unique_mapping)


def unique_json(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def load_yaml(text):
    return yaml.load(text, Loader=ConfigLoader)


def openhab_entities(name, document):
    """Validate the file-provider wrapper, not binding-specific configuration."""
    sections = {"widgets": "widgets", "block_libraries": "blocks", "things": "things", "pages": "pages"}
    section = sections.get(Path(name).parent.name)
    if section is None:
        raise ValueError("unsupported openHAB YAML directory")
    if not isinstance(document, dict) or type(document.get("version")) is not int or document["version"] != 1:
        raise ValueError("expected file-based YAML with version: 1")
    if set(document) != {"version", section} or not isinstance(document[section], dict) or not document[section]:
        raise ValueError(f"expected a nonempty {section}: map")
    for uid, entity in document[section].items():
        if not isinstance(uid, str) or not uid or not isinstance(entity, dict):
            raise ValueError("expected named entity definitions")
        if section in {"widgets", "pages", "blocks"}:
            if not isinstance(entity.get("component"), str) or not entity["component"]:
                raise ValueError("missing component")
        if section == "blocks" and entity["component"] != "BlockLibrary":
            raise ValueError("expected BlockLibrary component")
    return section, document[section]


def dotenv(text, public_credentials=None):
    """Require placeholder credentials, with explicitly selected public examples."""
    values = {}
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", line)
        if not match or match[1] in values:
            raise ValueError(f"expected unique KEY=value assignment at line {number}")
        key, value = match.groups()
        values[key] = value
        if re.search(r"PASSWORD|PASSWD|TOKEN|SECRET|API_KEY", key, re.IGNORECASE):
            if not re.fullmatch(r"CHANGE_ME_[A-Z0-9_]+", value) and value != (public_credentials or {}).get(key):
                raise ValueError(f"{key}: use a CHANGE_ME_ credential placeholder")
    return values


def project_files():
    result = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    )
    return sorted({
        name for name in result.decode().split("\0")
        if name and name != ".env" and (ROOT / name).is_file()
    })


def main():
    if len(sys.argv) != 1:
        print("Usage: ./tests/linter-check.sh", file=sys.stderr)
        return 2
    failures = []
    counts = {}
    active_ids = set()
    env_values = None

    def fail(name, message):
        failures.append(f"{name}: {message}")

    for name in project_files():
        path = ROOT / name
        suffix = path.suffix
        yaml_file = name.endswith((".yml", ".yaml", ".yml.example", ".yaml.example"))
        text_file = yaml_file or suffix in {".md", ".py", ".sh", ".js", ".json", ".conf", ".persist", ".influx"} or path.name in {".env.example", "smab.env.example"}
        if not text_file:
            continue
        try:
            text = path.read_bytes().decode("utf-8")
            for number, line in enumerate(text.splitlines(), 1):
                if re.match(r"^(<{7}|={7}|>{7})(?: |$)", line):
                    fail(name, f"unresolved merge marker at line {number}")
            if yaml_file:
                document = load_yaml(text)
                if path.is_relative_to(ROOT / YAML_ROOT):
                    section, entities = openhab_entities(name, document)
                    # Examples are inactive and may intentionally reuse live UIDs.
                    if suffix != ".example":
                        for uid in entities:
                            identity = (section, uid)
                            if identity in active_ids:
                                raise ValueError("duplicate active openHAB entity UID")
                            active_ids.add(identity)
                label = "YAML / openHAB file structure"
            elif suffix == ".json":
                json.loads(text, object_pairs_hook=unique_json)
                label = "JSON"
            elif suffix == ".py":
                ast.parse(text, filename=name)
                label = "Python syntax"
            elif suffix == ".sh":
                if not shutil.which("bash"):
                    raise ValueError("bash is required")
                result = subprocess.run(["bash", "-n", str(path)], capture_output=True)
                if result.returncode:
                    raise ValueError("bash -n failed")
                label = "Bash syntax"
            elif path.name in {".env.example", "smab.env.example"}:
                public = {"SMAB_MQTT_PASSWORD": "mosquitto-mqtt"} if path.name == "smab.env.example" else None
                parsed = dotenv(text, public_credentials=public)
                if path.name == ".env.example":
                    env_values = parsed
                label = "Dotenv / credential placeholders"
            else:
                label = "Text merge markers"
            counts[label] = counts.get(label, 0) + 1
        except yaml.YAMLError as error:
            mark = getattr(error, "problem_mark", None)
            fail(name, "invalid YAML" + (f" at line {mark.line + 1}" if mark else ""))
        except (ValueError, TypeError, SyntaxError) as error:
            # Never echo source lines: configuration files can contain credentials.
            message = "invalid syntax" if isinstance(error, (SyntaxError, UnicodeError)) else str(error)
            fail(name, message)

    if env_values is None:
        fail(".env.example", "missing or invalid repository configuration template")
    elif not shutil.which("docker"):
        fail("Compose", "Docker CLI with the Compose plugin is required")
    else:
        # Do not inherit shell credentials or COMPOSE_* settings when validating
        # the repository template. The Docker daemon is not contacted by config.
        environment = {k: v for k, v in os.environ.items() if k not in env_values and not k.startswith("COMPOSE_")}
        # Test each selection independently of the template's default profiles.
        environment["COMPOSE_PROFILES"] = ""
        for size in range(len(PROFILE_SERVICES) + 1):
            for profiles in combinations(PROFILE_SERVICES, size):
                command = ["docker", "compose", "--env-file", str(ROOT / ".env.example"), "-f", str(ROOT / "docker-compose.yml")]
                for profile in profiles:
                    command.extend(["--profile", profile])
                result = subprocess.run(
                    command + ["config", "--format", "json"],
                    cwd=ROOT, env=environment, capture_output=True,
                )
                selection = ",".join(profiles) or "openhab-only"
                if result.returncode or result.stderr:
                    fail("Compose", f"profile selection {selection}: validation failed or reported warnings")
                    continue
                expected = {"openhab"}
                for profile in profiles:
                    expected.update(PROFILE_SERVICES[profile])
                try:
                    actual = set(json.loads(result.stdout)["services"])
                except (ValueError, KeyError, TypeError):
                    fail("Compose", f"profile selection {selection}: invalid configuration output")
                    continue
                if actual != expected:
                    fail("Compose", f"profile selection {selection}: unexpected service selection")
                else:
                    counts["Docker Compose profiles"] = counts.get("Docker Compose profiles", 0) + 1

    for label, count in counts.items():
        unit = "checks" if label == "Docker Compose profiles" else "files"
        print(f"PASS  {label} ({count} {unit})")
    for failure in failures:
        print("FAIL  " + failure)
    print(f"\n{'FAIL' if failures else 'PASS'}: {len(failures)} issue(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
