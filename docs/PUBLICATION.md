# Public release and repository protection

Date: 2026-10-25 (Asia/Taipei). The owner explicitly authorized changing
`andrew29mo/grantweft` from Private to Public. The project uses
[MIT](../LICENSE); [third-party terms](../THIRD_PARTY_NOTICES.md) remain separate.
This publishes the bounded MVP, not a production-readiness guarantee.

## Content and qualification

The publication pass checks the existing 51-test macOS/Linux receipts, installed
runtime/service hashes, JSON/HTML consistency, 133 corruption controls and the
[MIT metadata-only bridge](LICENSE_REVIEW.md). All execution inputs are unchanged.
The source-bound VM record still covers the formal systemd lifecycle, enabled
boot recovery, preserved old journal, readonly repair and forty same-process
cycles over 600 seconds. It is not a new test run performed during publication.

The parent history was scanned across 224 unique blob objects and historical
paths before changing visibility. No private keys, common token patterns, private
workstation paths or accidentally committed test/build artifacts were found.
These checks are not proof against every possible secret format. Raw diagnostics,
PKI, databases, wheels, environments and VM disks remain untracked/ignored.

Historical documents retain the visibility and license state of their recorded
revision; current project status is Public/MIT. No execution receipt is rewritten
because the repository became public. RSS growth and finite catalog limits remain
explicit in [measured results](EXPLORATION_RESULTS.md). Sudden power loss,
boot-zero-gap, actual suspend and long-term operation remain untested.

## Verified GitHub settings

[Sanitized API snapshot](../evidence/publication-settings.json) records the settings
read back after application. These are a point-in-time configuration check:

| Setting | Observed |
| --- | --- |
| Visibility / license | Public / MIT |
| Write collaborators | Only the existing owner, andrew29mo; no new access grant |
| Secret scanning / push protection | Enabled |
| Dependabot alerts / automatic security updates | Enabled; security updates not paused |
| Private vulnerability reporting | Enabled; see [security policy](../SECURITY.md) |
| main force pushes / deletion | Disabled, including administrators |
| main history | Linear history required |
| Direct owner commits | Retained; no mandatory PR or nonexistent CI check |
| Project GitHub Actions workflows | Disabled; no CI workflow is shipped |
| Default workflow token | Read-only; cannot approve PR reviews |
| Fork PR workflows, if Actions is later enabled | Maintainer approval for all external contributors |

A weekly pip update configuration is in `.github/dependabot.yml`. The project
currently declares no third-party Python runtime packages. Repository dependency
features do not provide coverage for arbitrary host/VM images or OS packages.
Local verification evidence is not represented as remote GitHub CI.

GitHub lists a server-generated `Dependency Graph` workflow at
`dynamic/dependabot/update-graph`; its observed graph-update run completed
successfully. That is dependency infrastructure, not Grantweft correctness CI.
Dependabot may run GitHub-managed jobs independently of the ordinary project
Actions setting; see [GitHub's documented behavior](https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-on-actions).
No `.github/workflows` CI file is added by this publication.

The first attempt to set fork-PR approval while still Private was rejected by
GitHub because the setting applies to public repositories. It was applied and
read back after the authorized visibility change. Private-plan limitations on
branch/security features were resolved by publication, not by weakening checks.

## Public read verification

The final publication check uses unauthenticated GitHub/raw-file requests and
compares README, MIT LICENSE and the qualification/notice records to the committed
files. An owner-authenticated API response alone is not used as proof that readers
can access the repository. Repository settings can be changed later; this document
and snapshot describe the publication-time state.
