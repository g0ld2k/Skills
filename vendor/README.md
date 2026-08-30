# Vendored Agent Skills reference

This directory contains the validation API from the official
`agentskills/agentskills` `skills-ref` package at revision
`69ef37e9424c0a7ea9dd2293b559e43ec8176379`.

The repository uses the package's Python validation path for every canonical
and generated skill. The CLI module and its Click dependency are intentionally
not vendored: repository validation imports only the library API. The source
`errors.py` carries a `from __future__ import annotations` compatibility line
so the repository's supported Python 3.9 validation runner can load the
reference package's PEP 604 annotation; this does not change runtime behavior.

The reference parser is StrictYAML-based. Its behavior is intentionally the
source of truth for YAML parsing, including string treatment for plain scalars,
accepted comments, quoted escapes, block scalars, and rejection of flow
collections. The reference package describes itself as demonstration software
and does not enforce every documented field constraint. The repository wrapper
therefore completes the Agent Skills checks for exact `SKILL.md` casing,
portable ASCII names, directory/name identity, non-empty compatibility,
string-valued flat metadata, and optional-field shapes. These remain spec
diagnostics. Separate house policies cover MIT licensing, `Use when`
descriptions, the deliberate `allowed-tools` ban, and validation scenarios.

`manifest.json` records immutable source/artifact URLs, versions, hashes, and
license notices. `scripts/validate-skills-repo.py` independently anchors the
exact artifact paths and hashes, rejects missing or unexpected files, and
finishes verification before adding any vendor path to Python's import search
path. Missing, extra, or changed artifacts therefore fail closed.

The wheel archives retain their upstream license files, and verbatim copies
are available under `licenses/`:

* `strictyaml` 1.7.3 — MIT, `strictyaml-1.7.3.dist-info/LICENSE.txt`
  and [`licenses/strictyaml-LICENSE.txt`](licenses/strictyaml-LICENSE.txt)
  (Copyright (c) 2014 Colm O'Connor).
* `python-dateutil` 2.9.0.post0 — dual Apache-2.0/BSD license,
  `python_dateutil-2.9.0.post0.dist-info/LICENSE` and
  [`licenses/python-dateutil-LICENSE.txt`](licenses/python-dateutil-LICENSE.txt)
  (Copyright 2017 Paul Ganssle and dateutil contributors).
* `six` 1.17.0 — MIT, `six-1.17.0.dist-info/LICENSE` (Copyright (c)
  2010–2024 Benjamin Peterson); see also
  [`licenses/six-LICENSE.txt`](licenses/six-LICENSE.txt).

The vendored `skills-ref` source is Apache-2.0; its complete notice is in
`skills_ref/LICENSE`.
