# Historical reviewed exploration outcomes

Superseded by milestone 1; these numbers qualify only the source fingerprint below.

Recorded source fingerprint:
`e56c6648ae3439fc3148e9b3b28b0ba473fd7fc6e4c7b602f24ab9466569a204`.
[JSON](../evidence/review-01.json) and [HTML](../evidence/review-01.html) retain the same
complete `grantweft-review-v2` record. This is a bounded exploration qualification,
not an operational MVP, independently reproduced third-party audit or production
readiness claim. Two agents inspected the implementation/evidence; the parent
ran the new installed-package VM qualification.

## Actual outcomes

| Group | Observed evidence | Boundary |
| --- | --- | --- |
| Identity / transaction | Real mTLS, separate approver, owner refusal; precommit fixed deadline, delayed commit and immutable original results before/after restart | DELETE/FULL SQLite; no physical power-loss qualification |
| Transfer / revoke | Ordered bytes, half-close, malformed frames, deterministic post-connect pause/revoke, live/idle termination with positive EOF/reset | No recall of kernel/in-flight bytes or backend effects |
| Pressure / storage / time | Queue/session/catalog/handshake refusal, blocked DB plus elapsed expiry, SIGSTOP/resume, late result cannot reactivate; backend write queue exceeds high watermark before revoke | No actual suspend, ENOSPC/EROFS/FULL filesystem, unlimited pressure or Internet DoS qualification |
| Recovery / topology | Installed wheel and matching module hashes, UID 65534, client/gateway/backend namespaces, observed forwarding=0, actual reboot and preserved pre-recovery journal; stale refusal and fresh verified access | Manual gateway startup after normal reboot; no systemd-autostart, power loss, boot-zero-gap or session continuity |

Both platforms passed the same 34 unique test IDs with zero failures/errors/skips:
28 tests start the actual gateway/mTLS/backend implementation; six explicitly test
observers, stream-fragmentation checks and cleanup failure handling. The latter
are evidence controls, not substitutes for formal product tests.
Native suite: 23.34 s; installed Linux suite: 25.93 s. Fixture-inclusive suite times
are not comparative performance. Linux used Python 3.12.3, SQLite 3.45.1 and
OpenSSL 3.0.13 from the guest. No arbitrary runtime-build qualification follows.

## Linux VM measurements

- Twenty 8,192-byte roundtrips, 163,840 verified bytes per direction: 2.682 ms.
  Timer starts after mTLS/backend admission and excludes approval/setup. Responses
  are reassembled across DATA frames, not assumed to preserve TCP read boundaries.
- Live-session revoke RPC: 37.707 ms, including namespace client startup, mTLS,
  request, persistence and local cleanup response. The client observed actual
  `EOFError`, not an idle timeout. Session count after revoke: zero.
- Client closure interval: 39.929 ms from its own wait start, which precedes the
  RPC measurement. These are distinct intervals, not comparable latency samples.
- Gateway point observation after the roundtrip trial: 25,044 KiB RSS, 10 fds.
  Allocated managed-store bytes: 32,768. Store count excludes PKI/configuration,
  venv, VM filesystem and logs. Gateway RSS excludes fixture clients/backend.

These are single controlled VM observations, not a baseline comparison, native
performance, physical-device result, peak memory, deployment size, long-term bound
or SLO. Previous values remain in the historical receipt, not treated as a speedup
or regression comparison.

## Normal reboot witness

The gateway was SIGKILLed with PENDING and ACTIVE grants. Catalog bytes hash,
sorted grant rows and operation count were saved before reboot. After the boot ID
changed, all three matched before the new gateway ran. Then epoch advanced to 3,
old grants became INVALIDATED/DENIED, actual old data admission returned NO_ACCESS
and an old mutation returned STALE_EPOCH. A new request/approval completed twenty
verified roundtrips. Namespace/backend fixtures were recreated after boot; they
are not installed boot services.

Direct backend access had a timed-out connect attempt while the gateway path
successfully reached the same backend, and kernel ip_forward was read back as 0.
That timeout means this bounded direct-connect attempt did not establish; it is
not used as proof of closing an already-established session or WAN isolation.

## Controls, failures and cleanup

The new verifier rejected 33 corrupted records and also ran under `python -O`.
It requires the correct platforms, full stage order, exact unique test accounting,
source consistency, positive closure reason, pre/postboot witnesses, raw refusal
outcomes, a fresh verified workload and complete cleanup. It does not provide
cryptographic protection against fabrication of an entire receipt.

All qualification stages exited successfully without timeout. Every case cleaned
its registered processes and namespaces, with no cleanup errors. The dedicated
VM/data disk were removed and the existing relay profile remained Stopped.

The original 25-test run is retained as [attempt 03](../evidence/attempt-03.json),
with matching HTML. Its closure observer and incomplete validator were flawed;
it is not current qualification. Initial draft and two failed topology attempts
remain unchanged. [Original results](INITIAL_EXPLORATION_RESULTS.md) preserve their
context; [review findings](REVIEW.md) explain actual counterexamples and repairs.

## Remaining operational limitations

Concurrent approval/revoke revision conflict still fences access globally and
enters DEGRADED. It does not transparently reconcile the affected grant. Restart
invalidates previous grants and requires new approval. Catalog/audit rows have
finite caps and no automatic GC/rollover. Credential lifetime/replacement,
operational packaging/recovery workflow, real filesystem capacity faults and
broader control-plane pressure remain MVP gates. Untested power loss, actual
suspend, systemd autostart, boot-zero-gap and long-term stability are not passed.
