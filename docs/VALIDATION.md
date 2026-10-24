# Isolated Linux validation and reproduction

Use the source checkout and its declared Python >=3.12 environment. Install
setuptools>=77 and wheel in that environment, then build:

```sh
.venv/bin/python -c 'import setuptools.build_meta as b; b.build_wheel("results/dist")'
.venv/bin/python -m tools.validate \
  --colima-home /ABSOLUTE/DEDICATED_COLIMA_HOME \
  --toolchain /ABSOLUTE/COLIMA_TOOLCHAIN_BIN \
  --profile gw-exp-FRESH_NAME \
  --wheel results/dist/grantweft-0.1.0-py3-none-any.whl \
  --output results/FRESH_OUTPUT
```

A fresh gw-exp-* VM and absent data disk are required. The runner refuses reuse,
uses 2 vCPU / 2 GiB / requested 15-GiB data disk, no host mounts and no default
context activation, installs Python/OpenSSL/iproute2/util-linux from the guest
package manager, installs the no-dependency wheel, removes product source from
import reach and verifies installed module SHA-256. Tools/tests remain a checkout.
Both platforms run the same source-bound test IDs (28 formal-service tests plus six evidence/cleanup
controls in the reviewed run). OS/SQLite/OpenSSL versions
are captured; no firmware, hardware network or physical-storage claim follows.

Root creates only test network namespaces inside this VM:

```text
client gw-client (10.70.0.2)
       | veth / 10.70.0.0/24
router gw-router (10.70.0.1, 10.71.0.1)
       | veth / 10.71.0.0/24
backend gw-backend (10.71.0.2:9000)
```

A client route to the backend is deliberately present, but gateway namespace
IPv4 forwarding is disabled. Direct backend access must fail, while the actual
mTLS application proxy performs a verified roundtrip. Gateway runs as UID 65534
via runuser, with a 0700 owned store and no route/firewall privileges. Root fixture
and client subprocesses do not establish an untrusted-root threat model.

The installed formal gateway is tested separately from the backend fixture. A
controlled VM trial records 20 ordered 8-KiB roundtrips, live-session revocation,
client-observed positive EOF/reset termination (not timeout), sampled gateway RSS, fd count and managed allocated
bytes. Those are Linux VM observations; native test elapsed time is not a native
performance/RSS comparison. No baseline speedup or SLO is claimed.

For normal VM reboot, create ACTIVE and PENDING grants, SIGKILL the gateway and
save full catalog rows/hash before scheduling reboot. After boot-ID change, compare
the old journal before starting any new gateway; reconstruct only fixture topology,
then start the installed gateway. Old grants/data and stale epoch operations must
be refused; fresh request/approval must work. Fixture namespaces/processes are
explicitly cleaned, not part of service persistence. The service is manually
started, not systemd-autostart qualified. No abrupt-power-loss test.

Children are registered before readiness waits; cleanup attempts every owned
process/namespace and always attempts failure-receipt preservation. Cleanup errors
prevent case success. Partial guest receipts are fetched before deleting the VM.

Every subprocess stage has exit/timeout recording; stage failure or source changes
prevent a passing receipt. The runner retains JSON/HTML on failure and deletes
its owned VM/data disk in finally. A timeout kills the host stage process group;
VM deletion is the final containment boundary for possible remote leftovers.
Existing Colima profiles/statuses must remain unchanged. Raw commands, paths,
certificates, keys, databases, wheels and logs stay under ignored results or inside
the deleted VM. Only sanitized receipts are eligible for Git.

The review-v2 offline verifier requires complete ordered stages, actual platform
labels, postboot fresh-workload results, observed closure reason, recovered grant
states, raw stale-refusal outcomes and successful boot observations. Old receipts
without this contract are historical and are not accepted as current qualification.
