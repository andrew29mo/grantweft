# MIT adoption and dependency review

Repository-visibility statements below describe their recorded revision.
Grantweft is now Public; see [publication checks](PUBLICATION.md).

Date: 2026-10-25 (Asia/Taipei). Pre-adoption parent:
`badf7c898e71ac3f0f7cc3aa9f1ec6ca5a74dc2f`.
The owner selected MIT for Grantweft. The repository remains Private.

## Project grant and external components

[LICENSE](../LICENSE) contains the standard MIT grant, with copyright
2026 Andrew Yuan. [Third-party inventory](../THIRD_PARTY_NOTICES.md) distinguishes
Grantweft from its external runtime and development environment. The package
uses SPDX `License-Expression: MIT`; both the project license and inventory are
included as license/notice files in built distributions.

The runtime declares no third-party Python packages. Source and package inventory
show no vendored Python interpreter, OpenSSL/SQLite binary, upstream source,
model or dataset. Python's standard library/interpreter retain PSF and incorporated
terms; OpenSSL 3 retains Apache-2.0; SQLite's upstream deliverable code is public
domain. These upstream terms do not require relabelling this unbundled project
under a different license. They are not replaced by Grantweft's MIT grant.

The inventory links the official upstream license sources checked for this
adoption. Build tools and VM/guest packages remain separate external software.
A future combined interpreter/library/OS distribution requires review of its
actual bundled components and upstream notices; the Grantweft wheel is not such
a combined distribution.

## Metadata-only provenance change

[Adoption receipt](../evidence/license-adoption.json) compares the current inputs
with the immutable v8 [qualification](../evidence/latest.json). The only changed
qualified input is `pyproject.toml`, adding exactly:

```toml
license = "MIT"
license-files = ["LICENSE", "THIRD_PARTY_NOTICES.md"]
```

All other parsed configuration, runtime modules, service unit, tests and validation
tools are unchanged. The receipt records both fingerprints, the original TOML,
notice hashes and package hashes/inventories. LICENSE, notices and documentation
are additional artifacts outside the existing execution-source manifest.

Existing native/Linux/systemd/VM JSON and HTML retain their original bytes and
pre-license fingerprints. They are not rewritten as post-license VM results.
Their executable payload remains applicable because every module/service byte
in the new wheel equals the previously qualified installed payload. This does
not claim identical package bytes: metadata and included notices deliberately
change the archive hash.

## Checks performed

- Built the MIT wheel and sdist with setuptools 84.2.1, satisfying the existing
  setuptools>=77 build requirement.
- Verified MIT metadata and exact license/notice bytes in both distributions.
- Rebuilt a wheel from the sdist and repeated its metadata, notice and unchanged
  runtime-payload checks.
- Installed the new wheel without dependencies in a separate local virtualenv.
  Isolated imports, installed license metadata and all module/service hashes
  match expectations. Both CLI entry points pass `--help` checks.
- Existing v8 evidence verification still passes in ordinary/optimized Python,
  including all 133 corruption controls. Runtime, tests and tools match the
  qualification; only the declared packaging metadata differs.
- Checked current candidate files and notice/docs links for consistency and
  private information before upload. Wheels, source archives, install environments
  and build logs remain ignored local artifacts.

No functional suite, Linux VM, performance or recovery experiment was rerun for
this licensing-only task. The prior 51-test paired suites and 600-second VM run
remain source-specific historical execution evidence, connected by the exact
metadata-only comparison above. Power-loss recovery, boot-zero-gap and long-term
operation remain untested.

## Recheck the checkout relationship

From the source checkout, this verifies the metadata-only bridge without a VM:

```sh
.venv/bin/python - <<'PY'
import hashlib, json, tomllib
from pathlib import Path
from tools.unit import manifest, fingerprint
from tools.report import verify, controls
q = json.loads(Path('evidence/latest.json').read_text())
r = json.loads(Path('evidence/license-adoption.json').read_text())
assert verify(q) and controls(q) == q['controls']
assert manifest() == r['current_source']
assert fingerprint(manifest()) == r['current_source_sha256']
assert [k for k in manifest() if manifest()[k] != q['source'][k]] == ['pyproject.toml']
before = r['qualified_pyproject_toml']
assert hashlib.sha256(before.encode()).hexdigest() == q['source']['pyproject.toml']
after = tomllib.loads(Path('pyproject.toml').read_text())
assert after['project'].pop('license') == 'MIT'
assert after['project'].pop('license-files') == ['LICENSE', 'THIRD_PARTY_NOTICES.md']
assert after == tomllib.loads(before)
for name, digest in r['notice_sha256'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
print('MIT metadata bridge and unchanged execution inputs verified')
PY
```

Historical review statements that the license was unset describe their recorded
revision. The current project grant is the root MIT LICENSE. Repository visibility
is controlled separately and remains Private.
