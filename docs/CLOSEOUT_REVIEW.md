# Review of boot recovery and bounded operation

License-status statements below describe the recorded pre-MIT revision. The
project now uses [MIT](../LICENSE); see [adoption review](LICENSE_REVIEW.md).

Reviewed parent: `5f501e14f8ec184e68897522fffd5155307cb22f`.
Two read-only reviewers first inspected the diff, formal runtime, raw VM evidence
and report contract independently. Neither reviewer reran the VM. The main agent
reproduced the modified-copy counterexamples, repaired assertions and performs the
new source-bound qualification. Agreement is not proof of runtime behavior.

## Findings

The original run's raw/private receipts, published JSON and HTML agree. Its old
journal witnesses, actual service identities, zero-session denied states and
forty-cycle resource values are internally consistent. No actual old-authority
revival, hidden restart or threshold increase was found. Two P2 evidence-contract
holes were nevertheless reproduced:

1. The readonly case's prepared DEGRADED object checked health/error but could
   contain a live session or ALLOWED grant and still pass offline verification.
   Complete denial was asserted by the actual fixture, but not by this contract.
2. A cycle's revoke result could name an unrelated grant; cycle grant IDs could
   also repeat. The actual fixture used the current new grant, but the contract
   did not prove that relationship.

A smaller scope ambiguity allowed initial RSS above the configured absolute limit:
cycles and final samples were bounded, while initial identity only required a
positive value. The original initial RSS was well below the limit. The wording
has been clarified rather than declaring that an over-limit run was observed.
[Modified-copy observations](../evidence/closeout-review-observations.json) are
counterexamples, not VM incidents.

## Repairs and validation contract

- Readonly pre-reboot DEGRADED state now requires complete zero-session DENIED
  status bound to the exact persisted grant IDs/state/revision/epoch. The fixture
  records another complete snapshot after directory permissions are restored,
  performs owner-authenticated NO_ACCESS probes for every old grant and requires
  the same MainPID/invocation/restart count. Merely repairing permission cannot
  silently reactivate authority.
- Every cycle records terminal ID/state/revision/epoch/persistence. The ID must be
  a fresh canonical UUID, absent from the initial catalog and all preceding cycles.
  Revoke must be a nonhistorical committed result for that same grant/epoch and
  match its terminal revision. Request→approval→retirement is revision 1→2→3 in
  this fixed workload. The actual VM loop also checks these relationships.
- Initial, cycle and final RSS all use the existing 64-MiB absolute limit. The
  8-MiB post-warmup range, 4-MiB end/start mean-growth gate, identical warmed idle
  FDs, forty-cycle schedule and 600–720-second bounds are unchanged. The full
  POLICY object is compared to the archived run before qualification.
- Two new observer tests challenge live/missing DEGRADED authority and unrelated/
  historical/reused cycle grants. The existing identity test now challenges an
  oversized initial sample. These are evidence controls, not new product features.

The runtime gateway, installer and shipped systemd unit are unchanged. A fresh
no-mount VM must run the installed wheel, both platform suites, seven recovery
scenarios, actual systemd lifecycle, both boot witnesses, readonly repair and the
complete same-process forty-cycle observation before current evidence is promoted.
Failed stages/timeouts/source changes/cleanup errors still prevent success.

## Review limits

Reviewers' first passes were independent; subsequent diff and result checks use
known findings and are not new blind reviews. Offline checks cannot authenticate
fabricated telemetry. VM execution is performed by the main agent, not independently
reproduced by either reviewer. Source-specific prior JSON/HTML remains archived
byte-for-byte in [initial closeout evidence](../evidence/closeout-initial-01.json).
The current run's measured values and control count are in
[results](EXPLORATION_RESULTS.md).

Normal shutdown/reboot is not sudden power loss. Power-loss recovery, boot-zero-gap,
actual suspend, long-term rollover/endurance, hostile local users and arbitrary
production network provisioning remain unqualified. RSS can rise while remaining
within these bounded gates; neither no-leak nor plateau behavior is promised.
Private repository; no project license selected.
