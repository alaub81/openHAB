# Security checks and dependency updates

This repository consumes upstream images; it does not build or release its own.
Security gates assess the public defaults in Git, not a private installation's
local overrides, credentials or running containers. Passing a gate is not proof
of a vulnerability-free deployment.

## Secret scanning

CI runs `tools/secret-check.sh` on every PR and push, including documentation
changes. Gitleaks scans the committed base-to-head range. A missing, invalid,
unavailable or non-ancestor base falls back to the complete history. Shallow
clones fail rather than claim complete coverage. GitHub Actions checks out the
full history; local users must fetch it before running a full scan.

```bash
./tools/secret-check.sh --full
```

The scheduled workflow repeats the complete-history scan monthly, on the first
at 03:00 UTC, and on manual dispatch. Results are redacted; no secret-bearing
report is uploaded as a CI artifact. Local untracked credentials, archives and
runtime data are not scanned. A history finding requires investigation and, for
real credentials, revocation/rotation with the affected provider. Removing a
file in a later commit does not revoke credentials or erase older commits.
There are no blanket Gitleaks exceptions. History rewriting is a separate,
explicitly coordinated migration.

## Upstream image gate

```bash
./tools/image-security-check.sh .security-reports/trivy
```

Use the prerequisites in the [test guide](../tests/README.md). The command also
requires jq and downloads the pinned Trivy tool and current vulnerability
metadata on first use. It contacts public registries without starting services
or using a Docker daemon. The eight images come from the base and Advanced
Compose files and the public Advanced ENV template; local `.env`, `smab.env`,
Docker state and installed image caches never select the scan targets.

CI scans these images when public Compose/image inputs, scan tooling, workflows
or dependency policy change. Unknown bases and empty diffs scan everything.
The scheduled workflow scans all images every Monday at 03:00 UTC, monthly
alongside the history scan, and on manual dispatch. This covers mutable `latest`
tags even without repository changes. It downloads metadata; it does not rebuild
upstream images or update a running installation.

For each image, one full vulnerability scan creates raw JSON with all severity
levels and unfixed findings. SARIF and the gate are derived from that JSON.
Only findings with a nonempty fixed version and severity HIGH or CRITICAL block
the gate. There are currently no vulnerability exceptions. Do not lower severity
or hide packages merely to make CI green. Scan/database/conversion errors also
fail; other images continue where possible to preserve evidence.

Complete JSON, SARIF and derived gate JSON are retained as Actions artifacts for
seven days, including when the gate fails. Categories identify image and scan
platform. SARIF uploads to Code Scanning run on public non-PR events; PRs and
repositories without Code Scanning retain the full SARIF artifact instead.
No `continue-on-error` overrides the vulnerability gate.

The automated scan platform is `linux/amd64`. This is a documented, bounded
coverage choice for consumed images, not a multiarch release or runtime support
promise. ARM deployments require separate architecture-specific checks:

```bash
SCAN_PLATFORM=linux/arm64 ./tools/image-security-check.sh .security-reports/trivy-arm64
```

Coverage exception owner: Andreas Laub. Review by 2027-02-20, including the
renderer and optional bridges, before promising automated arm64 coverage.
Pinned tool versions/checksums are maintained in `lint-tools.json`.

## Renovate and Dependabot responsibilities

Renovate owns regular Docker/Compose, GitHub Actions, Python check-tool and Node
version updates. The native-tool regex manager extracts each platform's release
version and checksum together. A second regex manager tracks the isolated
Renovate validator image. Local archives, private ENV files and tool caches are
excluded.

Regular PRs may open Mondays before 06:00 Europe/Berlin, with three days minimum
release age and at most three concurrently open PRs. Related Actions and Python
check-tool minor/patch updates are grouped separately. Unstable releases are
excluded for stable dependencies. Major updates require manual review. Automerge
is disabled until a dependency-specific allowlist has meaningful runtime checks;
Compose syntax and an upstream vulnerability scan alone are insufficient.

InfluxDB remains on the **2.x** line because persistence and maintenance tools
use Flux. Renovate rejects 1.x, 3.x, prerelease and `latest` tags. Dependabot also
ignores InfluxDB versions 3 and above. Do not replace this constraint with an
unbounded major update to resolve an upstream security finding.

Dependabot Alerts and Dependabot Security Updates remain responsible for
alert-driven security PRs. Its configured ecosystems have a regular version-PR
limit of zero. Renovate vulnerability PRs are disabled to avoid duplicate
ownership. Security PRs have no added three-day age restriction, Monday window
or cooldown. GitHub ecosystem/advisory support determines which alerts can be
fixed automatically; an upstream Trivy finding does not guarantee a Dependabot
PR for that image.

The normal offline suite tests policy boundaries and native dependency
extraction. To run Renovate's actual strict validator and extract-only mode:

```bash
.lint-venv/bin/python tests/dependency-check.py
```

This additional command requires a running Docker daemon and the pinned public
Renovate image. It copies only public dependency manifests to a temporary Git
checkout and runs without network access, API credentials or repository writes.
CI executes it for dependency-policy/tooling/workflow changes. No lookup, update,
PR creation or merge occurs. Offline extraction may warn that GitHub lookup
requires a token; lookup is deliberately outside this test.

## GitHub activation and current findings

Before considering the rollout active on the default branch, verify:

- The Renovate GitHub App is installed and `alaub81/openHAB` is selected.
- Dependabot Alerts, the dependency graph and Dependabot Security Updates remain
  enabled in [repository security settings](https://github.com/alaub81/openHAB/settings/security_analysis).
- The Dependency Dashboard and first scheduled Renovate run appear after rollout.
- Actions can upload artifacts; Code Scanning accepts SARIF where available.

These account settings cannot be inferred from configuration files. During this
change, the connector confirmed admin access, default branch `master`, public
visibility and disabled repository automerge. It did not expose the installed
Renovate selection or Dependabot security switches. The available browser was
not signed in, so those switches remain unverified. Branch protection and PR
requirements remain deferred as specified by Repository Standard v1.

Local baseline on 2026-11-20:

- Full Gitleaks history scan: 146 commits, ten historical generic-API-key
  findings in formerly tracked ENV/maintenance files. They remain unresolved;
  a monthly full-history scan will fail until reviewed. No secrets were copied
  into repository documentation or scan exceptions.
- Trivy scanned all eight public default images for amd64. Fixable HIGH/CRITICAL
  occurrences were found in openHAB (35), InfluxDB 2 (88), PostgreSQL (45), Grafana
  (20) and the SMA bridge (1). These are per-image occurrences, not deduplicated
  CVE counts. All complete JSON/SARIF reports are kept locally in the ignored
  `.security-reports/trivy/` directory. The image gate currently fails as intended.

These are findings to resolve, not a conformance claim. Unfixed and lower-severity
findings are also present in the complete reports, including for images with no
blocking finding. Review current upstream releases, fixes and exploitability
separately. Historical credential status and production upgrades require owner
review; this package changes neither credentials nor deployed images.
