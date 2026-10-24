# Four exploration outcomes

Final source fingerprint:
`4fad58e67d7dfb592afb6428724f4abdae733bf173a980c845faf3853e6df93b`.
[JSON](../evidence/latest.json) and [HTML](../evidence/latest.html) contain the same
complete record. This is a controlled exploration qualification, not an operational
MVP or production deployment claim.

| Group | Observed result | Important boundary |
| --- | --- | --- |
| Identity / transaction | Formal mTLS clients, separate approver, ownership refusal; fixed deadline and delayed commit; deduplicated history after revoke/restart | SQLite journal mode DELETE, synchronous FULL; no physical power-loss test |
| Transfer / revoke | Real ordered payload, half-close response, malformed frames, live/idle/slow sessions, deterministic post-connect/pre-admission pause then revoke | Cannot retract kernel/in-flight bytes or backend effects; not every kernel/TLS callback schedule tested |
| Time / storage / capacity | Elapsed expiry and SIGSTOP/resume; blocked DB does not block live expiry; queue/session/catalog/handshake limits; storage-error hook and late completion retire access | No real suspend, ENOSPC/EROFS filesystem or external DoS qualification; saturation can retire the service |
| Recovery / topology | Same 25 test IDs/platform; installed wheel/module provenance; nobody UID; three namespaces/no bypass; real boot-ID change, unchanged pre-recovery journal, old authorization refused and fresh grant usable | Service manually started after ordinary VM reboot; no systemd-autostart, boot-zero-gap, power-loss or session continuity claim |

Native macOS suite: 25 tests, zero failures/errors/skips, 20.95 s.
Linux installed-wheel suite: same 25 IDs, zero failures/errors/skips, 23.35 s.
Test-suite durations include fixtures and are not a platform performance comparison.
Linux used Python 3.12.3, SQLite 3.45.1 and OpenSSL 3.0.13 (guest packages).
The service uses SQLite rollback journals, not WAL; this record is not a statement
that arbitrary SQLite builds or WAL workloads are qualified.

## Controlled Linux VM observations

- Twenty 8,192-byte roundtrips, 163,840 verified bytes each direction, 2.571 ms.
  Timer starts after mTLS/backend admission; it excludes setup, approval and
  session establishment. No baseline, repeated distribution or speedup claim.
- Revocation RPC: 32.610 ms, including spawning the namespace fixture client,
  mTLS, control request, durable update and the local cleanup response.
- The already-open client observed connection termination 43.866 ms after its
  own wait began, which precedes the revoke RPC; this is a different interval,
  not a directly comparable revocation latency. Session count after revoke: zero.
- One gateway process sampled after the roundtrip workload: 25,056 KiB RSS,
  10 fds; allocated managed-store bytes: 32,768. This excludes TLS client/backend
  processes, PKI/configuration, virtual environment, VM filesystem and raw logs;
  it is not whole-system memory, deployment size, peak or a hard resource bound.

No continuous resource-growth qualification is claimed. The tiny controlled
backend and VM network do not represent WAN or production workloads.

## Recovery witness

Before reboot the actual gateway was SIGKILLed, leaving PENDING/ACTIVE rows in
SQLite. The fixture then saved the catalog bytes hash, sorted grant rows and
operation count. After a changed boot ID and before any new gateway, those
witnesses matched exactly. Only then did the installed gateway start, increment
epoch and invalidate old grants. Actual old data admission and stale mutation
were refused; a newly requested/approved grant passed twenty fresh roundtrips.
Namespace/backend fixtures are recreated after boot, not persistent service units.

## Failures retained, not promoted to passes

- `initial-portable-failure.json`: first 18-test draft had 15 errors and one
  failure. Normal Store commands incorrectly accessed the internal action field;
  corrected command dispatch. Missing-certificate denial can be EOF as well as
  TLS error; the test now explicitly requires rejection instead of rejecting a
  valid EOF outcome. Actual certificate checks remain enabled.
- `attempt-01.json/html`: both platforms passed 24 tests, but VM topology failed
  moving interface `br`: ip interpreted its name as the broadcast option. The
  run failed and its VM cleanup succeeded.
- `attempt-02.json/html`: both platforms passed 25 tests, but the corresponding
  link-up call still lacked explicit `dev`; the run failed and cleanup succeeded.
  Every variable interface link-set call was then made explicit. A source change
  during that run is also recorded; it is not a qualifying receipt.
- The pre-recovery journal comparison was normalized to JSON lists before the
  final run; Python tuple/list representation must not masquerade as a journal
  change. Byte hash equality remains an independent check.

Final run: frozen source unchanged, all stages successful without timeouts,
19 corrupted report variants rejected, owned processes/namespaces reaped, VM and
its data disk removed, and preexisting Colima profile statuses unchanged.

## Remaining decisions

Simultaneous approval/revoke revision conflicts currently cause global DEGRADED,
not smooth per-grant reconciliation. Historical records have finite row caps and
no GC/rollover. A complete operator recovery workflow, certificate lifetime/
replacement, supported service packaging and broader storage/pressure testing
remain operational MVP gates. See [acceptance](ACCEPTANCE.md).
