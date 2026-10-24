# Installed systemd deployment

This Linux deployment uses the runtime wheel, a dedicated `grantweft` account and
the unit shipped inside that wheel. The gateway requires no root or capabilities.
Root performs installation/configuration and systemd manages its lifecycle. The
qualified topology is an isolated Linux VM with fixture namespaces. Deployment
must independently prevent clients from reaching the backend directly.

## Installation contract

Prerequisites: Linux with systemd, Python >=3.12 with venv/pip, useradd, and a
trusted runtime wheel built from the intended sources. Installation is a root
operation; use these fixed paths:

```sh
sudo python3 -m venv /opt/grantweft/venv
sudo /opt/grantweft/venv/bin/pip install --no-index --no-deps /PATH/grantweft-0.1.0-py3-none-any.whl
sudo /opt/grantweft/venv/bin/python -m grantweft.deploy
sudo install -d -o root -g grantweft -m 0750 /etc/grantweft/pki
sudo install -o root -g grantweft -m 0640 /SOURCE/ca.pem /etc/grantweft/pki/ca.pem
sudo install -o root -g grantweft -m 0640 /SOURCE/server.pem /etc/grantweft/pki/server.pem
sudo install -o root -g grantweft -m 0640 /SOURCE/server.key /etc/grantweft/pki/server.key
sudo install -o root -g grantweft -m 0640 /SOURCE/config.json /etc/grantweft/config.json
sudo systemctl start grantweft
```

The installer creates a system account/group if absent, creates a new config
folder as root:grantweft 0750, installs the exact shipped unit and reloads systemd.
It does not generate identities, overwrite configuration, start or enable the
service. Existing accounts/config folders are operator-managed. Keep runtime
files root-owned; the gateway must not be able to modify its code or credentials.

Provision actual certificate fingerprints and roles before starting. Use listener
ports above 1023; the unit has no privileged-bind capability. The config
has the same schema as the formal implementation: cert/key/ca absolute paths,
control and data host/port objects, one fixed numeric backend/service ID, and
principals mapping certificate SHA-256 to requester/approver roles. Use distinct
identities; duplicate fingerprints fail before state/worker creation. Certificate
names/SANs must match the clients' gateway address. Sample test PKI is not a
production CA and is never installed on the host or committed.

Systemd creates `/var/lib/grantweft` with service ownership and 0700 mode. The unit
uses UMask 0077, NoNewPrivileges, an empty capability bounding set, ProtectSystem
strict, ProtectHome and PrivateTmp. AF_UNIX/INET/INET6 are permitted; only the tested
IPv4 topology is qualified. The writable state directory includes SQLite rollback
journals; page limits do not cap total filesystem/log/VM storage.

## Readiness, stop and crash restart

Type=notify/NotifyAccess=main requires READY from the initialized gateway. It is
sent only after durable boot recovery, TLS context setup and listener creation.
Initialization readiness is distinct from current health. Use authenticated
`status` for READY/DEGRADED, current epoch, capacity and effective access. A past
ready.json or `systemctl is-active` alone does not establish usable access.
READY does not probe backend availability; verify a newly approved application
operation. After=network.target does not promise address assignment or WAN
readiness; binding/startup failure still consumes the configured start budget.

Explicit stop uses TERM with control-group cleanup, a five-second stop timeout and
final KILL. Restart=on-failure requests restart after one second for unexpected
failure, with three starts per thirty-second limit. Those are configured budgets,
not a guaranteed outage bound. A stopped systemd process cannot itself enforce a
grant timer. No session survives process restart; old PENDING/ACTIVE grants become
INVALIDATED before accepting new requests. Every recovery requires fresh approval.

The VM qualifies normal stop and SIGKILL takeover, then a root-only ptrace stop of
the actual main process to prevent TERM handling until the configured final KILL.
The original SIGSTOP trial did not exercise timeout: systemd resumes stopped tasks
while stopping them. See [systemd kill semantics](https://www.freedesktop.org/software/systemd/man/252/systemd.kill.html)
and [ptrace stop semantics](https://man7.org/linux/man-pages/man2/ptrace.2.html).
The tracer is a VM fault fixture outside the service. ExecStart is unchanged;
no product `--barriers` flag is used by the installed service. This fault does not
qualify an uninterruptible kernel-I/O hang or physical-storage failure.

## DEGRADED and restart-limit repair

An active DEGRADED gateway remains running, refuses new authorization/admission,
and stops existing transfers. It does not exit to trigger automatic resumption.
The API is the health authority. A single observed stable interval is not an
endurance guarantee; the code's retirement latch remains until process exit.

1. Read authenticated status and preserve the error. Stop the unit.
2. Repair filesystem capacity/permissions or increase finite config limits; retain
   catalog and stable lock inode. Do not delete history or edit epochs/grants.
3. If start limiting was reached, inspect the failure before explicitly resetting
   it. `systemctl reset-failed grantweft` clears the unit's restart-limit state.
4. Run `systemctl start grantweft`, check a new authenticated epoch and old denied
   grants, then request/approve and verify actual backend operation.

The VM uses real catalog exhaustion for this installed-service scenario. Other
real SQLite FULL, full tmpfs and readonly scenarios remain separately qualified
through the same installed runtime in the earlier recovery stage. The installer
and lifecycle tests do not constitute a new fault test for every storage mode.

Invalid duplicate identities repeatedly fail startup until the real unit reaches
the start-rate limit. The tested systemd retains Result=exit-code; the journal
records "Start request repeated too quickly", with exactly three duplicate-identity
failures and a stable restart count of three. Result text alone is not acceptance. Fixing config and an explicit reset/start must recover; historical
catalog is retained, and old authority remains unusable. Restart limiting bounds
attempts, not disk journald storage. No journal quota or long-term log bound is
claimed.

## Tested boundary

The fixture installs the wheel and unit, then adds only NetworkNamespacePath in a
VM-owned drop-in. The main process's actual argv, UID, capabilities and no-new-
privileges are observed. Root fixture provisions topology and certificates;
production network provisioning is outside the installer. The drop-in is removed
and all unit processes/namespaces are cleaned before the dedicated VM is deleted.

The unit is not enabled in this qualification. The separate normal VM reboot
still starts the gateway manually after a pre-recovery journal witness. Formal
boot-autostart recovery, power loss, boot-zero-gap, sustained resources and the
clean-VM operator walkthrough beyond this scripted fixture remain future gates.
No physical-device, WAN, unlimited retention or production-readiness guarantee.

## Reviewed service evidence

The reviewed qualification additionally binds observed /proc identity to each
initialized systemd MainPID, checks the systemd stage's own isolated topology,
and snapshots all old grants before fresh approval. DEGRADED and repaired states
require complete zero-session DENIED status and owner-authenticated NO_ACCESS for
every old grant. Catalog/state/revision preservation is directly asserted, not
inferred only from one failed data probe. See [deployment review](DEPLOYMENT_REVIEW.md).
