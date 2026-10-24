# Grantweft

A bounded temporary-access gateway: authenticated request, separate approval,
framed TLS-to-TCP access, and expiry/revocation of existing sessions.

This repository contains a **formal minimal implementation and four technical
explorations plus milestone 1 repair/restart**, not a qualified operational release. GitHub stays Private. No
project license has been selected or granted. Python/OpenSSL/SQLite and external
VM/build tools retain their respective terms; no upstream binaries, test keys,
VM images or source databases are committed.

## Delivered exploration scope

- Individual client certificates mapped to fixed principals and requester/approver
  roles; fixed backend service ID and numeric address. No arbitrary destination.
- SQLite requests, approval decisions, operation deduplication and audit rows;
  a single DB thread never owns sockets or activates access.
- Deadline frozen before approval commit; every completion is checked against
  current epoch, terminal fence, deadline and service generation.
- One TLS tunnel per backend TCP session, ordered DATA/EOF/CLOSE frames, bounded
  input and output, application half-close, expiry/revocation with transport abort.
- An owner-controlled stdio connector: no shared unauthenticated loopback port.
- Fixed-inode single-writer lock. Startup invalidates all prior PENDING/ACTIVE
  grants before opening listeners. Existing sessions and grants do not survive
  process/VM restart; operators must request and approve again.
- Bounded admissions/catalog; DEGRADED stops transfer after persistence errors.
  Catalogue counts include terminal records; automatic GC is not implemented.

A pending approval/revocation revision conflict conservatively retires the whole
service. This is a verified safety-first limitation, not transparent race recovery.
Storage hooks are explicit `--barriers` test fixtures; never set them in deployment.
A stop cannot retract bytes already passed to kernel buffers or undo backend work.

## Reviewed milestone 1: explicit safe recovery

DEGRADED retires current process authority. Authenticated status reports first
failure/action/SQLite code, effective access and finite capacity. Storage repair
alone cannot resume access. Operators repair storage or raise finite limits and
restart with the same catalog/lock; startup invalidates old grants and advances
epoch before listening. Historical operations never re-execute approvals.
See [recovery procedure](docs/RECOVERY.md) and [review repairs](docs/MILESTONE_1_REVIEW.md).

The reviewed source-bound run passes **42 tests on macOS and installed Linux**:
36 formal service/CLI tests plus six observer/cleanup controls. Seven Linux VM
scenarios cover operation/event/grant fullness, real SQLite FULL, full tmpfs,
live directory write denial plus readonly startup refusal, and approval committed
late after timeout. Full capacity still stops access. Repair/restart preserves
catalog/lock identities, operation/audit history and counts, invalidates old grants,
refuses stale operations and requires fresh approval. Even replaying the original
timed-out approval UUID reads history without reopening access.

One normal VM reboot retains ACTIVE/PENDING journal state before new startup,
excluding shutdown cleanup as its explanation. The installed unprivileged gateway
matches frozen sources, with product source removed from import reach. Direct
backend bypass is checked in isolated namespaces. **60 report corruption controls**
are rejected; raw failed and superseded attempts are retained.

A single VM trial verifies twenty ordered 8-KiB roundtrips in **2.45 ms after admission**;
a separate revoke RPC takes **40.57 ms** including fixture client startup and
TLS/control exchange. Positive EOF and zero remaining sessions are observed.
Sampled RSS **25,052 KiB**, FDs **10**, managed store **32,768 bytes**.
These are virtualized point observations, not peaks, speedups or SLOs.
See [results and limits](docs/EXPLORATION_RESULTS.md) and [JSON/HTML evidence](evidence/README.md).

Catalogs remain finite without automatic GC/rollover; increasing limits provides
bounded headroom. Global DEGRADED can disrupt unrelated grants. Formal systemd
deployment, sustained operation, power loss and boot-zero-gap remain unqualified.
Filesystem fault tests do not establish physical-media durability.

## Run portable formal-service tests

Python >=3.12 and OpenSSL CLI are required. Use a local venv:

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install 'setuptools>=77' wheel
mkdir -p results
.venv/bin/python -m tools.unit --output results/native.json
```

Tests launch the actual gateway subprocess and use real mTLS/TCP clients and
SQLite. Temporary CA/private keys, logs and databases remain local. A source
checkout is required for qualification tools; runtime wheels contain only
`grantweft` modules and distribution metadata.

## Documents and evidence

- [Repair/restart procedure](docs/RECOVERY.md)
- [Historical independent review and repairs](docs/REVIEW.md)
- [Architecture and transaction order](docs/ARCHITECTURE.md)
- [Wire frames and half-close](docs/PROTOCOL.md)
- [Resource budget](docs/RESOURCES.md)
- [Linux VM topology and reproduction](docs/VALIDATION.md)
- [MVP acceptance and remaining gaps](docs/ACCEPTANCE.md)
- [Exploration receipts](evidence/README.md)

Linux timings/RSS are virtualized observations and are labelled separately from
native macOS test duration. A short trial is not a long-term resource bound,
comparative speedup, outage SLO or production-readiness claim. Actual suspend,
sudden power loss, automatic systemd startup and hostile local root/same-UID
processes are unqualified. The client must not have another path to the backend.
