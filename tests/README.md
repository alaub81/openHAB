# Basic repository checks

Run from a checkout, without starting any containers:

```bash
./tests/linter-check.sh
```

The wrapper works from any directory. It requires Python 3.9+, Git, Bash, and
Docker CLI with Compose v2.20.2+ (for the existing `start_interval` settings).
A running Docker daemon is not required. On first use it creates `.lint-venv/`
and installs the pinned PyYAML dependency from `requirements-lint.txt`; that
installation requires package-index access. Later checks work offline.
The environment is ignored by Git and does not change system Python packages.

The command runs small regression tests for the checker, then checks tracked
files and non-ignored untracked files that exist in the working tree. It exits
with status 1 for failures and status 2 for unsupported arguments.
Checks do not contact live services or start containers. The linter runs only its
own regression tests and checks application-script syntax without executing those
scripts. There is no automatic formatting. Optional script safety tests are
run separately with `./tests/script-check.sh`.

## GitHub Actions

[Repository lint](../.github/workflows/lint.yml) runs the same basic linter for
pull requests, pushes to `master` and manual workflow dispatches. It uses a hosted
Ubuntu runner with Python and Docker Compose, read-only repository permissions
and pinned action revisions. It requires no deployment credentials, starts no
services and runs neither the optional script tests nor the database integration
tests. No images, tags or releases are built or published.

## Coverage

- YAML syntax and duplicate mapping keys, including `.yml.example` templates.
  This includes the local Compose example and Dependabot configuration; lint does
  not query registries, run Dependabot or verify available image tags.
- openHAB file-provider wrappers: integer `version: 1`, the appropriate entity
  map, component declarations, and unique UIDs among active files of each type.
- MQTT `on`/`off` keys remain strings rather than YAML 1.1 booleans.
- JSON syntax and duplicate keys.
- Python syntax using `ast.parse`, without importing or running project scripts.
- Bash syntax using `bash -n`, without running shell commands in those scripts.
- Unresolved merge markers in recognized text/source files.
- Unique `.env.example` assignments and `CHANGE_ME_...` credential placeholders.
  Local `.env` files are ignored and never read by the checker, even if present.
- The public `smab.env.example` receives the same checks, with one explicit
  exception for the documented public MQTT example password. Other passwords
  must remain placeholders; the private runtime `smab.env` is ignored.
- Compose configuration validation against `.env.example` for all eight
  combinations of the `mqtt`, `influxdb` and `grafana` profiles. It checks the
  exact service selection, including openHAB-only and the complete stack.
  Validation fails on warnings as well as errors. Shell values and a local
  `.env` cannot override the template. Diagnostic output never dumps resolved
  configuration or credential values. A local `.env` is not required to run checks.

Ignored archives, backups, virtual environments, and local thermostat Item files
are excluded. The checker does not validate JavaScript expressions, Item DSL,
Flux queries, binding-specific settings, Markdown links, external services,
image availability, or runtime behavior. Existing widget tests in `tools/`
remain separate. Passing lint is not a deployment or integration test.

## Shelly profile behavior checks

The profile regression runner requires Node.js in addition to the basic lint
tools. Export the library as JSON, then run the generated code with isolated
Item/MQTT/time mocks (no live openHAB connection):

```bash
ruby -ryaml -rjson -e 'puts JSON.generate(YAML.load_file(ARGV[0]))' \
  data/openhab/conf/yaml/block_libraries/lhlab_thermostat_library.yml \
  > /tmp/thermostat-library.json
node tests/verify_shelly_profiles.js /tmp/thermostat-library.json
```

It covers 48 operating combinations, 28 invalid profile/MQTT configurations,
profile zero, and a disabled thermostat. The basic lint runner also checks that
widget Item defaults remain empty and that all five profile fields start unset.
Native MainUI/Blockly generation and device integration still require a later
server-side verification.

## Optional script safety tests

Run these separately when changing maintenance scripts, the certificate helper
or the Shelly link migrator:

```bash
./tests/script-check.sh
```

The runner works from any directory and requires Python 3.9+, Bash and jq.
It uses only Python's standard library, creates no virtual environment and
installs no packages. The real curl executable and the requests package are
replaced by test doubles. OpenSSL is optional: certificate generation is skipped
when it is unavailable. All files are created in temporary directories; no live
API or Docker daemon is contacted. These tests are not part of `linter-check.sh`.

`test_maintenance.py` runs single configured Bash script copies with fake API
responses. It covers full measurement deletion, complete orphan cleanup,
conflict-log cleanup, timerange scopes, exact timestamp/tag predicates for wrong
values, response validation, failures and Digitalstrom actions. InfluxDB 1-only
checks were removed with the retired scripts. Token headers are checked without
logging token values.

`test_influxdb2_move.py` uses a stateful fake database to verify source-over-target
merging, preservation of unrelated target data, Item-tag changes, all field types,
nanoseconds, preflight changes, streamed errors and refusal to delete an
unverified source. No third-party Python packages are required.

These are offline safeguards, not live installation tests. Separate manual
checks with an isolated InfluxDB 2.9 container verify real protocol behavior.
The optional runner itself starts no containers.

Optional Bash style check (requires ShellCheck):

```bash
shellcheck scripts/*.sh certs/generate-certs.sh
```

The existing Shelly Python migrator is checked with a fake requests module for
backup protection, preflight failure, create-before-delete ordering and failed
link creation. Certificate tests use temporary repository paths; when OpenSSL is
available, they verify certificate signatures/SAN and refusal to overwrite keys.

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
