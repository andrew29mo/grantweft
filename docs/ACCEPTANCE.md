# Architecture decision and MVP acceptance

Four explorations must qualify the same minimal production modules. Model/reviewer
agreement is not evidence. The four groups qualified review-v2 (34 tests/platform: 28 formal service + six observer/cleanup controls,
installed Linux namespace trials and one normal VM reboot). Receipts, failed
attempts and exact limits live in evidence/README.md. The review repairs are documented in [REVIEW.md](REVIEW.md).
Milestone 1 extends this to 41 tests/platform: 35 formal service + six controls,
and seven installed-service recovery scenarios. No implementation is a production
deployment guarantee.

| Exploration | Required formal evidence |
| --- | --- |
| Identity / durable approval | Real mTLS, missing/unregistered certificate refusal; requester cannot approve or use another owner's grant; precommit fixed deadline, late commit cannot activate; historical retries remain historical after revoke/restart |
| Transfer / revocation races | Ordered real bytes, response after client half-close, malformed/truncated/EOF-after-DATA failures, connect registered before await, live/idle/slow transfer stopped, no fresh post-revoke nonce at backend |
| Time / storage / capacity | Real elapsed expiry and SIGSTOP/resume, delayed DB does not block expiry, bounded queue/session/catalog/handshake refusal, error/timeout retires access; no success from a late result |
| Recovery / isolation | Second process cannot recover/listen, old epochs/revisions refuse, client cannot directly reach backend, installed unprivileged gateway, boot-ID change and unchanged journal before new gateway, old grants invalidated and fresh approval works |

## Milestone 1 acceptance

- DEGRADED exposes first failure/action/SQLite code, effective denied state and
  an explicit repair-plus-restart contract; no online reset.
- Bounded grant/operation/event refusal retains all historical rows; full catalog
  revoke and expiry stop actual established sessions with positive EOF/reset.
- Real SQLite page-limit FULL, full tmpfs and live directory write denial retire
  authority; startup on an actual readonly mount fails; repair and restart preserve history and
  require fresh request/approval. Delayed commit after timeout remains unusable.
- Same formal product tests run natively and against installed Linux wheel,
  with module/source hashes and per-scenario JSON/HTML receipts.

## Remaining operational MVP gates

- Formal service packaging, startup failures, systemd stop/automatic restart and
  a fresh-VM installation/operator walkthrough.
- Bounded sustained operation/resource trends and eventual archive/rollover
  decisions. Raising finite limits is not indefinite catalog lifecycle.
- Additional control-pressure, credential expiry/rotation and callback schedules
  as required by the intended deployment. Global DEGRADED for approval/revoke
  revision conflict remains the chosen conservative behavior.
- No exact remote-stop latency claim: kernel in-flight bytes/backend effects
  cannot be recalled by a proxy.

Not qualified: sudden power loss, actual host suspend, boot-zero-gap, systemd
autostart, long-term stability, transparent session survival, WAN/NAT traversal,
SSO, arbitrary routing, malicious local root, tamper-proof audit or hard real-time
expiry while the process/kernel cannot run. Do not expand scope before reviewing
what the four experiments actually establish.
