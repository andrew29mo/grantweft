# Third-party components and scope

Grantweft's project source and documentation are licensed under the
[MIT License](LICENSE). Copyright (c) 2026 Andrew Yuan.
This does not relicense external software or grant rights to its trademarks.

The project declares no third-party Python package dependencies. Its wheel
contains Grantweft modules, its service unit and distribution metadata/notices;
it does not bundle an interpreter, cryptographic library, database library,
VM image, model or dataset. Its sdist contains project sources and notices.

| External component | Use | Upstream terms |
| --- | --- | --- |
| Python 3.12 standard library/interpreter | Runtime; ssl, asyncio, sqlite3, fcntl and other standard modules | [Python Software Foundation License Version 2 and incorporated notices](https://docs.python.org/3.12/license.html) |
| OpenSSL 3.x | Host Python TLS implementation and test certificate generation | [Apache License 2.0 for OpenSSL 3.0 and later](https://openssl-library.org/source/license/index.html) |
| SQLite | Host Python sqlite3 implementation | [Upstream deliverable code is dedicated to the public domain](https://www.sqlite.org/copyright.html) |

The recorded Linux qualification used Python 3.12.3, OpenSSL 3.0.13 and SQLite
3.45.1. Other host distributions may supply different versions and additional
notices. Releases before OpenSSL 3 use different terms; this notice does not
assert that every possible host distribution has identical licensing.

Build/test/VM prerequisites (including setuptools, wheel, OpenSSL CLI, Colima,
Lima, systemd and guest OS packages) are external tools, not shipped in the
Grantweft wheel. Their licenses remain their upstream licenses. This inventory
is not a replacement for those license texts. A distributor that additionally
bundles an interpreter, libraries or an OS/VM image must review and retain the
terms/notices for those actual artifacts independently.

The dependency declaration, source inventory and built artifacts were checked
for MIT adoption. No bundled third-party code requiring a conflicting project
license was identified. The upstream components above retain their own terms;
Grantweft's MIT label covers the project, not all software in its execution
or development environment.
