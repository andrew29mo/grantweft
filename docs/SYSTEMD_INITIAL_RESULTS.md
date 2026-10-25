Historical pre-review deployment qualification; only the recorded sources are qualified.

Repository-visibility statements below describe their recorded revision.
Grantweft is now Public; see [publication checks](PUBLICATION.md).

License-status statements below describe the recorded pre-MIT revision. The
project now uses [MIT](../LICENSE); see [adoption review](LICENSE_REVIEW.md).

# Installed-service and recovery outcomes

Source fingerprint: `bdca477cf50634c7fb2bf923dcce2340a584d91977160bec0a730fe5b87eb4b7`.
[JSON](../evidence/systemd-initial-01.json) / [HTML](../evidence/systemd-initial-01.html) contain the same
`grantweft-systemd-v5` receipt. Native and installed Linux each pass the same
**44 unique tests**: 38 formal service/CLI/readiness tests and six observer/cleanup
controls, zero failures/errors/skips. Native suite 30.85 s;
Linux suite 38.16 s. Fixture suite duration is not a platform
performance comparison. Linux runtime: Python 3.12.3, SQLite 3.45.1,
OpenSSL 3.0.13 30 Jan 2024. Runtime Python files and shipped service unit match the frozen
source/wheel; runtime source is removed from import reach before Linux testing.

This deployment run is performed by the main agent. The earlier two-agent
milestone review is [historical](MILESTONE_1_REVIEW.md); it is not an independent
review or reproduction of these new deployment changes. No remote CI, physical
hardware or operational-production qualification follows.

## Actual installed systemd service

The runtime wheel's root installer installs the shipped unit and a dedicated
account. Only NetworkNamespacePath is added for isolated VM topology; ExecStart
is unchanged. Actual /proc argv matches the shipped command. Systemd Type=notify
accepts READY after boot recovery/TLS/listeners initialize; API health remains
separate from process readiness and backend availability.

Observed runtime UID **996** (all UID fields equal,
non-root), effective capabilities **0**, NoNewPrivs **1**. The loaded unit has
ProtectSystem=strict, empty CapabilityBoundingSet, control-group kill, Restart
on-failure, one-second restart delay, three-start/thirty-second limit and five-
second stop timeout. No product storage barriers or startup wrapper are used.

| Scenario | Actual observation |
| --- | --- |
| Explicit normal stop | 0.014 s systemctl interval; positive EOF, old PID absent, no service-UID processes; remains stopped during an additional 1.3-s observation |
| SIGKILL takeover | New MainPID and InvocationID, NRestarts increases, epoch 2 → 3; old data/operations refused, fresh approved forwarding works |
| DEGRADED under real catalog exhaustion | Revoke CATALOG_FULL still closes tunnel; active process/invocation/restart count remain unchanged through the observed interval |
| Operator repair | Same catalog/history/counts/lock identities retained; larger finite limit plus explicit restart advances epoch; old data/operations refused, fresh approval works |
| Unresponsive main / stop timeout | Root ptrace stop observed; actual SIGKILL after configured timeout; Result=timeout, old PID absent, no service-UID process; repaired startup refuses old authority |
| Invalid-config restart limiting | 3 actual DUPLICATE_IDENTITY journal exceptions, journal rate limit, Result=exit-code, stable NRestarts=3; MainPID=0, no service-UID process; catalog unchanged |
| Repair after start limit | Correct config and explicit reset/start; initialized new epoch, fresh approved roundtrips; final stop/cleanup succeeds |

Crash-takeover timer: **1.115 s**, from the root fixture's
kill-command start to the new active service and status observation. This is one
controlled sample, not a recovery bound. Old client closure happens on process
kill and has a different measurement interval. Forced-stop timer:
**5.271 s**, from systemctl stop launch through ptrace exit/reap
and stop observation; client positive EOF interval **5.266 s**
starts earlier. The ten-second client observation budget permits the configured
five-second stop timeout; it does not turn timeout into closure.

Forced stop is an explicit root-only ptrace fault, not storage failure, deadlocked
kernel I/O, sudden power loss or a product debug flag. Systemd SIGCONT makes a
simple SIGSTOP insufficient for exercising stop timeout. See [deployment design
and primary materials](DEPLOYMENT.md).

## Linux VM measurements

Installed systemd service: twenty ordered 8,192-byte roundtrips,
163,840 verified bytes each direction in **1.980 ms after
session admission**. Point observation: **25,316 KiB RSS**, **12 FDs**,
**32,768 allocated managed-file bytes**.

The separate manual namespace workload remains in `cases`: twenty roundtrips in
2.671 ms, revoke RPC
38.925 ms including client launch/mTLS,
and 25,060 KiB sampled process RSS. These are separate
single VM trials, not baseline comparisons, speedup, peak/endurance measurements
or native performance. Roundtrip timers exclude TLS/backend admission and approval;
RSS excludes fixtures/VM overhead; store excludes PKI/config/venv/journal logs/VM
image. No total disk/RSS or remote application-termination bound is claimed.

## Retained recovery coverage and evidence controls

The same run retains seven installed-runtime recovery scenarios: grant/operation/
event capacity, SQLite page-limit FULL, zero-free-space tmpfs, live directory write
denial plus actual readonly-filesystem startup, and approval committed after its
application timeout. Committed counts, history digest, catalog/lock identities and
old grant transitions are compared before/after repair. Exact timed-out UUID replay
returns historical ACTIVE while actual data admission remains NO_ACCESS. Fresh
request/approval requires the expected new catalog entries.

A separate normal VM reboot retains ACTIVE/PENDING journal bytes/rows/hash until
manual gateway recovery, then advances epoch and refuses old authority. The service
unit is not enabled in this qualification: this is not formal systemd boot-autostart
or boot-zero-gap evidence. The service drop-in is removed and all unit processes
stopped before namespace cleanup and reboot. VM/disk deletion and preexisting
profile preservation are verified.

**72 corrupted-record controls** are rejected, also with Python -O,
including missing service, root privileges/capabilities, wrong unit, no new
invocation, fake stop timeout/restart limiting and failed catalog retention.
This is structural/invariant verification, not cryptographic proof or independent
reproduction. Failed/superseded JSON/HTML remain intact in [evidence](../evidence/README.md).

Finite limits still require explicit repair and new approval; no GC/rollover,
indefinite uptime or silent in-process reset. Global DEGRADED on some races remains
an availability cost. Formal boot-autostart, clean-VM operator walkthrough beyond
the scripted fixture, bounded sustained-resource observations, credential lifecycle,
power loss, actual suspend and boot-zero-gap remain unqualified. Repository stays
Private; no project license selected.

The failed reboot observation in attempt 06 is retained. The final runner sets
AccuracySec=1s on its VM reboot trigger and keeps the original 120-second boot-ID
observation deadline; no service recovery latency is inferred from this timer.
Atomic startup-receipt publication and its mid-write regression are included.

The systemd workload resource sample includes one additional live idle tunnel
used by the following stop test. The separate manual sample has no such held
tunnel. FD/RSS values must not be compared as equivalent workloads.
