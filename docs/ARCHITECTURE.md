# Architecture and frozen transaction order

Status: four bounded explorations plus milestone 1 repair/restart; formal deployment acceptance remains separate.
Single Linux gateway process, one asyncio socket-authority loop, one bounded
SQLite worker thread, fixed client-certificate fingerprints/roles and one fixed
numeric TCP backend. Python >=3.12, stdlib ssl/asyncio/sqlite3/fcntl. No privileged
route/firewall mutations by the gateway. Namespace provisioning is test-fixture root.

## Authority

The loop owns every TLS/backend transport and the in-memory terminal fence.
The DB thread owns one SQLite connection, no sockets. The protected store is
0700; lock file 0600, stable inode, never deleted/replaced on startup. No child
worker, socket activation or inherited listener. Same-UID/root actors are trusted.
The lock is held through socket teardown and DB-thread exit; a second process
must fail before catalog recovery/listener creation. Kernel locks are not a
sandbox against a local user replacing the inode.

Client certificate chain is verified and DER certificate SHA-256 is explicitly
mapped to a principal/role. All grant IDs are bound to owner and fixed service ID.
The ID is not a bearer capability. Requesters cannot approve; historical operation
lookup is keyed by authenticated principal and operation UUID. Control connections
are single-request; current role/identity is checked on every connection.
TLS tickets are disabled; no early-data API is used. Certificate expiry while an
already-established session remains open and broader credential rotation/revocation
are not qualified; authorization TTL is the implemented session boundary.

## Transactions

1. Authenticate, enforce exact request fields, role, epoch and grant revision.
2. For an existing operation UUID/principal, require identical canonical payload,
   return original outcome explicitly labelled historical plus current state.
   Immutable durable results and mutable runtime grant objects are deep copies;
   expiry/persistence markers cannot mutate an earlier operation result.
   New epoch checks do not prevent reading one's retained historical outcome.
3. For a new approval, freeze `CLOCK_BOOTTIME now + approved duration` before
   entering the bounded queue. No retry/commit callback can extend this deadline.
   On macOS portable tests use monotonic fallback; actual suspend is untested.
4. The sole DB worker checks durable state/revision, commits grant, operation result
   and audit event in one SQLite DELETE/FULL transaction. Internal expiry marks
   use epoch/revision compare-and-set and require exactly one affected row.
5. On completion, the loop checks service generation, terminal fence and deadline.
   A commit is a durable result, not permission. Expired/superseded completion is
   stopped; a storage failure/timeout permanently retires this service generation.
6. Revocation/cancellation sets a local terminal fence and aborts sessions before
   attempting persistence. Queue-full/storage errors cannot undo that fence.
   Expiry is checked before each socket write as well as by a 20-ms polling loop.

Positive EOF/reset is required by the revised qualification observers. A socket
waiting timeout cannot prove termination; cleanup counts alone are not sufficient.

No waiting database operation runs on the socket-authority loop. SQLite lock wait
is 200 ms; application wait is 2 s, but blocked OS I/O is not thereby cancelled.
The DB thread and process lock remain alive until it exits or the process is killed.
Late future results are consumed but cannot restore authority. The runtime view
reports effective access, durable result/persistence and current session count.
An API cleanup flag COMPLETE means owned transfer tasks were removed after abort;
it does not prove a remote process stopped executing or all in-flight packets died.

## State machines

Persistent grant states:
`PENDING -> ACTIVE / DENIED / CANCELLED / EXPIRED`;
`ACTIVE -> REVOKED / EXPIRED`.
On boot all PENDING/ACTIVE become INVALIDATED and revisions increase, then epoch
increases within the startup transaction, before the listeners are created.
APPROVING is represented by the bounded in-flight operation map, not a new durable
state; it never grants data access. A terminal fence is monotonic per process.

Session states are implemented by registered task ownership:
`AUTHENTICATING -> registered CONNECTING -> OPEN -> abort/cleanup -> removed`.
Registration precedes asynchronous backend connect. Every post-connect/send checks
owner grant revision, epoch, terminal fence, deadline and service health. Immutable
UUIDs identify sessions; raw fd reuse never grants authority. Cancelled transfers
reap their direction tasks in finally blocks.

A simultaneous approval/revoke at the old revision can commit approval first,
then reject the queued revoke as stale. The loop has already fenced access and
retires the service, so the durable ACTIVE row is never an effective grant. Restart
invalidates it. This bounded exploration intentionally prefers global unavailability
over pretending the revoke was durably committed. Smooth targeted reconciliation
of that race is not implemented.

## Recovery and storage failure

On SIGKILL, only this process owns sockets; the kernel releases them. No session
continuity is promised. Restart/normal VM reboot never reuses an ACTIVE row as
permission. Corrupt runtime state/startup writes fail before serving. DELETE/FULL
is a chosen durability setting, not tested physical power-loss survival.

Bounded catalog refusal denies new requests without pruning existing grants.
If a required revoke cannot be persisted, access is still fenced and the service
becomes DEGRADED. It does not resume automatically after storage repair. Historical
records are retained, not silently forgotten. Audit capacity is finite and no
external tamper-resistant audit or write-once guarantee is supplied.

## Primary materials

- [Python SSL identity verification](https://docs.python.org/3.12/library/ssl.html)
- [Asyncio transport abort, buffering and EOF](https://docs.python.org/3.12/library/asyncio-protocol.html)
- [SQLite atomic commit and assumptions](https://sqlite.org/atomiccommit.html)
- [Linux CLOCK_BOOTTIME](https://man7.org/linux/man-pages/man2/clock_gettime.2.html)
- [Linux flock inode/open-file-description semantics](https://man7.org/linux/man-pages/man2/flock.2.html)

The milestone 1 status, finite SQLite page budget and operator recovery contract
are specified in [RECOVERY.md](RECOVERY.md). Runtime authority never resumes in
place after DEGRADED; a repaired startup invalidates previous grants. Catalog
headroom is recovered by an explicit finite budget increase, preserving history.

The shipped Type=notify systemd unit and root-only installation command are
specified in [DEPLOYMENT.md](DEPLOYMENT.md). Runtime keeps no root/capabilities;
DEGRADED stays alive until explicit repair/restart. The service does not use a
privileged worker or automatic online recovery.
