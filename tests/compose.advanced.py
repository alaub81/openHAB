#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Validate optional bridge profiles without reading local settings or starting services."""

from itertools import combinations
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from lint import PROFILE_SERVICES, ROOT, dotenv, load_yaml

ADVANCED = ROOT / "docker-compose.advanced.yml"
BRIDGES = {"sma": {"sma-mqtt-bridge"}, "bmw": {"bmw-mqtt-bridge"}}


class CheckFailure(Exception):
    """A diagnostic that contains no configuration values or credentials."""


def require(condition, message):
    if not condition:
        raise CheckFailure(message)


def main():
    if len(sys.argv) != 1:
        print("Usage: .lint-venv/bin/python tests/compose.advanced.py", file=sys.stderr)
        return 2
    try:
        require(shutil.which("docker"), "Docker CLI with Compose is required")
        base = (ROOT / ".env.example").read_text()
        supplement = (ROOT / ".env.advanced.example").read_text()
        values = dotenv(base + "\n" + supplement)
        require(not set(values["COMPOSE_PROFILES"].split(",")) & set(BRIDGES),
                "Bridge profiles must be disabled in the example")
        require(values["COMPOSE_FILE"] == "docker-compose.yml:docker-compose.advanced.yml",
                "The supplement must select both Compose files in order")
        overlay = load_yaml(ADVANCED.read_text())
        require(set(overlay["services"]) == set().union(*BRIDGES.values()),
                "The extension may add only the two bridge services")
        require("environment" not in overlay["services"]["sma-mqtt-bridge"],
                "SMA runtime settings must come from smab.env without environment overrides")
        require({key for key in values if key.startswith("SMAB_")} ==
                {"SMAB_BRIDGE_VERSION", "SMAB_ENV_FILE", "SMAB_UID", "SMAB_GID"},
                "The stack template may contain only SMA Compose settings")
        referenced = set(re.findall(r"(?<!\$)\$\{([A-Z][A-Z0-9_]*)", ADVANCED.read_text()))
        # Optional CA paths are documented as commented example assignments.
        documented = set(re.findall(r"^# ([A-Z][A-Z0-9_]*)=", supplement, re.MULTILINE))
        require(referenced <= set(values) | documented,
                "Every Compose variable needs a template assignment or commented example")

        environment = {
            key: value for key, value in os.environ.items()
            if key not in values and not key.startswith(("COMPOSE_", "SMAB_", "BMB_"))
        }
        environment["COMPOSE_PROFILES"] = ""

        def config(env_path, profiles, advanced=True, automatic=False, use_defaults=False):
            command = ["docker", "compose", "--env-file", str(env_path)]
            if not automatic:
                command.extend(["-f", str(ROOT / "docker-compose.yml")])
                if advanced:
                    command.extend(["-f", str(ADVANCED)])
            for profile in profiles:
                command.extend(["--profile", profile])
            selected_environment = environment.copy()
            if use_defaults:
                selected_environment.pop("COMPOSE_PROFILES", None)
            result = subprocess.run(command + ["config", "--format", "json"],
                                    cwd=ROOT, env=selected_environment, capture_output=True)
            # Never print resolved configuration, credentials or Compose diagnostics.
            require(result.returncode == 0 and not result.stderr,
                    "Compose validation failed or reported warnings for " + (",".join(profiles) or "openhab-only"))
            return json.loads(result.stdout)

        with tempfile.TemporaryDirectory(prefix="openhab-advanced-check-") as directory:
            smab_path = Path(directory) / "synthetic-smab.env"
            smab_values = {
                "SMAB_MQTT_HOST": "mqtt.example.invalid", "SMAB_MQTT_PORT": "8883",
                "SMAB_MQTT_TLS": "true", "SMAB_MQTT_USERNAME": "sma-example",
                "SMAB_MQTT_PASSWORD": "CHANGE_ME_SYNTHETIC_MQTT_PASSWORD",
                "SMAB_INVERTER1_ENABLED": "true", "SMAB_INVERTER1_HOST": "inverter.example.invalid",
                "SMAB_INVERTER2_ENABLED": "false", "SMAB_COMMANDS_ENABLED": "false",
            }
            smab_path.write_text("".join(f"{key}={value}\n" for key, value in smab_values.items()))
            os.chmod(smab_path, 0o600)
            values["SMAB_ENV_FILE"] = str(smab_path)
            env_path = Path(directory) / "example.env"
            env_path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))
            os.chmod(env_path, 0o600)
            baseline = {}
            for size in range(len(PROFILE_SERVICES) + 1):
                for profiles in combinations(PROFILE_SERVICES, size):
                    baseline[profiles] = config(env_path, profiles, advanced=False)["services"]
            all_profiles = {**PROFILE_SERVICES, **BRIDGES}
            checked = 0
            for size in range(len(all_profiles) + 1):
                for profiles in combinations(all_profiles, size):
                    services = config(env_path, profiles)["services"]
                    expected = {"openhab"}
                    for profile in profiles:
                        expected.update(all_profiles[profile])
                    require(set(services) == expected, "Unexpected service selection")
                    base_profiles = tuple(profile for profile in profiles if profile in PROFILE_SERVICES)
                    require({name: services[name] for name in baseline[base_profiles]} == baseline[base_profiles],
                            "The extension must preserve the base services")
                    for profile, names in BRIDGES.items():
                        if profile not in profiles:
                            continue
                        service = services[next(iter(names))]
                        require(service.get("read_only") and not service.get("ports") and "build" not in service,
                                "Bridge must use an image, read-only root and no published ports")
                        prefix = "SMAB_" if profile == "sma" else "BMB_"
                        require(all(key.startswith(prefix) for key in service["environment"]),
                                "A bridge must not receive unrelated service credentials")
                        state_path = "/data/sma-mqtt-bridge/state" if profile == "sma" else "/app/token"
                        require(any(mount["type"] == "volume" and mount["target"] == state_path
                                    for mount in service["volumes"]), "Persistent bridge state volume missing")
                        if profile == "sma":
                            require(service.get("network_mode") == "host", "SMA UDP requires host networking here")
                            require(service["environment"] == smab_values,
                                    "Every SMA setting must come from the separate ENV file")
                        else:
                            require("app-nw" in service["networks"], "BMW must reach the app network")
                            require(service["environment"]["BMB_MQTT_HOMIE"] == "0", "BMW Homie must default to disabled")
                    checked += 1

            automatic = config(env_path, (), automatic=True, use_defaults=True)["services"]
            default_services = {"openhab"}
            for profile in values["COMPOSE_PROFILES"].split(","):
                default_services.update(PROFILE_SERVICES[profile])
            require(set(automatic) == default_services, "COMPOSE_FILE must preserve the template's default services")
            require(set(config(env_path, ("sma", "bmw"), automatic=True)["services"]) ==
                    {"openhab", "sma-mqtt-bridge", "bmw-mqtt-bridge"},
                    "COMPOSE_FILE must load both optional services")

            external_values = values.copy()
            external_values.update({
                # Stack values must not shadow the existing SMA runtime file.
                "SMAB_MQTT_HOST": "unused.example.invalid", "SMAB_INVERTER1_ENABLED": "false",
                "BMB_MQTT_LOCAL_HOST": "mqtt.example.invalid",
                "BMB_MQTT_LOCAL_PORT": "8883", "BMB_MQTT_LOCAL_TLS": "true",
                "BMB_MQTT_HOMIE": "1", "BMB_MQTT_RETAIN": "1",
                "BMB_MQTT_LOCAL_CLIENT_ID": "example-bmw-client",
                "BMB_BMW_HOST": "stream.example.invalid", "BMB_BMW_PORT": "9001",
                "BMB_BMW_STATUS_STABLE_DELAY": "10",
            })
            env_path.write_text("".join(f"{key}={value}\n" for key, value in external_values.items()))
            external = config(env_path, ("sma", "bmw"))["services"]
            require(set(external) == {"openhab", "sma-mqtt-bridge", "bmw-mqtt-bridge"},
                    "An external broker must not require the local MQTT service")
            require(external["sma-mqtt-bridge"]["environment"] == smab_values,
                    "Stack variables must not shadow smab.env")
            settings = external["bmw-mqtt-bridge"]["environment"]
            require(settings["BMB_MQTT_LOCAL_HOST"] == "mqtt.example.invalid" and
                    settings["BMB_MQTT_LOCAL_PORT"] == "8883" and settings["BMB_MQTT_LOCAL_TLS"] == "true",
                    "External MQTT overrides must reach BMW")
            for key in ("BMB_MQTT_HOMIE", "BMB_MQTT_RETAIN", "BMB_MQTT_LOCAL_CLIENT_ID",
                        "BMB_BMW_HOST", "BMB_BMW_PORT", "BMB_BMW_STATUS_STABLE_DELAY"):
                require(settings[key] == external_values[key], "Additional BMW overrides must reach the service")

            # Compose validates required IDs before profiles, even if BMW is off.
            # Use only temporary files, never a real local smab.env.
            minimal = dotenv(base)
            minimal["SMAB_ENV_FILE"] = str(Path(directory) / "absent-smab.env")
            for key in ("BMB_BMW_CLIENT_ID", "BMB_BMW_GCID"):
                incomplete = {**minimal, **{other: values[other] for other in
                              ("BMB_BMW_CLIENT_ID", "BMB_BMW_GCID") if other != key}}
                env_path.write_text("".join(f"{name}={value}\n" for name, value in incomplete.items()))
                result = subprocess.run(
                    ["docker", "compose", "--env-file", str(env_path), "-f", str(ROOT / "docker-compose.yml"),
                     "-f", str(ADVANCED), "config", "--quiet"],
                    cwd=ROOT, env=environment, capture_output=True,
                )
                require(result.returncode != 0 and key.encode() in result.stderr,
                        "Missing BMW ID declarations must fail Compose validation")
            minimal.update({key: values[key] for key in ("BMB_BMW_CLIENT_ID", "BMB_BMW_GCID")})
            env_path.write_text("".join(f"{key}={value}\n" for key, value in minimal.items()))
            require(set(config(env_path, tuple(PROFILE_SERVICES))["services"]) ==
                    {"openhab"}.union(*PROFILE_SERVICES.values()),
                    "Declared placeholder IDs must allow an unused BMW profile")
            fallback = config(env_path, ("bmw",))["services"]["bmw-mqtt-bridge"]["environment"]
            require(fallback["BMB_MQTT_LOCAL_HOST"] == "host.docker.internal" and fallback["BMB_MQTT_HOMIE"] == "0",
                    "BMW fallback values must match the transferred local defaults")

        print(f"PASS: {checked} advanced profile combinations; 8 unchanged base combinations.")
        print("PASS: default-off, COMPOSE_FILE loading, external MQTT, required BMW IDs and isolated runtime settings.")
        print("No containers started; no local .env, devices or accounts accessed.")
        return 0
    except CheckFailure as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1
    except (ValueError, KeyError, TypeError, OSError):
        # Suppress exception details that might contain source values.
        print("FAIL: advanced Compose check failed; inspect templates and rerun basic lint.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
