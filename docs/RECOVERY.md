# Milestone 1: bounded repair and restart

The gateway has two runtime health states: READY and DEGRADED. DEGRADED is a
monotonic retirement of the current process authority. It aborts existing
sessions and refuses new mutations/admissions. Repairing storage in place does
not clear that latch. There is deliberately no online reset/re-enable command.

`status` remains a read-only in-memory mTLS operation. It includes `health`, the
first `failure` code/action/SQLite error name and CLOCK_BOOTTIME observation,
`recovery`, effective grant access, persistence markers and catalog capacity.
No raw exception text, database path or credentials are returned. A failure time
is a process clock reading, not wall time or an outage deadline. In DEGRADED,
capacity counts are last-observed values with `exact:false`: an already queued
transaction may subsequently commit. They must not be interpreted as durable
current counts. Counts are also inexact while a mutation is in flight. A response error is not a successful persisted revocation.

## Capacity and failures

| Condition | Response and effective behavior | Repair |
| --- | --- | --- |
| Grant row limit reached | GRANT_FULL; retain existing rows; established access stays subject to ordinary revoke/expiry | Increase finite max_grants, then restart |
| Operation/audit limit reached | CATALOG_FULL for a new mutation; no pruning; revoke/cancel fences first and retires if it cannot persist | Increase finite max_ops/max_events, then restart |
| Queue full | DB_QUEUE_FULL; revoke/cancel fences first and retires if enqueue fails | Resolve pressure and restart if DEGRADED |
| SQLite FULL / filesystem full / write-denied directory | STORAGE_FAILED, retire all access; status contains actual SQLite code | Restore writable capacity and restart |
| DB wait deadline | STORAGE_FAILED, retire generation; worker can still commit late | Resolve blockage; wait for process exit or terminate it; restart |
| Expiry persistence failure | Access already fenced, EXPIRY_PERSIST_FAILED, retire all access | Repair storage, restart |

An internal expiry update does not allocate an operation/audit row; it still needs
SQLite write/journal space. The absence of an audit slot never postpones the
in-memory deadline or makes an expired grant usable. SQLite `max_store_pages`
(default 1024, allowed 8–4096) bounds the database page count. Bytes depend on the
existing database page size (new default SQLite databases in the tests: 4096).
Rollback journals, TLS buffers, logs, config, keys and free filesystem capacity
are separate. This is not a total disk/RSS quota. A budget below an existing
page count fails startup with STORE_PAGE_LIMIT; it does not shrink/delete data.

## Operator recovery procedure

1. Read authenticated status if reachable; preserve the error response and current
   failure/capacity view. If the control listener is saturated or process is
   unresponsive, use trusted local process supervision. Status is not out of band.
2. Stop the gateway and verify the owning process exited. Keep the store directory,
   catalog and stable writer.lock inode intact. Never unlink the lock or delete
   catalog.sqlite to make the gateway start.
3. Repair the underlying filesystem or adjust explicit finite catalog/page limits
   in the operator-owned configuration. Catalog limits are bounded at 4096 each.
   Do not remove SQLite journal files or edit grants/epochs. Preserve a stopped
   store copy for diagnosis when needed.
4. Start the same gateway with the same state root. Boot recovery must commit a
   new epoch and invalidate old PENDING/ACTIVE grants before any listener opens.
   A failed boot write must exit without serving. ready.json is only a receipt
   of a past startup, not an authenticated live readiness check.
5. Establish a new authenticated status connection. Confirm the new epoch, READY,
   old grants denied and capacity with sufficient headroom. Submit a fresh request,
   obtain separate approval and verify the required backend operation.

Previously committed operation retries remain explicitly historical and include
current denied state. Reading a historical result never executes the old action.
A new operation UUID with an old epoch is rejected. Existing sessions, old grants
and old approvals are not revived after recovery.

This milestone uses increased finite limits for catalog recovery, not deletion,
archival, rollover or a new blank database. Once those finite limits are exhausted,
continued service requires a separately designed lifecycle. No indefinite uptime
or automatic GC is claimed. Startup/service packaging and systemd automatic restart
remain later milestones. Normal VM reboot evidence exists; abrupt power loss,
actual suspend, boot zero-gap and long-term endurance are unqualified.

The live read-only scenario removes directory write permission while the real
SQLite connection remains open, forcing journal creation to fail. After stopping
the gateway, the fixture remounts that tmpfs read-only and separately tests startup
refusal, then restores read/write mode and directory permissions. A live remount
was refused by Linux as busy; that failed attempt is retained, not counted as
passing EROFS injection. These are VM filesystem tests, not physical-media failures.

A corrupt or unrecoverable catalog is not automatically discarded. It requires
separate operator diagnosis/restoration; the tested writable-capacity repair
workflow does not qualify recovery from arbitrary journal corruption.
