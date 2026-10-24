# Isolated Linux validation and reproduction

Use the source checkout and its declared Python >=3.12 environment. Install
setuptools>=77 and wheel in that environment, then build:

```sh
.venv/bin/python -c 'import setuptools.build_meta as b; b.build_wheel("results/dist")'
.venv/bin/python -m tools.validate \
  --colima-home /ABSOLUTE/DEDICATED_COLIMA_HOME \
  --toolchain /ABSOLUTE/COLIMA_TOOLCHAIN_BIN \
  --profile gw-exp-FRESH_NAME \
  --wheel results/dist/grantweft-0.1.0-py3-none-any.whl \
  --output results/FRESH_OUTPUT
```

A fresh gw-exp-* VM and absent data disk are required. The runner refuses reuse,
uses 2 vCPU / 2 GiB / requested 15-GiB data disk, no host mounts and no default
context activation, installs Python/OpenSSL/iproute2/util-linux from the guest
package manager, installs the no-dependency wheel, removes product source from
import reach and verifies installed module SHA-256. Tools/tests remain a checkout.
Both platforms run the same source-bound test IDs (38 formal-service tests plus eleven evidence/cleanup
controls in the closeout contract). OS/SQLite/OpenSSL versions
are captured; no firmware, hardware network or physical-storage claim follows.

Root creates only test network namespaces inside this VM:

```text
client gw-client (10.70.0.2)
       | veth / 10.70.0.0/24
router gw-router (10.70.0.1, 10.71.0.1)
       | veth / 10.71.0.0/24
backend gw-backend (10.71.0.2:9000)
```

A client route to the backend is deliberately present, but gateway namespace
IPv4 forwarding is disabled. Direct backend access must fail, while the actual
mTLS application proxy performs a verified roundtrip. Gateway runs as UID 65534
via runuser, with a 0700 owned store and no route/firewall privileges. Root fixture
and client subprocesses do not establish an untrusted-root threat model.

The installed formal gateway is tested separately from the backend fixture. A
controlled VM trial records 20 ordered 8-KiB roundtrips, live-session revocation,
client-observed positive EOF/reset termination (not timeout), sampled gateway RSS, fd count and managed allocated
bytes. Those are Linux VM observations; native test elapsed time is not a native
performance/RSS comparison. No baseline speedup or SLO is claimed.

For normal VM reboot, create ACTIVE and PENDING grants, SIGKILL the gateway and
save full catalog rows/hash before scheduling reboot. After boot-ID change, compare
the old journal before starting any new gateway; reconstruct only fixture topology,
then start the installed gateway. Old grants/data and stale epoch operations must
be refused; fresh request/approval must work. Fixture namespaces/processes are
explicitly cleaned, not part of service persistence. This retained legacy stage starts the service manually. The later closeout stage
separately qualifies the enabled formal systemd service. No abrupt-power-loss test.

Children are registered before readiness waits; cleanup attempts every owned
process/namespace and always attempts failure-receipt preservation. Cleanup errors
prevent case success. Partial guest receipts are fetched before deleting the VM.

Every subprocess stage has exit/timeout recording; stage failure or source changes
prevent a passing receipt. The runner retains JSON/HTML on failure and deletes
its owned VM/data disk in finally. A timeout kills the host stage process group;
VM deletion is the final containment boundary for possible remote leftovers.
Existing Colima profiles/statuses must remain unchanged. Raw commands, paths,
certificates, keys, databases, wheels and logs stay under ignored results or inside
the deleted VM. Only sanitized receipts are eligible for Git.

The closeout-v7 offline verifier requires complete ordered stages, actual platform
labels, postboot fresh-workload results, observed closure reason, recovered grant
states, raw stale-refusal outcomes and successful boot observations. Old receipts
without this contract are historical and are not accepted as current qualification.

## Milestone 1 recovery scenarios

The recovery-v3 runner adds `tools.vm_recovery` after the ordinary namespace
trial, before the normal-reboot witness. Every scenario uses the installed wheel,
actual mTLS/data-plane clients and the same unprivileged gateway, with a fresh
state root. Repair/restart within a scenario always reuses that state root.

Seven scenarios cover operation/event/grant catalog limits, SQLite max_page_count,
zero-free-space tmpfs, removal of directory write permission plus a separate
readonly-filesystem startup, and an approval deliberately committed after its
application timeout. The SQLite error code is captured from the real exception.
The disk-full and directory-write-denied trials attempt actual revocation, not
only an unrelated insertion. Fault hooks are used only for deterministic delayed
approval, not for manufacturing FULL/READONLY errors.

Every scenario observes a live tunnel's positive EOF/reset, old admission refusal,
new epoch and stale-operation refusal after repair/restart, then fresh approval
and twenty verified roundtrips. RSS/FD/store samples are VM point observations;
fault-phase intervals include fixture induction and verification work (including
late-commit readback/refusal after closure). They are not closure or recovery bounds.
No reboot/systemd qualification follows merely from a process restart. The
separate normal VM reboot witness remains manual gateway startup after boot.

The first milestone attempt failed when Linux refused a live readonly remount
because writable files were open. Its partial receipt is retained. The revised
scenario distinguishes live write-permission denial from actual readonly-mount
startup, rather than claiming the unsupported remount succeeded.

A second attempt reached real SQLITE_READONLY_DIRECTORY during live revoke,
but its startup observer required the unhyphenated word "readonly" and rejected
a different startup refusal. That attempt also remains failed. The corrected
observer preserves the actual final exception line and accepts only explicit
read-only-filesystem or readonly-database startup failures, never a timeout or
generic nonzero exit.

## Milestone review contract

The reviewed run adds a formal duplicate-identity CLI exit regression and retains
the same seven recovery workloads. Each case snapshots the stopped catalog and
the postboot catalog before new writes: counts, history digest, grant transitions
and catalog/lock file IDs. The late-commit case replays the exact operation UUID
then proves data access remains refused. Expected refusal exit codes, committed
grant-full revoke, cleanup errors and capacity increments are mandatory checks.
The old receipts remain historical, not rewritten to satisfy new acceptance.

## Installed systemd stage

The wheel includes grantweft.deploy and the shipped service unit. Provenance now
hashes every runtime .py and .service file in both the frozen source and installed
package. `tools.vm_service` installs the unit, provisions root-owned test config/PKI,
and applies only a VM NetworkNamespacePath drop-in; actual process argv must be
the shipped command. The unit uses a dedicated service UID (not fixture nobody).

Observed UID/capabilities/no-new-privileges, READY notification, normal stop, SIGKILL
takeover, DEGRADED catalog repair, root-ptrace stop timeout, invalid-config restart
limiting and repaired startup have per-case receipts. A ptrace stop is root fixture
injection; no product barrier flag or alternative startup wrapper is used.

Service attempt 01 failed because SIGSTOP did not exercise stop timeout; systemd
resumed the process to handle termination. Attempt 02 exercised timeout/KILL and
recovery, then failed when the fixture tried to reset a normally stopped unit
already unloaded by systemd. The corrected script resets failed units only. Those
failed receipts remain failed and are not current qualification.

This lifecycle stage stops the unit and removes its namespace drop-in before
cleanup. It does not enable the unit. The additional closeout stage below enables
the shipped unit and has its own automatic-recovery witness. Neither stage
qualifies power loss or boot-zero-gap. See [deployment](DEPLOYMENT.md) for commands and limits.

Service attempt 03 observed limiting but failed a too-specific Result expectation.
A dedicated non-qualification diagnostic then captured journal rate limiting with
Result=exit-code and NRestarts=3. Acceptance now requires three actual error traces,
the explicit rate-limit journal message and a stable stopped restart count; it
does not accept a generic exit-code by itself. Attempt 04 instead exposed a torn
ready.json read in the formal Linux suite. Atomic receipt publication fixes that
race; a mid-write publication regression challenges the real startup path.

Service attempt 05 failed the first version of the new publication regression:
the test wrapper referenced argv after rewriting it, so it waited for the wrong
marker. The wrapper now captures its marker/release paths before invoking the
real CLI; its isolated regression passes. That failed full run remains failed.
The diagnostic-only run skipped suites and is never promoted to qualification;
its sanitized observations are retained separately.

Service attempt 06 passed both platforms, all recovery and service cases, but
failed the extra normal-VM-reboot witness: repeated successful polls still returned
the old boot UUID for 120 seconds. It is not a passing run. The timer now specifies
AccuracySec=1s, retaining the same boot-observation deadline and additional timer/
journal/job diagnostics on failure. VM creation/DNS delays remain infrastructure
stage timings, separate from service-performance measurements.

The deployment review retains the unchanged runtime wheel/unit and adds stronger
actual-service observations: per-instance identity bound to MainPID, complete
zero-session DENIED status, owner-authenticated refusal for every old grant,
explicit DEGRADED admission refusal and full repaired catalog transitions. Two
new observer tests are evidence controls, not additional product features. The
prior systemd-v5 evidence is retained as historical; it does not qualify v6 sources.

## Final boot and bounded-operation stages

`tools.vm_closeout` follows the retained manual-start reboot. It migrates the
stopped service catalog without deleting it, provisions a dedicated persistent
ext4 state image, and enables the shipped unit. Only VM fixture dependencies
and NetworkNamespacePath are added. The runtime ExecStart is unchanged.

On each of two normal VM reboots, a root fixture opens the catalog read-only
before the gateway service starts and records unchanged old ACTIVE/PENDING
authority, digest/history/inodes and changed boot identity. One boot is writable;
the other deliberately mounts the state filesystem readonly after a live
SQLITE_READONLY retirement. Failed startups must leave the journal unchanged,
exhaust the configured three-start budget and refuse control connections.
Explicit remount/permission repair plus reset/start must invalidate old authority
and allow only fresh approvals. Unit enablement, PID/argv/UID/capabilities and
old owner-authenticated data refusals are checked, not inferred from a ready file.

The final forty-cycle workload lasts at least 600 seconds on one systemd
instance. It alternates revoke/natural expiry with verified payloads and positive
closure. It records every cycle, complete paginated catalog status, fixed
capacity counts, process identity and idle RSS/FD/managed-file allocation.
Thresholds and workload are fixed before execution; observer controls challenge
restarts, growth and incomplete evidence. See [exact acceptance](CLOSEOUT.md).

Every new stage has an outer timeout. Partial receipts/progress and boot journal
diagnostics are fetched on failure; failed attempts remain failed. Successful
cleanup stops/disables service and backend, removes namespaces/drop-in and
unmounts fixture storage before VM/data deletion. VM resource samples remain
separate from native macOS test duration. No power-loss/boot-zero-gap or long-term
rollover claim follows.

Closeout attempt 01 passed normal automatic startup and readonly failure/rate
limiting but failed repair because an automatic readonly loop mapping prevented
remount-rw. The corrected fixture explicitly creates a writable loop mapping and
records its blockdev flag while keeping the filesystem readonly. The failed run
is retained; no acceptance threshold or timeout is loosened.

Closeout attempt 02 completed both boot cases and readonly repair but failed the
first sustained cycle: a fresh verification grant from the preceding case remained
active. The strict observer rejected it. Cases now explicitly revoke/probe their
fresh grants, and sustained startup checks complete denied state. The failed
receipt remains failed; no threshold is weakened and no restart clears the
sustained workload.
