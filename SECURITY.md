# Security policy

Please report security issues affecting current main or the 0.1.x MVP through
[GitHub private vulnerability reporting](https://github.com/andrew29mo/grantweft/security/advisories/new).
Avoid publishing exploit details, credentials or sensitive access records in
public issues. Include the revision, sanitized configuration, reproduction,
expected/observed behavior and affected authorization or recovery boundary.
Do not send private keys or production data.

This is a single-maintainer project; no response-time SLA is offered. The MVP
requires trusted local administrators, individually provisioned client identities
and a network topology preventing direct backend bypass. See
[architecture](docs/ARCHITECTURE.md), [deployment](docs/DEPLOYMENT.md) and
[qualified limits](docs/EXPLORATION_RESULTS.md). MIT licensing and passing tests
are not a production-security guarantee.

Repository protection settings were checked during [publication](docs/PUBLICATION.md).
Project Actions workflows are disabled because this project uses recorded local
macOS/Linux VM qualification and has no CI workflow. GitHub-managed dependency
graph/Dependabot jobs may still appear; they are not correctness CI. Dependabot alerts/security updates and a
weekly pip update configuration are enabled; no third-party Python runtime
packages are declared. This does not monitor arbitrary host/VM OS packages.

Power-loss recovery, boot-zero-gap, long-term catalog rollover/endurance,
credential lifecycle on already-open sessions and hostile local root/same-UID
actors are outside the qualified scope.
