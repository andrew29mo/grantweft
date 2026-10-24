# Architecture decision and MVP acceptance

Four explorations must qualify the same minimal production modules. Model/reviewer
agreement is not evidence. The four groups now have passing source-bound evidence (25 tests/platform,
installed Linux namespace trials and one normal VM reboot). Receipts, failed
attempts and exact limits live in evidence/README.md. No implementation is a production deployment guarantee.

| Exploration | Required formal evidence |
| --- | --- |
| Identity / durable approval | Real mTLS, missing/unregistered certificate refusal; requester cannot approve or use another owner's grant; precommit fixed deadline, late commit cannot activate; historical retries remain historical after revoke/restart |
| Transfer / revocation races | Ordered real bytes, response after client half-close, malformed/truncated/EOF-after-DATA failures, connect registered before await, live/idle/slow transfer stopped, no fresh post-revoke nonce at backend |
| Time / storage / capacity | Real elapsed expiry and SIGSTOP/resume, delayed DB does not block expiry, bounded queue/session/catalog/handshake refusal, error/timeout retires access; no success from a late result |
| Recovery / isolation | Second process cannot recover/listen, old epochs/revisions refuse, client cannot directly reach backend, installed unprivileged gateway, boot-ID change and unchanged journal before new gateway, old grants invalidated and fresh approval works |

## Operational MVP gates that remain separate

- Give operator responses a complete persistence/cleanup contract for every error,
  including targeted reconciliation of concurrent approval/revoke. Current conflict
  causes global DEGRADED and requires restart; it is safe but disruptive.
- Qualify an explicit operator recovery workflow and bounded catalog lifecycle;
  current finite history refuses on exhaustion and has no rollover/GC.
- Qualify installation/service packaging, startup failures, certificate expiry/
  replacement and stronger control-pressure handling as required by intended use.
- The exploration includes a deterministic pause after backend connect and before
  admission, then revoke and a fresh session. Additional kernel/TLS callback
  interleavings remain outside this one controlled schedule.
- Test disk ENOSPC/EROFS on a real managed filesystem if claiming them. Current
  storage-error hooks and real catalog/queue/session capacity refusals are distinct;
  a SQLite FULL error has not been physically induced.
- Evaluate and test cleanup evidence beyond current abort/task removal if claiming
  exact remote termination latency. Kernel in-flight bytes/backend effects remain
  outside a TCP proxy's recall ability.

Not qualified: sudden power loss, actual host suspend, boot-zero-gap, systemd
autostart, long-term stability, transparent session survival, WAN/NAT traversal,
SSO, arbitrary routing, malicious local root, tamper-proof audit or hard real-time
expiry while the process/kernel cannot run. Do not expand scope before reviewing
what the four experiments actually establish.
