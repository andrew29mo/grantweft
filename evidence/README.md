# Evidence and provenance

The project now uses [MIT](../LICENSE). Recorded qualification fingerprints
precede this license-only metadata update. [License adoption receipt](license-adoption.json)
and [review](../docs/LICENSE_REVIEW.md) bind the current metadata to unchanged
runtime/test/tool inputs. Existing JSON/HTML measurements are not rewritten or
represented as new VM runs.

- [Additional prepublication macOS test receipt](prepublication-native-01.json):
  51 tests against the unchanged qualified source. This supplemental run does not
  replace the paired native/Linux receipts or VM measurements in latest.
- [Current JSON](latest.json) / [HTML](latest.html): closeout-review-v8, matching frozen
  sources/installed runtime, 51 identical tests/platform (38 formal + thirteen controls),
  seven storage scenarios, installed systemd lifecycle, retained manual-start reboot,
  two enabled-systemd boot cases with old-journal witnesses, readonly repair,
  forty same-process cycles / 600 seconds, 133 corruption controls and cleanup.
- [Initial closeout](closeout-initial-01.json) / [HTML](closeout-initial-01.html):
  exact archived v7 bytes, 49 tests/platform / 122 controls; actual run consistent,
  superseded by stronger authority/grant/resource evidence relationships.
- [Closeout review observations](closeout-review-observations.json) and
  [findings](../docs/CLOSEOUT_REVIEW.md): modified copies, not VM incidents.
- [Previous reviewed deployment](systemd-reviewed-01.json) / [HTML](systemd-reviewed-01.html):
  exact archived v6 bytes, 46 tests/platform / 95 controls; historical manual-start boot scope.
- [Closeout attempt 01](closeout-attempt-01.json) / [HTML](closeout-attempt-01.html):
  failed readonly repair due to an unintentionally readonly loop backing device.
- [Closeout attempt 02](closeout-attempt-02.json) / [HTML](closeout-attempt-02.html):
  boot/repair passed, sustained setup failed on a preceding fresh grant left valid.
- [Original deployment](systemd-initial-01.json) / [HTML](systemd-initial-01.html):
  v5, 44 tests/platform and 72 controls; historical source-specific qualification.
- [Deployment review observations](systemd-review-observations.json) and
  [findings](../docs/DEPLOYMENT_REVIEW.md): altered receipt copies, not VM incidents.
- [Previous reviewed recovery](recovery-reviewed-01.json) / [HTML](recovery-reviewed-01.html):
  v4, 42 tests/platform and 60 controls; historical source-specific qualification.
- [Service attempt 01](service-attempt-01.json) / [HTML](service-attempt-01.html):
  failed SIGSTOP timeout injection; no stop timeout exercised.
- [Service attempt 02](service-attempt-02.json) / [HTML](service-attempt-02.html):
  real timeout/KILL passed, then unnecessary reset of an unloaded healthy unit failed.
- [Service attempt 03](service-attempt-03.json) / [HTML](service-attempt-03.html):
  failed too-specific restart Result expectation; diagnostic observations follow.
- [Service attempt 04](service-attempt-04.json) / [HTML](service-attempt-04.html):
  failed Linux suite due to torn startup-receipt JSON; repaired atomically.
- [Service attempt 05](service-attempt-05.json) / [HTML](service-attempt-05.html):
  failed publication-test wrapper arguments; corrected before qualification.
- [Service attempt 06](service-attempt-06.json) / [HTML](service-attempt-06.html):
  service cases passed; normal VM reboot witness failed, so the run failed.
- [Diagnostic observations](service-diagnostic-observations.json): derived from a
  non-qualification diagnostic; not an accepted run or an independent reproduction.
- [Original milestone](milestone-01.json) / [HTML](milestone-01.html): recovery-v3,
  41 tests/platform and 42 controls; superseded by the reviewed contract.
- [Manual milestone review counterexamples](milestone-review-observations.json) and
  [review findings](../docs/MILESTONE_1_REVIEW.md).
- [Native receipt](native-unit.json) / [Linux receipt](linux-unit.json).
- [Milestone attempt 01](milestone-attempt-01.json) / [HTML](milestone-attempt-01.html):
  failed live readonly remount (busy writable files).
- [Milestone attempt 02](milestone-attempt-02.json) / [HTML](milestone-attempt-02.html):
  failed startup-error observation; not promoted to success.
- [Milestone attempt 03](milestone-attempt-03.json) / [HTML](milestone-attempt-03.html):
  passed its sources; superseded by accurately named fault-phase timing field.
- [Historical reviewed run](review-01.json) / [HTML](review-01.html): review-v2,
  34 tests/platform and 33 corruption controls; qualifies only its frozen sources.
- [Manual pre-fix counterexamples](review-observations.json),
  [historical review](../docs/REVIEW.md).
- [Original superseded 25-test run](attempt-03.json) / [HTML](attempt-03.html):
  flawed timeout/closure observer and incomplete verifier, not current qualification.
- [Initial portable failure](initial-portable-failure.json).
- [Original failed VM attempt 01](attempt-01.json) / [HTML](attempt-01.html).
- [Original failed VM attempt 02](attempt-02.json) / [HTML](attempt-02.html).
- [Current interpretation and limits](../docs/EXPLORATION_RESULTS.md).

Historical/failed receipts preserve original bytes and source fingerprints. Their
JSON and HTML encode identical records, but only latest is checked against the
current contract. Raw paths/logs, credentials/private keys, databases, wheels and
VM images remain ignored. Repository is Public; project source and
documentation use MIT. Earlier license-status statements are historical.

Recheck without starting a VM (also works with `python -O`):

```sh
.venv/bin/python -c 'import json; from tools.report import verify, controls; v=json.load(open("evidence/latest.json")); print(verify(v), controls(v))'
```

This checks the recorded evidence structure, not the current checkout or an
independent reproduction/cryptographic proof. For the post-MIT checkout, also
run the [metadata-only bridge check](../docs/LICENSE_REVIEW.md#recheck-the-checkout-relationship). The VM/test runner requires normal Python; failed/timed-out stages or
incomplete cleanup cannot pass. See [reproduction](../docs/VALIDATION.md).
