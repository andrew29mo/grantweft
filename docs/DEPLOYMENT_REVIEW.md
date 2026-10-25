# Historical review of the installed deployment

Repository-visibility statements below describe their recorded revision.
Grantweft is now Public; see [publication checks](PUBLICATION.md).

License-status statements below describe the recorded pre-MIT revision. The
project now uses [MIT](../LICENSE); see [adoption review](LICENSE_REVIEW.md).

Reviewed parent: `fc92369bf459bb1620e0dc5b035a6f2b49a3a603`.
Two read-only agents independently inspected service/runtime lifecycle and evidence.
The main agent reproduced the verifier counterexamples, repaired qualification
assertions and runs the new source-bound installed-package VM. Review agreement
is not proof; reviewers did not independently rerun the VM.

## Findings and repairs

No confirmed runtime privilege escalation, old-grant revival, broken atomic rename
or failed cleanup was observed in the original qualification. Three P2 acceptance
gaps were reproduced by altering copies of the actual receipt:

1. The systemd stage's own topology/direct-backend evidence could be absent or
   claim forwarding enabled/backend reachable, while other stages' isolation still
   allowed the overall record to pass. The reviewed verifier requires the actual
   systemd stage's independently recreated isolation and failed direct connect.
2. Crash takeover could contain MainPID=0, inactive state, empty invocation, root
   effective/saved UIDs or a different argv. The original fixture's runtime checks
   were stronger than its offline verifier. All initialized service instances now
   require a live positive MainPID, valid invocation, unchanged security/budget
   properties and a matching observed /proc PID, all UID columns, argv, no-new-
   privileges and empty effective capabilities.
3. DEGRADED could claim READY, live sessions or ALLOWED grants; repaired catalog
   rows could remain ACTIVE or disappear. Original real receipts were consistent,
   but the fixture directly asserted too few of these properties. The reviewed
   fixture requires complete status, consistent health, zero sessions and all old
   grants denied; every old grant is probed with its owner certificate before and
   after repair. A new request while DEGRADED must actually return DEGRADED.
   Catalog counts/history/file IDs remain equal while every old PENDING/ACTIVE
   row becomes INVALIDATED with revision+1; status must match those rows.

Runtime gateway, installer and shipped unit are unchanged by these review fixes.
The existing atomic-publication regression still pauses the actual startup write
mid-publication, checks final receipt absence, releases it and authenticates to the
real gateway; it is not a JSON-rendering-only test. Atomic rename is not physical
power-loss durability, and a stale ready.json is not a live readiness endpoint.

The new independent observer tests challenge contradictory DENIED status and old
catalog transitions with both positive and negative controls. They are counted
separately from formal product tests. The actual VM then exercises the original
installed runtime/unit with stronger observations; the report contract rejects
contradictory service identities, stages and authority states.

[Manual counterexamples](../evidence/systemd-review-observations.json) are derived
observations, not VM failures. The prior [JSON](../evidence/systemd-initial-01.json)
and [HTML](../evidence/systemd-initial-01.html) remain byte-for-byte historical.
That reviewed run and its corruption-control count are preserved in
[reviewed deployment results](SYSTEMD_REVIEWED_RESULTS.md). Later closeout
evidence is separately described in [current results](EXPLORATION_RESULTS.md).

## Independent review limits

The logic reviewer checked runtime/Store and installation/atomic-publication code,
then reviewed the fixes and ran the new observer tests with project Python 3.12.
Its first socket attempt was blocked at bind by sandbox EPERM and used unsupported
system Python 3.9; that attempt is not product validation. The evidence reviewer
checked raw receipts, source/provenance, HTML, controls and the new assertion
ordering, without creating a VM. The main agent performs full socket/VM tests.

The VM still uses a test namespace-only drop-in, trusted root fault fixture and a
root ptrace stop for configured stop-timeout testing. This is not kernel-I/O-hang,
power-loss, boot-autostart, boot-zero-gap, sustained-resource or hostile-same-UID
qualification. Finite capacity recovery still raises bounded limits and requires
new approval; no online reset, GC or rollover is supplied. Repository stays Private
with no project license selected.
