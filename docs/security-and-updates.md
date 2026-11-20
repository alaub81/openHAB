# Security checks and dependency updates

This repository consumes upstream images; it does not build or release its own.
Security checks cover this repository's code and committed history. Third-party
container images are not scanned here, including optional bridge images. Their
maintainers publish image fixes and rebuilds. This Compose-only profile
uses Renovate for version updates and Dependabot for supported security alerts;
it does not claim that a dependency update makes a deployment vulnerability-free.

The decision to omit upstream-image scans was explicitly requested by the
repository owner on 2026-11-20. No repository-local image gate or image-scan
schedule is maintained. Existing scan artifacts remain historical evidence.

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
Compose syntax checks alone are insufficient.

InfluxDB remains on the **2.x** line because persistence and maintenance tools
use Flux. Renovate rejects 1.x, 3.x, prerelease and `latest` tags. Dependabot also
ignores InfluxDB versions 3 and above. Do not replace this constraint with an
unbounded major update to resolve an upstream security finding.

Dependabot Alerts and Dependabot Security Updates remain responsible for
alert-driven security PRs. Its configured ecosystems have a regular version-PR
limit of zero. Renovate vulnerability PRs are disabled to avoid duplicate
ownership. Security PRs have no added three-day age restriction, Monday window
or cooldown. GitHub ecosystem/advisory support determines which alerts can be
fixed automatically. Upstream image vulnerabilities may require a maintainer
release and manual review even when no Dependabot PR is available.

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

Historical credential status and production upgrades require owner review.
Removing the image scanner does not resolve upstream vulnerabilities. Upstream
maintainers publish image fixes; deployment operators review and apply updates.
This package changes neither credentials nor deployed images.
