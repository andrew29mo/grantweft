# Review of the four technical explorations

Reviewed parent: `f42981dbe6987b39e3948abd0f54f5b1c5101548`. Two read-only
reviewers independently inspected authority/transport and evidence/recovery.
Parent reproduced the historical-result failure and old-verifier/timeout false
acceptances. Their agreement alone is not validation; the revised installed
package must complete a new source-bound native/Linux/VM run.

## Confirmed defects and fixes

1. **Timeout was accepted as closure.** `socket.timeout` inherits `OSError`.
   Both the formal tests' `ended()` and the namespace holder accepted idle timeout
   as a closed tunnel. The reviewed helper requires positive transport EOF/reset;
   a timeout is a failed observation, and EOF/control frames alone are insufficient.
   A real live socketpair timeout negative control and positive EOF control now
   challenge this observer. Data denial tests require the actual NO_ACCESS response,
   not any generic socket error/timeout. TLS identity tests also reject timeout as
   an authentication result. The wait has one fixed overall deadline.
2. **Historical results shared mutable runtime state.** An approved row was
   simultaneously in the operation-result cache and the runtime grant map. Expiry
   changed original_result from ACTIVE/revision 2 to EXPIRED/revision 3, while
   restart restored the durable ACTIVE/revision 2 outcome. A formal mTLS regression
   failed on the old code. Runtime and immutable historical results are now deep
   copies. Both ordinary expiry and delayed-commit expiry are tested before/after
   restart. A committed historical ACTIVE result never grants current access.
3. **Incomplete cleanup and missing failure receipts.** A first cleanup timeout
   previously skipped other processes/namespaces and the receipt write. Children
   are now registered immediately on successful spawn, before readiness waits;
   cleanup continues after individual errors, aggregates them, closes pipes and
   always attempts a receipt. Forced-kill or cleanup errors prevent a passing case.
   Failure receipts are fetched before VM containment cleanup when available.
4. **The old verifier accepted incomplete evidence.** Empty stages, missing
   postboot fresh roundtrip and a Linux receipt labelled Darwin were independently
   reproduced as accepted. The versioned review-v2 verifier requires ordered stages,
   correct platforms and unique test counts, source consistency, positive closure
   reason, actual pre/postboot state, refusal results, reboot observations and a
   fresh verified workload after recovery. New corruption controls challenge these
   requirements; they do not authenticate a fabricated receipt cryptographically.

## Additional evidence improvements

The prior slow-consumer test did not observe a blocked userspace write queue.
A new formal test blocks backend reads, sends bounded data until the actual
backend transport buffer exceeds its high watermark, and requires the resulting
backpressure counter before revoking. It then requires positive tunnel termination
and no remaining owned session. Kernel-buffered data and backend effects remain
outside the gateway's recall ability.

The VM echo probe now assembles the response byte stream across DATA frames,
rather than assuming a TCP read preserves the sender's frame size. The gateway
namespace's ip_forward value is read back, and direct-connect failure reasons are
recorded. The normal-reboot catalog/hash/rows witness is retained; the reviewer
found its original ordering appropriate, not a shutdown-cleanup masquerade.

## DEGRADED remains an explicit availability limitation

A simultaneous approval/revoke at the old revision can commit approval and then
refuse the queued revoke as stale. Access is already terminally fenced; the whole
service becomes DEGRADED, and restart invalidates durable ACTIVE rows. The review
does not claim smooth per-grant reconciliation or automatic resumption. Database
queue/storage failure can likewise retire the service. Only the tested bounded
pressure cases are qualified, not arbitrary control-plane/CPU/Internet DoS.

## Evidence status and boundaries

The old raw receipt is preserved as `attempt-03.json/html`; it must not qualify
revised code. The immutable history defect, observer false positive and report
counterexamples are summarized in [manual review observations](../evidence/review-observations.json).
[Historical reviewed results](REVIEWED_EXPLORATION_RESULTS.md) identify that review run, test split,
timings/RSS and cleanup. No reviewer independently reran a VM; the parent runs the
revised reproducible runner and retains its complete evidence. Power loss, actual
suspend, systemd autostart, boot-zero-gap and long-term stability remain untested.
No license grant or visibility change is part of this review.

Milestone 1 adds explicit diagnostics and repair/restart qualification; see
[recovery contract](RECOVERY.md) and [current outcomes](EXPLORATION_RESULTS.md).
The earlier two-agent review is not an independent audit of later changes.
