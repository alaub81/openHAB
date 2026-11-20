"""Export public YAML into a temporary directory and run Node behavior tests."""

import json
import subprocess
import tempfile
from pathlib import Path

from lint import ROOT, load_yaml


def main():
    with tempfile.TemporaryDirectory(prefix="openhab-js-tests-") as directory:
        bundle = {}
        for section in ("widgets", "block_libraries"):
            for path in (ROOT / "data/openhab/conf/yaml" / section).glob("*.yml"):
                document = load_yaml(path.read_text())
                bundle.update(document["widgets" if section == "widgets" else "blocks"])
        path = Path(directory) / "components.json"
        path.write_text(json.dumps(bundle))
        subprocess.run(["node", "tests/javascript-check.cjs", str(path)], cwd=ROOT, check=True)
        library = Path(directory) / "alarms.json"
        library.write_text(json.dumps(bundle["lhlab_alarm_library"]))
        subprocess.run(["node", "tools/state-alarms/check.cjs", str(library)], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
