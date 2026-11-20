# Repository checks

Run the same entry points locally and in GitHub Actions:

```bash
./tests/linter-check.sh
./tests/test-check.sh
```

Both wrappers work from any directory and fail when a required tool is missing.
Use Python 3.9+, Git, Bash, Node.js at the version in [`.node-version`](../.node-version),
and Docker CLI with Compose v2.20.2+ (for `start_interval`). The behavior tests
also require jq and OpenSSL. No running Docker daemon is required.

On first use, the wrappers create the ignored `.lint-venv/` and install the exact
Python dependencies in [`requirements-lint.txt`](requirements-lint.txt). Lint
also prepares ShellCheck and Actionlint in the ignored `.lint-tools/`, using the
versions and release checksums in [`lint-tools.json`](../lint-tools.json).
Matching system installations can be reused. The native tool installer supports
Linux and macOS on x86-64 and arm64. Initial dependency preparation needs network
access; subsequent checks run offline. System Python packages are not changed.

## Lint and documentation

`linter-check.sh` runs checker/planner regression tests and validates tracked and
non-ignored untracked public files. It does not format or execute application code.
Coverage includes:

- YAML syntax and duplicate keys, including inactive `.yml.example` files.
- openHAB file-provider wrappers, `version: 1`, component declarations, unique
  active UIDs, explicit Item selection and unset thermostat profile fields.
- String MQTT `on`/`off` keys; valid JSON without duplicate keys.
- ENV placeholders and unique assignments, with the explicitly documented public
  SMA MQTT example exception. Private `.env` and `smab.env` files remain excluded.
- All eight base Compose profile combinations, using the public ENV example in
  isolation from local credentials. Compose warnings are failures.
- Python syntax, Ruff static checks and Ruff formatting; Bash syntax and
  ShellCheck; GitHub Actions syntax with Actionlint; JavaScript/CommonJS syntax.
- LF line endings, final newlines, trailing whitespace and merge markers.
- Local Markdown links and heading fragments, including reference-style links;
  syntax of fenced Bash, YAML, JSON and Python examples. Examples are parsed,
  never executed. External URLs and image availability are not queried.

Python rules are defined in [`ruff.toml`](../ruff.toml). To format an intentional
Python change, use `.lint-venv/bin/python -m ruff format --config ruff.toml PATH`.
No Dockerfiles are present, so Hadolint is not needed for this profile.

## Offline behavior tests

`test-check.sh` runs Python regression tests, the Advanced Compose checker and a
shared Node runner. All inputs are synthetic or versioned public YAML; no local
archives, accounts, devices, services or notification endpoints are used.

- Maintenance scripts: measurement deletion, orphan cleanup, conflict logs,
  timerange boundaries, wrong-value predicates, failures and Digitalstrom actions.
- InfluxDB move/merge: stateful fake database, typed values, nanoseconds,
  preservation of target data and refusal to delete unverified sources.
- Certificates: temporary keys/certificates, signatures/SAN and overwrite refusal.
  OpenSSL is required by the full entry point, so these checks cannot silently skip.
- Shelly migration: fake requests API, protected backups, preflight failure,
  create-before-delete ordering and failed-link handling.
- Advanced Compose: all 32 profile combinations, unchanged base services,
  default-off bridges, separate SMA ENV, external MQTT and required BMW IDs.
- Battery/humidity widgets: actual YAML helpers and bindings, using Node on Linux
  or macOS. Optional private archived-Item comparisons remain outside CI.
- Window widget: synthetic contacts, metadata, loading, alarm and unknown states,
  plus current compact/detail bindings. The optional historical performance
  comparison still requires a caller-supplied old widget.
- Shelly thermostat: 48 operating combinations, 28 invalid configurations,
  profile zero and disabled behavior, with Item/MQTT/time mocks.
- State/temperature alarms: source and generated YAML utilities are both checked,
  including equality with their maintained JavaScript sources.
- Humidity alarms: both the standalone source and the current YAML utility run
  against the simulated Items/cache/timer harness. They are checked separately;
  their synchronization policy remains documented in the tools guide.
- DWD: source/YAML equality, formatting, alarm memory, updates, clearance and DST
  scenarios. CI uses a small time double backed by Node's Intl timezone data;
  verification against openHAB's installed time API is still required.

The runner converts YAML to temporary JSON with the pinned Python YAML parser;
Ruby and macOS `osascript` are not needed. `script-check.sh` remains available as
a smaller, standard-library-only maintenance test subset, requiring Python, Bash
and jq. That subset keeps its optional OpenSSL behavior for compatibility.

The heat-pump verifier in `tools/heatpump-daily/verify.js` needs JavaScript
produced by openHAB's Blockly generator; this generated rule is not versioned.
It remains an explicit manual verification, as does DWD notification-rule wiring
with a saved generated rule. CI does not claim to cover either installed rule,
MainUI's native generator/rendering, Item DSL, Flux semantics or real devices.

## GitHub Actions

[Repository checks](../.github/workflows/lint.yml) runs on pull requests, pushes to
`master` and manual dispatch. Lint, Compose validation and documentation/example
checks always run. Behavior tests may skip only when a known diff contains solely
Markdown or LICENSE changes. Changes to workflows, tools, dependencies, Compose,
fixtures or unknown paths run all behavior tests. Missing/unavailable bases and
empty diffs also run all tests. Renames include both old and new paths.

The `CI required` job runs even after failures and cancellations. It accepts a
skipped behavior job only when the planner explicitly selected documentation-only
checks. Permissions remain read-only, actions are SHA-pinned, jobs have timeouts,
and newer runs may cancel older runs of the same branch. No containers, images,
tags or releases are started, built or published. This does not configure GitHub
branch protection or required-status enforcement.

## Optional real InfluxDB 2.9 checks

This separate opt-in command requires a running local Docker daemon and the
explicitly downloaded test image:

```bash
docker pull influxdb:2.9-alpine
python3 tests/influxdb2-integration-check.py
```

It starts a unique temporary container with no network, published ports or host
data volumes. It limits the instance to one CPU and 512 MiB RAM, uses synthetic
data and removes the container afterward. It exercises merging/moving typed
field values with nanosecond timestamps, complete measurement deletion,
timerange boundaries, exact tagged outlier deletion, conflict-log cleanup and
orphan cleanup. openHAB Item responses are simulated; InfluxDB is real. HTTP
calls are transported through `docker exec` into the isolated container, so
this does not test host networking, TLS or deployment credentials.

The image stays in Docker's local cache. This command is separate from both the
simple linter and offline script runner.
