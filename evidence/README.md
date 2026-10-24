# Evidence and provenance

- [Current JSON](latest.json) / [HTML](latest.html): recovery-v3, matching frozen
  sources/installed runtime, 41 identical tests/platform (35 formal + six controls),
  seven storage/capacity/late-commit recovery scenarios, one normal VM reboot,
  42 corruption controls and complete cleanup.
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
