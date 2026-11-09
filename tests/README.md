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
with status 1 for failures and status 2 for unsupported arguments. Checks are
read-only: there is no automatic formatting or application-script execution.

## Coverage

- YAML syntax and duplicate mapping keys, including `.yml.example` templates.
- openHAB file-provider wrappers: integer `version: 1`, the appropriate entity
  map, component declarations, and unique UIDs among active files of each type.
- MQTT `on`/`off` keys remain strings rather than YAML 1.1 booleans.
- JSON syntax and duplicate keys.
- Python syntax using `ast.parse`, without importing or running project scripts.
- Bash syntax using `bash -n`, without running shell commands in those scripts.
- Unresolved merge markers in recognized text/source files.
- Unique `.env.example` assignments and `CHANGE_ME_...` credential placeholders.
  Local `.env` files are ignored and never read by the checker, even if present.
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
