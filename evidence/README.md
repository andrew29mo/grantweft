# Technical exploration evidence

- [Final complete JSON](latest.json) / [HTML](latest.html): source unchanged,
  installed-package Linux evidence, same 25 tests/platform, namespace topology,
  normal VM reboot and 19 report corruption controls.
- [Native unit receipt](native-unit.json) / [Linux unit receipt](linux-unit.json).
- [Initial portable draft failure](initial-portable-failure.json).
- [Failed VM attempt 01](attempt-01.json) / [HTML](attempt-01.html).
- [Failed VM attempt 02](attempt-02.json) / [HTML](attempt-02.html).
- [Interpretation and actual limits](../docs/EXPLORATION_RESULTS.md).

Retained failures qualify nothing; final pass does not rewrite their causes or
source fingerprints. Raw private paths, logs, generated CA/private keys, databases,
wheels and VM images stay ignored. JSON/HTML pairs contain the same complete data.
No project license selected. Repository remains Private.

Recheck a passing receipt without running another VM:

```sh
.venv/bin/python -c 'import json; from tools.report import verify, controls; v=json.load(open("evidence/latest.json")); print(verify(v), controls(v))'
```

The report verifier uses explicit checks; it also rejects corruptions under
Python optimization. The VM/test runner requires normal Python and never treats
failed subprocess exits or timeouts as passes. Reproduction and distinct native/
VM timing/RSS scopes are documented in [validation](../docs/VALIDATION.md).
