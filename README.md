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

## Milestone 1: explicit safe recovery

DEGRADED permanently retires current process authority. Authenticated status
reports the first failure/action/SQLite code, effective access and finite capacity.
Storage repair alone cannot resume access. Operators repair storage or raise
explicit finite limits, then restart using the same catalog and stable lock.
Startup invalidates old grants and advances epoch before opening listeners.
Historical operation replies remain historical and never re-execute approvals.
See [recovery procedure and limits](docs/RECOVERY.md).

The current source-bound run passed the same **41 tests on macOS and installed
Linux**: 35 formal service tests plus six observer/cleanup controls. Seven Linux
VM scenarios cover operation/event/grant fullness, actual SQLite FULL, full tmpfs,
live directory write denial plus readonly-filesystem startup refusal, and a late
approval commit after timeout. Full capacity still allows effective stopping;
repaired restart refuses old grants/operations and requires fresh approval.

Late approval was actually read back as ACTIVE on disk after timeout, while data
remained denied. One normal VM reboot also preserved ACTIVE/PENDING journal state
before recovery, excluding shutdown cleanup as an explanation. Installed module
hashes match the frozen sources, with product source removed from import reach.
The gateway runs unprivileged; backend bypass is checked in isolated namespaces.
**42 report corruption controls** were rejected.

One controlled VM trial verified twenty ordered 8-KiB roundtrips in
**2.02 ms after admission**; a separate revoke RPC took **44.17 ms**
including fixture client launch and TLS/control exchange. The client observed
positive EOF and zero sessions remained. Sampled gateway RSS: **25,056 KiB**,
FDs: **10**, managed allocated store: **32,768 bytes**.
These are single virtualized point observations, not peaks, speedup or SLOs.
See [current results](docs/EXPLORATION_RESULTS.md) and [JSON/HTML evidence](evidence/README.md),
including failed and superseded attempts.

Catalogs remain finite with no automatic GC/rollover; raising limits is bounded
headroom, not indefinite operation. Formal systemd deployment, sustained resource
behavior, power loss and boot-zero-gap remain unqualified. Live write-denial and
readonly-startup tests do not imply physical-media durability.

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
