# Reporting a security problem

Report vulnerabilities privately through
[GitHub Security Advisories](https://github.com/alaub81/openHAB/security/advisories)
using **Report a vulnerability**. Private vulnerability reporting is enabled.
Keep exploit details, credentials and private installation data out of public
issues, pull requests and screenshots.

A useful report includes:

- The affected repository commit and component: Compose configuration, widget,
  Blockly library or maintenance script.
- Relevant openHAB, container image and host versions.
- The impact and minimal reproduction steps using synthetic data.
- Redacted diagnostic output, if needed. Never include a complete `.env`, API
  token, password, private key, database export or openHAB userdata backup.

If GitHub's private reporting form is unavailable, open a public issue asking
only for a private security contact, without vulnerability details. Share the
report after a private channel has been agreed.

## Scope and maintained version

The current `master` branch is maintained. Include its commit ID when reporting;
this repository does not require versioned releases. Upstream openHAB, Docker
images, bindings and other dependencies have their own security processes.
Report a flaw in this repository's configuration or code here; report an
upstream-only flaw through the affected project's private reporting channel.

For ordinary setup questions and reproducible non-security bugs, use
[GitHub issues](https://github.com/alaub81/openHAB/issues).

## Automated checks

See [security checks and dependency updates](docs/security-and-updates.md) for
Gitleaks history checks, known baseline findings and the division between
Renovate and Dependabot. Third-party container images are not scanned in this
Compose repository. Secret-scan failures block the CI summary.
