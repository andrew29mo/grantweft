# Review of milestone 1

Repository-visibility statements below describe their recorded revision.
Grantweft is now Public; see [publication checks](PUBLICATION.md).

License-status statements below describe the recorded pre-MIT revision. The
project now uses [MIT](../LICENSE); see [adoption review](LICENSE_REVIEW.md).

Historical source-specific review. Current qualification and boundaries are in
[current results](EXPLORATION_RESULTS.md).

Reviewed parent: `1a91800666381a5b99f6a1e41e3f963e40253820`.
Two read-only reviewers independently inspected product authority and evidence.
The main agent reproduced the counterexamples, implemented repairs and performs
new source-bound native/installed-Linux/VM qualification. Reviewer agreement is
not proof; reviewers did not independently rerun the VM.

## Confirmed repairs

1. **Invalid identity configuration could hang startup.** The gateway checked
   duplicate certificate fingerprints after starting the non-daemon SQLite thread.
   The real subprocess raised DUPLICATE_IDENTITY but remained alive waiting on an
   idle queue. Identity uniqueness is now checked before creating the state root,
   writer lock or worker. A formal CLI subprocess regression requires nonzero exit,
   the exact error and absence of the state root. This defect was reproduced by
   the main agent; the logic reviewer independently checked the fix and ran the
   regression. No grant-revival defect was observed in that review.
2. **Incomplete offline evidence acceptance.** The evidence reviewer reproduced
   accepted zero/missing exit codes for late data refusals. Follow-up and main-agent
   checks found missing catalog admission/revoke outcomes, missing old grant rows,
   reset counts and explicit cleanup-error markers could also pass the verifier.
   Current raw receipts had actual nonzero refusals and intact old rows; these
   acceptance holes do not establish a data-plane bypass or catalog-loss incident.
   The new contract requires expected refusal codes/exits, successful committed
   grant-full revocation, retained IDs/counts and absence of failure markers.
3. **Stronger preservation and replay observations.** Every recovery case now
   records the stopped catalog and the postboot catalog before fresh mutations:
   committed counts, ordered grant states/revisions/epochs, a digest of ordered
   operation/audit history and device/inode IDs of catalog and writer.lock.
   Recovery must preserve counts, history and file identities, with only the
   defined grant invalidation/revision changes. Post-workload status must account
   for one new grant plus two operations/audit events.
   The delayed approval case retries its exact timed-out UUID after restart:
   historical ACTIVE may be read, but fresh data admission must still be NO_ACCESS.
   The formal service regression also checks this boundary.

[Manual pre-fix counterexamples](../evidence/milestone-review-observations.json)
are labelled observations, not VM receipts. The original milestone record remains
[historical JSON](../evidence/milestone-01.json) / [HTML](../evidence/milestone-01.html).
It qualifies its frozen sources; the revised contract intentionally rejects it.

## Review scope and limitations

The logic reviewer exercised actual Store/Gateway state with SQLite without
network sockets: catalog-full fencing, delayed ACTIVE commit after timeout and
restart invalidation. Its full service suite was blocked by localhost bind EPERM
in the review environment, before product socket behavior; this is not a passing
network test. The main agent runs the full suite with local network permission.
The evidence reviewer checked raw JSON/HTML/source consistency, counterexamples
and verifier repairs. Actual installed-package VM evidence is produced by the main
agent's reproducible runner; final counts/results are in [current outcomes](EXPLORATION_RESULTS.md).

The snapshot digest tests consistency across the controlled restart, not physical
power-loss durability, tamper resistance or indefinite retention. DEGRADED still
requires repair plus restart; catalog recovery raises finite limits and retains
history. There is no online reset, automatic GC or rollover. Global retirement on
approval/revoke conflict remains an availability limitation. Formal systemd,
long-term operation, power loss and boot-zero-gap remain unqualified. Private
visibility and no project license are unchanged.
