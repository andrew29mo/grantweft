# Grantweft

A bounded temporary-access gateway: authenticated request, separate approval,
framed TLS-to-TCP access, and expiry/revocation of existing sessions.

This repository contains a **formal minimal implementation and four technical
explorations**, not a qualified operational release. GitHub stays Private. No
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

## Recorded results

The final source-bound run passed the same **25 tests on native macOS and an
isolated Linux VM**, with zero failures/errors/skips. The installed wheel's five
runtime module hashes match the frozen checkout; product source was removed
from import reach before the Linux tests.

Three isolated network namespaces verified actual TLS/TCP forwarding through a
UID-65534 gateway while direct client access to the backend failed. One normal VM
reboot preserved the ACTIVE/PENDING catalog before gateway recovery, then
invalidated old grants and refused stale operations. Fresh approval worked.
**19 report corruption controls** were rejected.

A single Linux VM trial verified twenty ordered 8-KiB roundtrips in **2.57 ms after
session admission**. A separate live-session revoke RPC took **32.61 ms**, including
the fixture client-process startup and TLS/control exchange; local cleanup was
complete and client termination was observed. Sampled gateway RSS was **25,056 KiB**,
fd count **10**, and allocated managed-store bytes **32,768**. These are controlled
point observations, not peak usage, deployment size, a speedup or a latency bound.
See [results and limitations](docs/EXPLORATION_RESULTS.md) and
[complete JSON/HTML](evidence/README.md), including retained failures.

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
