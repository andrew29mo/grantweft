# Wire protocol v0: fixed exploration format

Both ports require TLS >=1.2, server identity validation and an individually
registered client certificate. Every TLS stream carries one control request or
one backend session. No multiplexing, tunnel reuse, compression or arbitrary proxy.

Each frame: unsigned 8-bit type followed by unsigned 32-bit big-endian payload
length, then exactly that many bytes. Maximum payload 16,384 bytes. Incremental
reads require the complete payload before forwarding; oversized declared lengths
are rejected before allocation. JSON rejects NaN/Infinity literals and duplicate
keys. Duration validation also rejects numeric values that overflow to a
nonfinite floating-point result.

| Type | Meaning |
| --- | --- |
| 1 DATA | Ordered application bytes, only after successful OPEN and before that direction's EOF |
| 2 EOF | Zero-length application half-close |
| 3 CLOSE | Zero-length complete session termination |
| 4 OPEN | Control JSON, or data JSON containing exactly grant/service |
| 5 OK | JSON response or session admission acknowledgement |
| 6 ERROR | Bounded JSON refusal; never a grant |

Control mutation: action, operation UUID, integer epoch, plus service/duration
for request or grant/integer revision for approve/deny/revoke/cancel. Control
status supports an optional `after` grant-ID cursor; at most 16 visible rows are
returned per page, with next_cursor and remaining count. Repeated operations are
identified by principal + UUID + full canonical mutation payload.

Data OPEN binds one grant owner and configured service; no client address is
accepted. Gateway sends OK only after backend connect and repeated authorization
check. DATA cannot bypass OPEN. Client EOF maps to backend write_eof after earlier
DATA; backend replies continue. Backend EOF is sent as an EOF frame. The connector
sends CLOSE after consuming response EOF. Abrupt TLS termination is an error/abort,
not authenticated EOF. Duplicate EOF, DATA after EOF, nonempty control frames,
unknown type, oversized/truncated frames and idle frame timeout terminate the session.

Normal half-close may drain previous DATA. Revocation/expiry never waits for
normal EOF/TLS close_notify; it aborts transports and discards userspace queues.
Bytes already submitted to the kernel/remote service and remote side effects
cannot be recalled. Lack of a response does not imply a backend operation failed;
caller-level idempotency is outside this gateway's scope.

CLI control example after installing the runtime package:

```sh
grantweft --host GATEWAY_IP --port 7443 --ca CA_FILE --cert CLIENT_CERT \
  --key CLIENT_KEY --request '{"action":"status"}'
```

The stdio connector uses --port 7444 --grant GRANT_ID --service demo without
--request. TLS credentials remain owned by its user. It is not a shared local
TCP listener and does not authenticate other applications on the user's behalf.

Milestone 1 adds read-only status fields: health (READY/DEGRADED), first failure
code/action/SQLite error name/boottime observation, repair-plus-restart guidance,
and capacity used/limit/full/exact for grants, ops and events. `exact:false` means
counts may not describe current committed state; it is used while mutations are
in flight and throughout DEGRADED. `ok:true` on status means the query succeeded,
not that access is available. Historical mutation replies never reactivate access.
No network recovery/reset command exists. Error replies do not imply persistence
or cleanup succeeded; query current effective state when possible.
