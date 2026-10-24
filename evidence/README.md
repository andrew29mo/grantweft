# Evidence and provenance

- [Current JSON](latest.json) / [HTML](latest.html): systemd-v5, matching frozen
  sources/installed runtime, 44 identical tests/platform (38 formal + six controls),
  seven storage/capacity/late-commit recovery scenarios, installed systemd lifecycle,
  one manual-start normal VM reboot,
  72 corruption controls and complete cleanup.
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
VM images remain ignored. Private repository, no project license selected.

Recheck without starting a VM (also works with `python -O`):

```sh
.venv/bin/python -c 'import json; from tools.report import verify, controls; v=json.load(open("evidence/latest.json")); print(verify(v), controls(v))'
```

This checks evidence structure, not independent reproduction or cryptographic
proof. The VM/test runner requires normal Python; failed/timed-out stages or
incomplete cleanup cannot pass. See [reproduction](../docs/VALIDATION.md).
