# Technical exploration evidence

- [Current reviewed JSON](latest.json) / [HTML](latest.html): contract review-v2,
  unchanged frozen source, installed Linux package, same 34 tests/platform
  (28 formal service, six observer/cleanup controls), namespace topology, one
  normal VM reboot and 33 report corruption controls.
- [Native unit receipt](native-unit.json) / [Linux unit receipt](linux-unit.json).
- [Manual pre-fix counterexamples](review-observations.json) and
  [review findings](../docs/REVIEW.md).
- [Original superseded 25-test run](attempt-03.json) / [HTML](attempt-03.html):
  positive source observations retained; its timeout/closure observer and missing
  verifier checks prevent treating it as current reviewed qualification.
- [Initial portable draft failure](initial-portable-failure.json).
- [Failed VM attempt 01](attempt-01.json) / [HTML](attempt-01.html).
- [Failed VM attempt 02](attempt-02.json) / [HTML](attempt-02.html).
- [Current interpretation and limits](../docs/EXPLORATION_RESULTS.md).

Failures/superseded records qualify no revised code. Their original bytes and
source fingerprints are preserved. Raw private paths, logs, generated CA/private
keys, databases, wheels and VM images remain ignored. JSON/HTML pairs contain the
same data. No project license selected; repository remains Private.

Recheck current evidence without starting another VM:

```sh
.venv/bin/python -c 'import json; from tools.report import verify, controls; v=json.load(open("evidence/latest.json")); print(verify(v), controls(v))'
```

Checks also reject corruptions under Python optimization. The VM/test runner
requires normal Python and never treats subprocess failure/timeout or incomplete
cleanup as success. See [reproduction](../docs/VALIDATION.md).
