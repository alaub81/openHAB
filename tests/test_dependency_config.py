"""Protect security ownership, compatibility boundaries and native-tool extraction."""

from collections import Counter
import json
import re
import unittest

from lint import ROOT, load_yaml

CONFIG = json.loads((ROOT / "renovate.json").read_text())


class DependencyTests(unittest.TestCase):
    def test_influxdb_two_only_in_all_regular_updates(self):
        rule = next(
            r for r in CONFIG["packageRules"] if "influxdb" in r.get("matchPackageNames", [])
        )
        pattern = re.compile(rule["allowedVersions"][1:-1])
        for value in ("2", "2.9", "2.99.1", "2.9-alpine"):
            self.assertRegex(value, pattern)
        for value in ("1.8", "3", "3.0-alpine", "latest", "2.9-rc1"):
            self.assertNotRegex(value, pattern)
        image = load_yaml((ROOT / "docker-compose.yml").read_text())["services"]["influxdb"][
            "image"
        ]
        self.assertRegex(image.split(":")[1], pattern)

    def test_dependabot_is_security_only_without_regular_delay(self):
        bot = load_yaml((ROOT / ".github/dependabot.yml").read_text())
        self.assertFalse(CONFIG["vulnerabilityAlerts"]["enabled"])
        self.assertEqual(
            {u["package-ecosystem"] for u in bot["updates"]},
            {"pip", "github-actions", "docker-compose"},
        )
        for entry in bot["updates"]:
            self.assertEqual(entry["open-pull-requests-limit"], 0)
            self.assertNotIn("cooldown", entry)
            self.assertNotIn("target-branch", entry)
        compose = bot["updates"][0]
        self.assertEqual(compose["ignore"], [{"dependency-name": "influxdb", "versions": [">=3"]}])

    def test_regular_update_policy_and_manual_merges(self):
        self.assertEqual(CONFIG["timezone"], "Europe/Berlin")
        self.assertEqual(CONFIG["schedule"], ["* 0-5 * * 1"])
        self.assertEqual(CONFIG["minimumReleaseAge"], "3 days")
        self.assertEqual(CONFIG["prConcurrentLimit"], 3)
        self.assertTrue(CONFIG["ignoreUnstable"])
        self.assertFalse(CONFIG["automerge"])
        self.assertFalse(any(r.get("automerge") for r in CONFIG["packageRules"]))

    def test_native_assets_versions_and_checksums_are_all_extracted(self):
        manager = CONFIG["customManagers"][0]
        matches = [({}, (ROOT / "lint-tools.json").read_text())]
        for expression in manager["matchStrings"]:
            expression = re.sub(r"\(\?<([A-Za-z][A-Za-z0-9_]*)>", r"(?P<\1>", expression)
            matches = [
                (dict(previous, **m.groupdict()), m[0])
                for previous, content in matches
                for m in re.finditer(expression, content)
            ]
        extracted = Counter(
            (m["depName"], m["currentValue"], m["currentDigest"]) for m, _ in matches
        )
        tools = json.loads((ROOT / "lint-tools.json").read_text())
        expected = Counter(
            (t["repository"], a["version"], a["sha256"])
            for t in tools.values()
            for a in t["assets"].values()
        )
        self.assertEqual(extracted, expected)


if __name__ == "__main__":
    unittest.main()
