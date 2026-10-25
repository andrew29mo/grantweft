# Prepublication review

Date: 2026-10-25 (Asia/Taipei). Reviewed parent:
`1210234a34cd2e9ba102c89ddd884cb7603e3702`.
Repository: `andrew29mo/grantweft`, main, Private, sole collaborator/owner
`andrew29mo`. No project license selected or granted. Visibility/access/license
are checked through the authenticated GitHub API; this review does not publish
or grant access to the repository.

## Outcome and documentation repairs

No new runtime defect was reproduced in this review. Formal program, tests,
installed wheel and shipped service unit are unchanged. Documentation repairs:

- Architecture status now describes the delivered installed-service/boot-recovery
  MVP and bounded observation, replacing an outdated milestone-only status.
- Deployment scope separates the namespace-only lifecycle-stage drop-in from the
  enabled-boot stage's additional explicit VM setup/backend dependencies. Both
  retain the shipped ExecStart and unprivileged gateway.
- Protocol wording distinguishes rejected NaN/Infinity literals from numeric
  overflow, which duration validation separately rejects. No broader JSON numeric
  validation or new protocol capability is claimed.
- Historical review pages and source fingerprints are explicitly historical or
  recorded. Their source-specific results remain separate from current evidence;
  archived JSON/HTML bytes and failed outcomes are not rewritten.

## Correctness and evidence provenance

Current source fingerprint:
`a05bc2a1f07b564345fb685a0713e6db4e81e14863bff2e3ebdca944a97b82ec`.
The current manifest equals the source-bound v8 receipt. Runtime wheel SHA-256 and
installed .py/.service hashes match; its inventory contains only runtime modules,
the shipped unit and distribution metadata. Product source was removed from the
Linux test checkout's import reach before the recorded qualification.

The additional macOS run in this review passes **51/51 tests**, zero failures,
errors or skips, in 30.53 seconds. Its IDs and manifest exactly match
the paired Linux receipt. [Supplemental receipt](../evidence/prepublication-native-01.json).
This is a new native correctness run; suite duration is not a performance claim.
The existing paired native/Linux/VM qualification is retained intact.

No new Linux VM run is represented by this documentation-only review. Instead,
the unchanged sources are checked against the prior complete installed-wheel VM
run, its raw receipts and published evidence. That run includes actual systemd
lifecycle and boot enablement, old-journal witnesses, readonly cross-boot repair,
seven storage/recovery scenarios and the same-process forty-cycle observation.
The earlier two-agent review is documented in [CLOSEOUT_REVIEW.md](CLOSEOUT_REVIEW.md);
this prepublication pass is a main-agent review.

Current JSON equals the raw qualification receipt. Current HTML equals its
renderer; all historical HTML/JSON pairs carry identical records. Separate
native/Linux receipt objects match latest. The offline verifier passes in ordinary
and optimized Python and rejects all **133 corruption controls**. Source changes,
failed/timed-out stages or incomplete cleanup cannot pass the qualified contract.

## Performance claims and boundaries

The current results report accurately states the measurement boundaries:

- The 20-roundtrip VM point measurement is **1.962 ms after admission**, with
  **25,316 KiB** sampled main-process RSS, **12 FDs** and one additional held idle
  tunnel. It excludes TLS/backend admission and is not a comparative speedup.
- The distinct 40-cycle observation lasts **600.001 s**, retaining one process,
  epoch and service invocation. Idle FDs are **10**; post-warmup RSS is
  **26,412–28,188 KiB**, final RSS **27,932 KiB**. RSS rises; no plateau/no-leak or
  peak-RSS claim is made. Fixed resource/workload gates are unchanged.
- Configured grants grow **14→54 of 96**, operations/events each **28→128 of 512**;
  these finite capacities exceed defaults and are disclosed. No GC/rollover or
  indefinite-operation guarantee is supplied. Allocated managed-file blocks grow
  **53,248→122,880 bytes**, excluding the VM image/runtime/PKI/logs.
- **1.148 s** SIGKILL-to-new-active/status is one controlled observation, not an
  outage upper bound. Normal VM shutdown/reboot is distinct from sudden power loss.

Linux timings/RSS are virtualized observations. Native correctness-suite duration
is separate. Neither sudden power-loss recovery nor boot-zero-gap protection,
actual suspend, long-term endurance, arbitrary production network provisioning or
hostile local-root/same-UID behavior is qualified. Historical failed attempts are
explicitly retained as failures. See [measured results](EXPLORATION_RESULTS.md).

## Privacy, repository contents and license state

The parent revision's reachable Git history was scanned across **194 unique blob
objects** and its historical path inventory. Current candidates and metadata are
also inspected for private workstation paths, private-key blocks, common GitHub/
cloud/chat token formats and accidental credential/database/build artifacts.
No such exposure was found. Author/committer addresses use GitHub noreply; the
public GitHub identity is intentional. These inventory/pattern checks do not
certify absence of every possible secret format.

Tracked files are source, tests/tools, package configuration, documentation and
sanitized receipts. No virtualenv, wheel, database, raw log, certificate/private
key, VM image, .env, personal AGENTS or orchestration notes is tracked. Existing
ignore rules cover generated results and the actual fixture's PEM/key/SQLite
files. Temporary PKI and raw diagnostics remain local and ignored.

README and pyproject agree that no project license is selected. There is no
LICENSE file, license field or license grant in wheel metadata, and the GitHub
licenseInfo is null. The runtime declares no third-party Python packages; it uses
Python's standard library with host OpenSSL/SQLite. Their upstream terms, along
with build/VM tools, are separate; no upstream source/binaries are vendored by
this repository. No license or repository visibility is changed by this review.
