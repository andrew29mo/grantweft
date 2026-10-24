# Grantweft

A bounded temporary-access gateway: authenticated request, separate approval,
framed TLS-to-TCP access, and expiry/revocation of existing sessions.

This repository contains a **bounded single-node MVP with installed-service and
local VM qualification**. GitHub stays Private. No project license has been
selected or granted. Python/OpenSSL/SQLite and external VM/build tools retain
their respective terms; no upstream binaries, test keys, VM images or source
databases are committed.

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

## Installed service and bounded recovery

The runtime wheel now ships a root installer and a systemd unit. The gateway runs
as a dedicated non-root account with no capabilities and a restricted writable
state directory. Type=notify separates completed initialization from process
startup; authenticated status reports current READY/DEGRADED health. See
[deployment and repair commands](docs/DEPLOYMENT.md).

The source-bound closeout run passes **49 identical tests on macOS and installed
Linux** (38 formal implementation/CLI/readiness tests plus eleven observer controls),
seven storage/recovery scenarios and the actual installed systemd lifecycle.

The enabled service now has two normal-VM-reboot cases: automatic boot recovery
and readonly storage across boot with explicit repair. A read-only witness captures
the unchanged old ACTIVE/PENDING journal **before** the formal service starts,
excluding shutdown cleanup as the explanation. Old grants and epochs remain
unusable; fresh approval/forwarding works. VM network setup is an explicit test
fixture, not a claim about arbitrary production host networking.

A **40-cycle, approximately ten-minute** mixed revoke/expiry run uses one service
process throughout. Every cycle verifies ordered bytes, positive connection
closure, denied retired access and zero idle sessions. Idle FDs remain **10**;
after five warmup cycles, RSS samples range **26,552–28,468 KiB**.
RSS rises during this bounded observation; passing fixed gates does not prove
absence of leaks or long-term stability. History is retained: grants grow 14→54
of a configured 96; operations/events each 28→128 of 512. No GC or rollover.

**122 report corruption controls** are rejected. Failed attempts and the
previous deployment qualification are retained. All owned service/fixture
resources and the dedicated VM/disk are cleaned. See [current results](docs/EXPLORATION_RESULTS.md),
[boot and sustained acceptance](docs/CLOSEOUT.md) and [JSON/HTML](evidence/README.md).

These are controlled Linux VM observations. Sudden power loss, boot-zero-gap,
actual suspend and long-term operation remain untested; no production guarantee,
peak-memory limit, speedup or outage SLO follows.

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
`grantweft` modules, the shipped service unit and distribution metadata.

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
sudden power loss, boot-zero-gap and hostile local root/same-UID
processes are unqualified. The client must not have another path to the backend.
