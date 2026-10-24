# Boot recovery and bounded-operation acceptance

This closes the existing single-node scope. The runtime wheel, installer and
shipped service command remain the formal implementation; qualification tools
are external VM fixtures. No online reset, catalog GC, HA or new access feature
is introduced. See the current source-bound results before interpreting a pass.

## Enabled boot startup

After installing and testing the configuration according to [deployment](DEPLOYMENT.md),
operators explicitly enable the shipped unit:

```sh
sudo systemctl enable grantweft.service
sudo systemctl is-enabled grantweft.service
```

Enabling does not prove that the configured listener address exists during boot.
The unit's After=network.target is not network-online/address provisioning.
Provision the actual network and any required storage ordering for the host;
startup failure consumes the finite systemd restart budget. READY means the
service completed journal recovery and listener initialization. Use authenticated
status and a fresh approved application request to verify usable access.

The dedicated VM adds a test-only dependency to construct its client/router/backend
namespaces and start the deterministic backend. That root fixture does not replace
ExecStart, generate authorization, edit epochs or repair the gateway catalog.
The shipped gateway process still runs as grantweft, without capabilities, with
its configured restrictions. There is no claim about arbitrary production network
managers or a boot protection window.

## Preserve evidence before automatic recovery

The fixture service runs before the enabled gateway on each boot. It mounts the
persistent test state filesystem and opens SQLite read-only. It records the new
boot ID, absence of service-UID processes, database SHA-256, old ACTIVE/PENDING
rows, operation/audit digest and catalog/lock inode identities. It then prepares
network namespaces. The witness does not repair or write gateway state.

The normal reboot begins with the formal service still running and pending/live
authority recorded. Startup must observe the same journal content; normal shutdown
must not have erased the evidence. After automatic service activation, the actual
catalog must retain history and invalidate all prior ACTIVE/PENDING rows with
revision+1, advancing epoch before admission. Every old grant is probed using its
owner's credentials. Fresh request/approval/forwarding must succeed. Each case then explicitly
revokes its own fresh verification grant and checks NO_ACCESS, so the next
workload begins without an unrelated active grant. This sequence
separates shutdown behavior from boot recovery.

The VM migrates the stopped preceding service catalog to a dedicated 32-MiB ext4
image, preserving file bytes, row counts and history, before these trials. Inode
comparisons begin after this documented migration. Device numbers may change at
boot, so cross-boot comparison uses inode/content; within a single boot, recovery
also requires unchanged filesystem device/inode pairs. The underlying original
catalog is not deleted. The image remains inside the disposable VM.

## Storage fault across boot

Live removal of directory write permission causes the installed service's actual
revoke write to fail with SQLITE_READONLY. Effective access must retire and new
requests return DEGRADED. Restoring that permission alone must not reset authority.
The subsequent normal reboot mounts the persistent ext4 state filesystem readonly.

The loop backing device remains writable (observed with blockdev); only the
filesystem mount is readonly, so an unintended device fault does not obstruct
the explicit remount repair. The enabled formal unit must fail startup, reach its restart limit and remain
without a MainPID/service-UID process. An authenticated control attempt must fail
with a refused connection, not merely time out. The pre-service witness and a
snapshot after failed starts must preserve the old journal unchanged. Stale
ready.json is explicitly not considered health.

Repair is an operator action: remount writable, restore directory permissions,
retain catalog/history/lock, inspect failures, reset the systemd failure budget
and start the formal unit. Old grants remain unusable; a fresh approval works.
This qualifies one actual readonly filesystem across reboot, not every storage
failure mode, media corruption or physical power loss.

## Fixed bounded-operation workload

Run forty mixed cycles on one initialized formal systemd instance: a fresh
request, approval and twenty ordered 8-KiB roundtrips per cycle, then alternate
explicit revocation and natural two-second expiry. A held tunnel verifies positive
EOF/reset, and the retired grant must refuse new admission. Each cycle must persist
its expected terminal state and return to zero sessions. Authenticated status
pagination must cover every retained grant.

Cycles follow a fixed fifteen-second interval: a minimum 600-second observation,
maximum 720 seconds overall, and each cycle's work must finish within its slot.
No process or service restart, epoch change, reset, database deletion or history
pruning is permitted. PID, /proc start ticks, invocation ID, restart count and full
runtime privilege identity are checked throughout. Test clients/backend/observer
processes are outside gateway RSS/FD scope.

Fixed finite config: max_grants=96, max_ops=max_events=512; default capacities for
sessions/queues/buffers remain unchanged. The workload is budgeted below these
limits. A separate earlier fault matrix covers intentional exhaustion; this run
must not consume its last slot or hide expected rejection as completed work.

Thresholds are fixed in code before the run: initial, cycle and final RSS must
all be <=64 MiB. After five warmup cycles, all 35 idle FD samples and the final
sample must match; post-warmup RSS range <=8 MiB and last-ten minus first-ten
sample mean <=4 MiB. RSS can retain allocator
pages; these gates detect this bounded workload's growth, not prove absence of
leaks. Every failed cycle remains in the receipt. Catalog rows and disk allocation
are expected to grow with retained history; there is no GC/rollover claim.

## Boundaries

Normal VM shutdown/reboot is not sudden power loss. Neither power-loss recovery
nor boot-zero-gap protection is tested. Ten minutes is not an endurance result,
physical/native performance measurement, outage SLO or production-readiness
qualification. Credential lifecycle, hostile local root/same-UID processes,
uninterruptible kernel I/O and indefinite catalog operation remain outside scope.

## Retained failed attempt

The first closeout run passed enabled normal-boot recovery and real readonly
startup/rate limiting, then failed repair: `mount -o loop,ro` had also opened the
loop backing device readonly, making a filesystem-only remount insufficient.
Its receipt remains failed. The revised fixture explicitly opens a writable
loop device and mounts only the filesystem readonly, records blockdev's readonly
flag, and keeps the same service failure/recovery checks and observation budgets.
This is a fixture repair, not evidence that the earlier repair succeeded.

The second attempt completed both reboot cases and readonly repair, then failed
the first sustained cycle because the previous case's freshly approved verification
grant was still valid. The strict all-denied observer correctly rejected that
mixed setup. Each boot case now explicitly revokes and probes its fresh grant;
the sustained phase also requires a complete denied initial status. No observer
condition, capacity or resource threshold was relaxed. This was a fixture
workload-isolation defect, not revival of an old epoch's authority.

The RSS trend gate uses the post-warmup cycle checkpoints followed by the final
post-schedule sample. Its end-ten mean therefore includes the final sample and
the last nine cycle checkpoints; the first ten are cycles 6–15.

## Reviewed evidence relationships

The reviewed contract requires the readonly DEGRADED state before reboot and
after permission repair to cover every persisted grant with DENIED/zero sessions,
plus actual owner-authenticated NO_ACCESS and unchanged process identity. Each
cycle's unique new grant ID and terminal revision/epoch are tied to its committed
nonhistorical revoke result. Initial RSS explicitly shares the existing absolute
limit; no workload or numerical threshold is relaxed. See [review](CLOSEOUT_REVIEW.md).
