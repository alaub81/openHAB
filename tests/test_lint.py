# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Regression checks for configuration mistakes the repository linter must catch."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from lint import dotenv, load_yaml, openhab_entities, project_files, unique_json


class LintRegressionTests(unittest.TestCase):
    def test_local_environment_is_excluded_even_if_it_exists(self):
        with patch("lint.subprocess.check_output", return_value=b".env\0.env.example\0"):
            with patch("lint.Path.is_file", return_value=True):
                self.assertEqual(project_files(), [".env.example"])

    def test_widget_item_parameters_have_no_implicit_items(self):
        root = Path(__file__).resolve().parents[1] / "data/openhab/conf/yaml/widgets"
        for path in root.glob("*.yml"):
            widget = next(iter(load_yaml(path.read_text())["widgets"].values()))
            for param in widget.get("props", {}).get("parameters", []):
                if param.get("context") == "item":
                    self.assertFalse(param.get("default"), (path.name, param["name"]))

    def test_shelly_profile_fields_require_explicit_configuration(self):
        path = Path(__file__).resolve().parents[1] / "data/openhab/conf/yaml/block_libraries/lhlab_thermostat_library.yml"
        blocks = load_yaml(path.read_text())["blocks"]["lhlab_thermostat_library"]["slots"]["blocks"]
        block = next(b for b in blocks if b["config"]["type"] == "Shelly Walldisplay Thermostat Control")
        fields = {a["name"]: a for a in block["config"]["args0"] if a["name"].startswith("PROFILE_") and a["name"] != "PROFILE_ITEM"}
        self.assertEqual(set(fields), {"PROFILE_WINDOW", "PROFILE_ABSENCE", "PROFILE_BOOSTER", "PROFILE_SGGREEN", "PROFILE_NIGHT"})
        for field in fields.values():
            self.assertEqual(field["value"], -1)
            self.assertEqual(field["precision"], 1)

    def test_duplicate_yaml_service_settings_are_rejected(self):
        with self.assertRaises(ValueError):
            load_yaml("service:\n  stop_grace_period: 1m\n  stop_grace_period: 2m\n")

    def test_mqtt_on_off_keys_remain_strings(self):
        value = load_yaml('on: "true"\noff: "false"\nenabled: true\n')
        self.assertEqual(value, {"on": "true", "off": "false", "enabled": True})

    def test_mainui_export_is_not_a_file_based_widget(self):
        with self.assertRaises(ValueError):
            openhab_entities("widgets/widget.yml", {"uid": "widget", "component": "oh-cell"})

    def test_boolean_version_is_not_version_one(self):
        with self.assertRaises(ValueError):
            openhab_entities(
                "widgets/widget.yml",
                {"version": True, "widgets": {"widget": {"component": "oh-cell"}}},
            )

    def test_inactive_thing_example_uses_file_provider_wrapper(self):
        section, entities = openhab_entities(
            "things/thing.yml.example",
            load_yaml("version: 1\nthings:\n  mqtt:topic:broker:device:\n    config: {}\n"),
        )
        self.assertEqual(section, "things")
        self.assertIn("mqtt:topic:broker:device", entities)

    def test_duplicate_json_keys_are_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"item":"first","item":"second"}', object_pairs_hook=unique_json)

    def test_dotenv_rejects_duplicate_assignments(self):
        with self.assertRaises(ValueError):
            dotenv("TZ=Europe/Berlin\nTZ=UTC\n")

    def test_dotenv_rejects_literal_credentials_without_echoing_them(self):
        credential = "not-a-real-credential"
        with self.assertRaises(ValueError) as error:
            dotenv("POSTGRES_PASSWORD=" + credential)
        self.assertNotIn(credential, str(error.exception))
        self.assertEqual(
            dotenv("POSTGRES_PASSWORD=CHANGE_ME_POSTGRES_PASSWORD\n")["POSTGRES_PASSWORD"],
            "CHANGE_ME_POSTGRES_PASSWORD",
        )


if __name__ == "__main__":
    unittest.main()
