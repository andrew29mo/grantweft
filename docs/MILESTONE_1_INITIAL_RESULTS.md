Superseded by the reviewed milestone; this document describes only its recorded sources.

# Historical initial milestone 1 outcomes

Recorded source fingerprint: `907560f00ba0d95eff7a1b5d7e29883542c76d31a48a5857253f89300b058f40`.
[JSON](../evidence/milestone-01.json) / [HTML](../evidence/milestone-01.html) contain the same
complete `grantweft-recovery-v3` record. This qualifies milestone 1 on the recorded
sources, not a complete operational release or independent third-party audit.
The earlier two-agent review is historical; this milestone was implemented and
qualified by the main agent using the reproducible installed-package runner.

## Formal implementation and VM evidence

Both native macOS and installed Linux passed **41 identical unique test IDs**:
35 formal gateway/mTLS/backend tests plus six observer/cleanup controls, with
zero failures, errors or skips. Native suite: 30.29 s;
Linux suite: 36.12 s. These fixture-inclusive suite durations
are not native-versus-VM performance comparisons. Linux runtime: Python
3.12.3, SQLite 3.45.1, OpenSSL 3.0.13 30 Jan 2024.

The runtime wheel hashes match the frozen source; runtime product source was
removed from Linux import reach before testing. The unprivileged UID-65534
gateway used three network namespaces. Forwarding was read back as disabled;
the direct backend connect timed out while real gateway forwarding succeeded.
That bounded connect failure is not proof of WAN isolation or session termination.

Seven fresh-root scenarios passed. Repair within each scenario reused the same
catalog and lock inode, advanced epoch, refused old data and new operations using
the old epoch, then required fresh request/approval and twenty verified roundtrips.
Each established holder observed actual EOF, never timeout-as-closure.

| Scenario | Actual error/behavior | After-repair RSS KiB | FDs | Managed allocated bytes |
| --- | --- | ---: | ---: | ---: |
| ops_full | CATALOG_FULL | 25,296 | 10 | 32,768 |
| events_full | CATALOG_FULL | 25,288 | 10 | 32,768 |
| grant_full | GRANT_FULL; revoke committed | 25,292 | 10 | 32,768 |
| sqlite_full | SQLITE_FULL | 25,324 | 10 | 53,248 |
| disk_full | SQLITE_FULL | 25,280 | 10 | 32,768 |
| read_only | SQLITE_READONLY_DIRECTORY | 25,300 | 10 | 32,768 |
| late_commit | STORAGE_FAILED | 25,300 | 10 | 32,768 |

Operation/event limits refuse new admission without deleting records. A revoke
that cannot record its event still stops access and retires the process. Grant
fullness preserves ordinary revoke/expiry. Formal tests also cover expiry with
full audit capacity and expiry-write failure. Internal expiry needs no new audit
slot but still needs SQLite write space.

SQLite page-budget FULL is an actual SQLite error, not a mocked storage response.
The disk-full scenario fills a 1-MiB tmpfs until free bytes are zero and attempts
real revoke; it is kernel filesystem ENOSPC, not a physical disk test. The live
write-denial scenario removes directory write permission and observes
SQLITE_READONLY_DIRECTORY during revoke. After stop, an actual readonly remount
separately rejects startup with EROFS at writer.lock opening. This proves startup
refusal on readonly storage, not an injection into the SQLite boot transaction.
Writable capacity/permissions are restored before restart.

In the late-commit scenario, the application times out and retires authority,
then the held real approval transaction is released and ACTIVE is read back from
the catalog. Data remains refused both before and after repair/restart. A durable
ACTIVE row is not runtime permission. Historical results remain readable and
explicitly historical; their replay never re-executes an approval. Tests compare
immutable history before/after restart.

DEGRADED has no online reset. Status reports first failure, recovery guidance and
capacity counts marked inexact while degraded or a mutation is in flight.
Catalog recovery increases explicit finite limits after stopping the service;
no GC, history deletion, blank-database reset or indefinite rollover is qualified.
See [operator recovery](RECOVERY.md).

## Controlled VM timing and resources

Twenty ordered 8,192-byte roundtrips verified 163,840 bytes in each direction in
2.017 ms after session admission (excludes TLS/setup/approval).
A separate live revoke RPC took 44.170 ms, including
fixture client launch, mTLS/control, persistence and local cleanup. The client's
positive EOF observation interval was 47.509 ms
from its own earlier wait start. These are different intervals, not repeat samples.
Sessions after revoke: zero. Point observation after the ordinary roundtrip trial:
25,056 KiB RSS, 10 FDs, 32,768 managed allocated bytes.

Per-scenario resource values above are sampled after repair and fresh forwarding,
not peaks or growth tests. Gateway RSS excludes clients/backend/VM overhead;
managed store size excludes config, PKI, venv, logs and VM image. The receipt's
`fault_phase_seconds` includes fault induction and verification (including delayed
commit readback/refusal after closure). It is not pure closure latency or recovery
time. No baseline speedup, native performance, SLO, total disk quota or hard RSS
bound follows from these observations.

## Recovery witness, controls and failures

One normal VM reboot retains ACTIVE/PENDING catalog bytes/hash/rows and operation
count unchanged after boot, before a new gateway is started. Boot UUID changes;
epoch advances to 3; old grants become INVALIDATED,
old data returns NO_ACCESS and a stale mutation returns STALE_EPOCH. Fresh approval
and forwarding work. This remains manual startup, not systemd autostart.

The offline verifier rejects **42 corrupted receipts**, including missing
recovery cases, false closure, failed epochs, false FULL/readonly evidence and
unobserved late commit. Normal and optimized Python checks agree. This validates
record structure/invariants, not cryptographic authenticity of fabricated evidence.
All owned processes/namespaces were cleaned, VM and disk deleted, preexisting
profiles unchanged. No stage failure/timeout was accepted.

[Milestone attempt 01](../evidence/milestone-attempt-01.json) failed because Linux
refused a live readonly remount with writable files open. [Attempt 02](../evidence/milestone-attempt-02.json)
failed a too-specific startup-error observer. [Attempt 03](../evidence/milestone-attempt-03.json)
passed on its frozen sources; it is superseded by precise fault-phase timer naming.
Their original JSON/HTML remain intact and do not qualify revised sources.
[Earlier reviewed exploration results](REVIEWED_EXPLORATION_RESULTS.md) retain
previous measurements and review context; no speedup/regression comparison is made.

Remaining gates: formal service packaging/systemd, fresh install/operator walkthrough,
bounded sustained resource observations, broader control pressure and credential
lifecycle as needed. Global DEGRADED on approval/revoke revision conflict remains
an availability limitation. No power loss, actual suspend, boot-zero-gap,
long-term endurance, automatic rollover or arbitrary journal-corruption recovery
is claimed. Repository remains Private; no project license selected.
