# Historical reviewed installed-service outcomes

License-status statements below describe the recorded pre-MIT revision. The
project now uses [MIT](../LICENSE); see [adoption review](LICENSE_REVIEW.md).

Archived v6 source-specific run; see [current results](EXPLORATION_RESULTS.md).

Source fingerprint: `032ac1d3d22e26b602013e878667e1b29d8fa3ad48da826d69227a66f0d9327a`.
[JSON](../evidence/systemd-reviewed-01.json) / [HTML](../evidence/systemd-reviewed-01.html) encode the same
`grantweft-systemd-review-v6` receipt. Two read-only agents reviewed runtime and qualification;
the main agent performed the new source-bound installed-package VM run. The
second reviewer also checked this run's raw logs, HTML, hashes and controls.
That offline review is not an independent VM reproduction or hardware test.
[Review findings](DEPLOYMENT_REVIEW.md) distinguish acceptance holes from observed
product failures. Runtime gateway, installer and shipped unit are unchanged.

## Formal tests and installed service

Native macOS and installed Linux each passed the same **46 unique test IDs**:
**38 formal implementation/CLI/readiness tests plus eight observer/cleanup controls**,
zero failures, errors or skips. Native suite: 30.28 s; Linux:
36.86 s. Fixture duration is not platform performance.
Linux runtime: Python 3.12.3, SQLite 3.45.1, OpenSSL 3.0.13 30 Jan 2024.
Installed runtime .py/.service hashes match frozen source and wheel; runtime
source is removed from import reach before Linux tests. No remote CI is claimed.

The installed service uses the shipped unit, with only a network-namespace test
drop-in. Actual process PID, argv and four UID columns are checked at initial
start, normal restart, crash takeover, operator repair, stop-timeout recovery and
restart-limit repair. All six observations run as UID 996,
with zero effective capabilities and NoNewPrivileges=1, bound to the corresponding
active MainPID and valid invocation. Unit security settings and fixed restart/stop
budgets remain checked. The systemd stage independently observes forwarding=0,
a failed direct backend connect, and successful authenticated proxy forwarding.
That bounded connect failure is not WAN or hostile-root isolation proof.

| Scenario | Qualified observation |
| --- | --- |
| Normal stop/restart | Positive EOF, no service-UID process, old PID gone, no restart during the observed stable interval; new epoch and old authority refusal |
| SIGKILL takeover | New live MainPID/invocation, increased restart count, new epoch; complete old-grant invalidation and actual old data/operation refusal |
| DEGRADED | Consistent DEGRADED health, complete DENIED/zero-session status; all 4 old grants individually return NO_ACCESS using their owners' certificates; new request returns DEGRADED |
| Operator repair | Same catalog/history/counts/file identities; every PENDING/ACTIVE row becomes INVALIDATED with revision+1; all 4 old grants still return NO_ACCESS before fresh approval |
| Stop timeout | Root ptrace stop; actual final SIGKILL, Result=timeout, no remaining service process; new initialized recovery remains unprivileged and denies old authority |
| Restart limit | Three actual DUPLICATE_IDENTITY exceptions, explicit rate-limit journal message, stable restart count 3, MainPID=0; explicit config repair/reset/start succeeds |

Every repaired/initialized state snapshot precedes fresh request/approval. Old
rows must remain present; partial status pages, residual sessions, ALLOWED old
rows or unchanged ACTIVE catalog rows fail qualification. The old UUID/history
replay boundary and seven separate storage/capacity/late-commit scenarios retain
actual installed-runtime coverage. Existing atomic ready.json publication is
challenged by pausing the actual startup write midway: final file absent until
complete, then valid PID/epoch and authenticated status. It is not a pure rendering
test, fsync durability test or live-readiness guarantee for stale files.

## Timing and resource scope

One systemd VM trial verifies twenty ordered 8,192-byte roundtrips (163,840 bytes
each direction) in **1.865 ms after admission**; TLS/backend
admission and approval are excluded. Sampled main-process RSS **25,308 KiB**,
**12 FDs**, **32,768 managed allocated bytes** includes an
additional held idle tunnel for the following stop test. Clients/backend/VM
memory, PKI/config/venv/logs/VM image are outside those scopes.

Normal stop command interval: 0.013 s.
SIGKILL-to-new-active/status observation: 1.181 s.
Root-ptrace stop-timeout interval: 5.212 s, with positive client EOF
observed over its distinct earlier-started wait interval. These are single VM
observations, not an outage bound, peak, speedup, hard resource cap or long-term
stability result. Ptrace is root fault injection; it does not qualify uninterruptible
kernel I/O or physical-media failure. The separate manual namespace point sample
has no held tunnel and is not an equivalent comparison baseline.

## Controls, reboot and boundaries

The verifier rejects **95 corrupted receipts** in both ordinary and optimized
Python. New controls cover the systemd stage's isolation, non-running/root/wrong-
argv takeover, PID binding, contradictory health/authority, incomplete old-grant
probe sets and failed catalog transitions. Two new observer tests count separately
from formal product tests. Structural checks do not authenticate fabricated data.
All stages exit successfully without timeout; service/drop-in/process/namespace
cleanup completes, dedicated VM/disk are removed and preexisting profiles unchanged.

One normal VM reboot still uses a preserved ACTIVE/PENDING journal witness before
manual gateway recovery. Boot ID changes, old grants invalidate, stale operations
refuse and fresh forwarding works. The unit is not enabled: this does not qualify
systemd boot-autostart, boot-zero-gap or power loss. The VM reboot trigger retains
AccuracySec=1s and the original 120-second observation deadline; that timer is not
service recovery performance.

[Original deployment result](SYSTEMD_INITIAL_RESULTS.md),
[prior reviewed recovery](RECOVERY_REVIEWED_RESULTS.md) and all failed receipts
remain source-specific historical evidence, not rerendered passes. The current
review found acceptance gaps; it did not establish that the original VM ran as
root, revived grants or leaked a process. [Deployment commands](DEPLOYMENT.md)
retain the same installer/runtime contract.

Global DEGRADED can disrupt unrelated grants. Repair raises finite limits and
requires new approval, without online reset, automatic GC/rollover or indefinite
operation. Formal boot-autostart, power loss, actual suspend, kernel-I/O hangs,
long-term resources and hostile local root/same-UID processes remain unqualified.
Repository remains Private; no project license selected.
