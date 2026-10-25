# Reviewed boot recovery and bounded-operation outcomes

The project has since adopted [MIT](../LICENSE). This receipt retains its original
pre-license source fingerprint and measurements; [license review](LICENSE_REVIEW.md)
records the metadata-only delta and unchanged runtime payload. No new VM
performance/recovery claim is made by license adoption.

Source fingerprint: `a05bc2a1f07b564345fb685a0713e6db4e81e14863bff2e3ebdca944a97b82ec`.
[JSON](../evidence/latest.json) / [HTML](../evidence/latest.html) encode the same
`grantweft-closeout-review-v8` receipt. The current main-agent run uses a fresh no-mount
Linux VM and the installed runtime wheel. Runtime gateway, installer and shipped
unit are unchanged from the prior reviewed deployment. Two read-only agents
independently reviewed source and raw historical evidence,
then checked fixes and this new run offline. Neither independently reran the VM.
These are controlled VM observations, not a production guarantee. See
[review findings](CLOSEOUT_REVIEW.md).

## Formal implementation and deployment

macOS and installed Linux each pass **51 identical unique test IDs**:
**38 formal implementation/CLI/readiness tests plus thirteen observer/cleanup controls**,
zero failures/errors/skips. Native suite: 31.07 s; Linux:
37.18 s. Suite duration is not comparative performance.
Linux runtime: Python 3.12.3, SQLite 3.45.1, OpenSSL 3.0.13 30 Jan 2024.
Installed .py/.service hashes match frozen sources and wheel; the runtime source
checkout is removed from import reach before Linux testing. No remote CI claim.

The retained installed-systemd stage still verifies actual non-root UID 996,
all four UID columns, original argv, no capabilities and NoNewPrivileges=1;
normal stop, SIGKILL takeover, DEGRADED repair, ptrace stop timeout and real
restart limiting pass. Seven separate capacity/storage/late-commit recovery
scenarios pass. Atomic ready.json publication still has the actual paused-write
regression; neither atomic rename nor a stale receipt is a live health or
physical-power-loss guarantee.

## Enabled boot recovery and readonly repair

| Case | Qualified observation |
| --- | --- |
| Enabled normal reboot | Shipped service starts automatically after the VM fixture prepares its network; changed boot ID; old journal unchanged before service; epoch 8→9; all ten old grants individually refuse access |
| Live write failure | Actual revoke raises SQLITE_READONLY after directory write permission is removed; DEGRADED refuses new requests; restoring permission alone does not reset authority |
| Readonly state across reboot | Persistent ext4 state mounts readonly, writable backing device observed; three actual EROFS failures opening writer.lock, explicit start-limit journal message, stable NRestarts=3/MainPID=0 and refused control connection |
| Explicit repair | Remount writable, retain catalog/lock, reset/start formal unit; epoch 9→10; all thirteen old grants remain unusable; fresh approval/verified forwarding works |

Before each automatic startup, a root fixture opens the journal read-only and
records absent service-UID processes, changed boot identity, old ACTIVE/PENDING
rows, full database hash, history/counts and inode identities. Those match the
pre-shutdown snapshot: shutdown cleanup cannot explain boot recovery. After
startup, every old ACTIVE/PENDING row becomes INVALIDATED with revision+1;
history and catalog rows remain. Old-epoch operations refuse. Both the readonly
pre-reboot and permission-repaired DEGRADED snapshots cover all thirteen persisted
grants with zero sessions and denied authority. After permission repair, actual
owner-authenticated probes return NO_ACCESS for every grant without process
replacement. Each case explicitly revokes its own fresh verification grant before
the next workload.

The real service is enabled and its ExecStart/security properties remain intact.
Only VM fixture setup/backend dependencies and NetworkNamespacePath are added.
Root network/backend provisioning is outside the unprivileged runtime boundary.
The dedicated 32-MiB ext4 image contains the migrated preceding service catalog;
no catalog/history reset is used. The readonly boot refusal occurs at lock opening,
not at a claimed SQLite boot transaction. Arbitrary production network provisioning
and corrupt-media recovery are not qualified. See [procedure](CLOSEOUT.md).

## Same-process bounded observation

**40 cycles / 600.001 seconds**, alternating twenty explicit revocations
and twenty natural expiries. Every cycle performs a fresh request/approval,
twenty verified ordered 8-KiB roundtrips, held-tunnel positive EOF/reset, old-grant
NO_ACCESS and committed terminal-state checks. That is 800 timed payload
roundtrips, 6.25 MiB each direction, plus separate held-tunnel marker traffic.
All forty cycle grant IDs are new/unique; terminal ID/epoch/revision match the
nonhistorical revoke result where applicable. All cycles pass; complete status
pagination covers retained grants; every idle checkpoint has zero sessions and
denied access.

PID 1101, process start ticks, invocation ID, restart
count and epoch stay unchanged throughout. No restart, reset, pruning or database
replacement cleans resources during the observation. Main-process VM samples:

| Measurement | Observed |
| --- | ---: |
| Initial RSS | 25,336 KiB |
| All-cycle idle RSS samples | 25,820–28,188 KiB |
| After-five-cycle-warmup RSS range | 26,412–28,188 KiB |
| Final RSS | 27,932 KiB |
| Warmed first-ten / final-ten checkpoint means | 26,975.2 / 27,881.6 KiB |
| Idle FDs, all cycles and final | 10 |
| Managed allocated file blocks, initial→final | 53,248→122,880 bytes |
| Catalog grants | 14→54 of configured 96 |
| Operation / audit rows, each | 28→128 of configured 512 |

The final-ten checkpoint mean includes the final post-schedule sample plus the
last nine cycle samples; the initial mean uses cycles 6–15.

The POLICY matches the historical v7 run exactly. Initial, cycle and final RSS
now explicitly share the existing <=64 MiB gate. Other gates remain a post-warmup
range <=8 MiB, last-ten minus first-ten mean <=4 MiB and exactly unchanged warmed
idle FD count. All pass.
**RSS rose during the run**; this is not a no-leak or plateau claim. The cause of
that rise is not isolated by a memory profile. Catalog/disk growth is expected
from retained history. Configured finite limits exceed the default 64 grants and
256 operations/events; this run does not prove indefinite operation or rollover.
Internal expiry updates do not allocate a new operation/audit row.

These are idle main-process samples, not peak RSS or total VM/client/backend
memory. Managed files exclude the ext4 image's reserved space, runtime, PKI,
config and logs. They do not establish physical-media durability or a total disk
quota. The earlier systemd point trial measures twenty 8-KiB roundtrips in
1.962 ms **after admission**, with
25,316 KiB sampled RSS / 12 FDs including an additional
held idle tunnel. It is a different workload from the sustained idle checkpoints,
not a comparative speedup. SIGKILL-to-new-active/status observation is
1.148 s, a single VM observation,
not an outage bound.

## Controls, failures and limits

The offline verifier rejects **133 corrupted receipts** under ordinary
and optimized Python. Two further observer tests challenge incomplete DEGRADED
authority and unrelated
cycle grant/revoke evidence; the identity test also rejects oversized initial
RSS. These thirteen observer tests are separate from the 38 formal product tests.
Structural verification does not authenticate fabricated telemetry. All stages exit successfully without timeout. Service,
clients/backend, namespaces, loop mount/device and test drop-in are cleaned;
the dedicated VM/data disk are deleted and preexisting profile states unchanged.

[Attempt 01](../evidence/closeout-attempt-01.json) failed repair because the loop
backing device was unintentionally readonly. [Attempt 02](../evidence/closeout-attempt-02.json)
completed boot/repair but failed the strict sustained setup check because the
preceding case left its fresh verification grant valid. Both remain failed.
Fixture fixes preserve the workload, timeouts and resource thresholds.
[Initial closeout](CLOSEOUT_INITIAL_RESULTS.md),
[previous reviewed deployment](SYSTEMD_REVIEWED_RESULTS.md) and historical/failed
receipts retain their original source-specific interpretation.

Normal VM reboots are qualified. **Sudden power loss and boot-zero-gap are not
tested.** Actual suspend, long-term resources/rollover, credential lifecycle,
uninterruptible kernel I/O, hostile local root/same-UID processes and arbitrary
production networks remain outside scope. Global DEGRADED may disrupt unrelated
grants; capacity repair still requires bounded limits and a restart/new approval.
Repository remains Private. License was unset at this recorded qualification;
the project now uses MIT, as documented in [license review](LICENSE_REVIEW.md).
