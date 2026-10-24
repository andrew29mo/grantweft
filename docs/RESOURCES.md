# Frozen default exploration budgets

| Resource | Default | Failure behavior |
| --- | ---: | --- |
| Raw data connections, including handshakes | 20 | Abort new excess accept before TLS |
| Raw control connections, including handshakes | 8 | Abort excess; not an Internet DoS guarantee |
| Active/connecting backend sessions | 16 global, 4 per principal | SESSION_FULL; no backend dial |
| TLS handshake | 2 s | Abort/release connection slot |
| DB queue | 8 waiting + 1 active | DB_QUEUE_FULL; a revoke first fences access |
| DB operation wait | 2 s | DEGRADED, stop all sessions; late result cannot activate |
| SQLite lock busy timeout | 200 ms | Refusal/error; not an OS-I/O cancellation guarantee |
| New grant rows, including terminal rows | 64 | GRANT_FULL, no eviction |
| Operation result rows | 256 | CATALOG_FULL |
| Audit event rows | 256 | CATALOG_FULL |
| SQLite database pages | 1024 (8–4096 configurable) | SQLITE_FULL; DEGRADED |
| PENDING waiting window | 60 s | Expire/fence |
| Approved duration | 0.2–900 s | Reject outside range; short values enable real timer tests |
| Frame/read chunk | 16 KiB | Reject oversized frame |
| StreamReader limit | 16 KiB | Backpressure; not a hard total memory cap |
| StreamWriter high/low watermark | 16 KiB / 4 KiB | Await drain; does not cap TLS/kernel buffers |
| Complete next tunnel frame/backend read | 10 s | Abort stalled session |
| Control next frame | 3 s | Abort stalled client |
| Status page | 16 grant rows | Explicit cursor; no silent history eviction |

Config may reduce budgets for targeted tests. Positive finite values and bounded
integer counts are required. No hard RSS ceiling, total-CPU isolation, unbounded
endurance or fixed FD consumption is promised. Control/data listener separation
protects against the tested bounded data pressure, not all shared-CPU/TLS/control
floods. Control saturation still refuses new controls; status/revoke are not magical
out-of-band paths.

Catalog/audit fullness is a stop condition, not automatic rollover. New requests
are denied; a revoke that cannot record its event stops traffic and retires the
service. This first version requires explicit operator repair/restart and new
approval; no retention/archival policy is implemented. Resource measurements must
include runtime TLS overhead and all owned child processes, rather than treating
watermarks as proven RSS caps.

The review adds an actual transport-queue high-watermark observation before the
blocked-consumer revoke test. This counter is an observed pressure event, not a
maximum memory guarantee. Denial requires a formal refusal response; termination
requires EOF/reset, with timeout reported as failed observation.

Milestone 1 recovery preserves the same catalog/lock and increases explicit finite
limits only after stopping the gateway. Counts are marked inexact while DEGRADED.
SQLite page limits exclude rollback journals and other deployment files. See
[recovery procedure](RECOVERY.md). A boot budget smaller than the existing page
count fails before listening.
