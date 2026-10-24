# Reviewed milestone 1 outcomes

Source fingerprint: `32e57f3573efd1d9b40ffd55fde677eb0c7766b8d41314dc61b70914c7d10fc4`.
[JSON](../evidence/latest.json) / [HTML](../evidence/latest.html) encode the same
`grantweft-recovery-review-v4` receipt. Two read-only agents reviewed implementation and evidence;
the main agent performed the new installed-package qualification. This is not an
independent VM reproduction, full operational release or production guarantee.
See [review findings](MILESTONE_1_REVIEW.md) for counterexamples and fixes.

## Formal implementation and recovered authority

Native macOS and installed Linux each passed the same **42 unique test IDs**:
36 formal service/CLI tests plus six observer/cleanup controls. Zero failures,
errors or skips. Native suite 30.35 s; Linux suite
36.30 s. These fixture-inclusive durations are not a platform
performance comparison. Linux: Python 3.12.3, SQLite 3.45.1,
OpenSSL 3.0.13 30 Jan 2024. Installed module hashes match frozen sources; runtime source was
removed from import reach before Linux tests. No remote CI result is implied.

The duplicate-fingerprint CLI regression requires prompt failure before creating
state, a writer lock or DB thread. This fixes a real error-plus-startup-hang defect.
The full gateway tests cover mTLS/ownership, slow commit, immutable history,
revocation/expiry, actual backpressure, capacity and repaired restart.

Seven installed-service scenarios passed in isolated namespaces with UID 65534,
forwarding read back as zero, real gateway forwarding and a failed direct backend
connect. A direct-connect timeout is bounded isolation evidence, not session closure.
Actual EOF is observed for every established holder; timeout is never closure.

| Scenario | Committed ops before / after boot | After-repair RSS KiB | FDs | Managed allocated bytes |
| --- | ---: | ---: | ---: | ---: |
| ops_full | 2 / 2 | 25,296 | 10 | 32,768 |
| events_full | 2 / 2 | 25,284 | 10 | 32,768 |
| grant_full | 3 / 3 | 25,288 | 10 | 32,768 |
| sqlite_full | 14 / 14 | 25,324 | 10 | 53,248 |
| disk_full | 2 / 2 | 25,296 | 10 | 32,768 |
| read_only | 2 / 2 | 25,296 | 10 | 32,768 |
| late_commit | 4 / 4 | 25,308 | 10 | 32,768 |

Each scenario reuses its same root. After writer stop and immediately after boot,
committed grant/operation/audit counts match; ordered operation/audit history
digests and catalog/writer.lock device/inode IDs match. All PENDING/ACTIVE rows
become INVALIDATED with revision+1; terminal rows are retained. Old data and new
operations using old epochs are refused. Fresh request plus separate approval
adds exactly one grant and two operations/audit events, then completes twenty
verified roundtrips. This checks retention and consistency, not physical durability.

The late approval is held past application timeout, then actually committed ACTIVE
on disk. Runtime access stays refused. After repair/restart, the exact timed-out
UUID returns a historical ACTIVE result, but data admission remains NO_ACCESS
before and after that replay. Reading history never executes an old approval.

Catalog-full admission has the expected refusal code. Operation/event-full revoke
cannot persist, but still fences and retires authority. Grant-full revoke remains
durably REVOKED/COMMITTED with READY health. Formal tests also require actual
expiry closure with full audit capacity and expiry-write failure.

SQLite page-limit FULL is real. The filesystem-full trial fills a 1-MiB tmpfs to
zero free bytes and attempts revoke, producing SQLITE_FULL. Live directory write
permission removal produces SQLITE_READONLY_DIRECTORY during revoke. After stop,
a separate actual readonly remount refuses startup at writer.lock opening with
EROFS. This does not inject failure inside SQLite's boot transaction or simulate
physical media. Permissions/capacity are repaired before a successful restart.

## Timing and memory scope

One VM trial verifies twenty 8,192-byte roundtrips, 163,840 bytes each direction,
in 2.447 ms after session admission; approval/TLS/setup are excluded.
A separate revoke RPC takes 40.571 ms including fixture client
launch, mTLS/control, persistence and local cleanup. Client EOF observation is
45.727 ms from its own earlier wait start;
these are distinct intervals, not repeated latency samples. Sessions after revoke:
zero. Ordinary workload point sample: 25,052 KiB RSS, 10 FDs,
32,768 managed allocated bytes.

Per-case samples above follow repair and fresh forwarding, not peak/growth tests.
Gateway RSS excludes client/backend/VM overhead; store excludes PKI, config, logs,
venv and VM image. `fault_phase_seconds` includes fixture induction and verification,
including late-commit readback after closure; it is not a closure/recovery bound.
No speedup, SLO, native/physical result, hard RSS bound or total disk quota follows.

## Reboot, evidence controls and limits

One normal VM reboot preserves ACTIVE/PENDING catalog bytes/hash/rows and operation
count until the new gateway is started. Boot UUID changes; epoch advances to
3; grants invalidate, old data returns NO_ACCESS and a
stale mutation returns STALE_EPOCH. Fresh approval forwards correctly. Startup is
manual; systemd automatic startup is not qualified.

The verifier rejects **60 corruptions**, including contradictory/missing late
refusal exits, missing catalog admission/revoke, lost old rows/counts/history/file
IDs and explicit cleanup errors. It also works under Python -O. Receipt validation
is not cryptographic proof or independent reproduction. All stages passed without
timeout; all owned processes/namespaces cleaned; dedicated VM/disk removed and
preexisting profiles unchanged.

[Original milestone evidence](../evidence/milestone-01.json) and
[initial milestone results](MILESTONE_1_INITIAL_RESULTS.md) remain historical;
[earlier exploration results](REVIEWED_EXPLORATION_RESULTS.md) and all failed
attempts are retained. Earlier measurements are not speedup/regression baselines.

DEGRADED still retires the whole service on some approval/revoke conflicts.
Repair requires restart and new approval. Catalog recovery raises finite limits
(up to configured bounds); it provides headroom, not GC, rollover or indefinite
operation. Formal systemd deployment, sustained resource behavior, broader control
pressure and credential lifecycle remain later gates. Power loss, actual suspend,
boot-zero-gap, arbitrary corruption repair and long-term stability are unqualified.
Private repository; no project license selected.
