# Changelog

This file summarizes released versions and notable development changes.

## 0.7.1 â€” PyPI Distribution

### Added

- PyPI-facing package metadata, including README rendering, project URLs,
  author information, keywords, and supported Python classifiers.
- GitHub Actions Trusted Publishing workflow for tokenless PyPI publication
  through the dedicated `pypi` environment.
- PyPI installation guidance for `cage-assurance`.

### Runtime compatibility

- No CAGE runtime semantic changes from v0.7.0.

## 0.7.0 â€” Developer Product

### Added

- High-level `CAGE` facade for evaluation, guarded execution, verification,
  and observation-only reconciliation with typed result and recovery errors.
- Configurable ID generation and explicit record-ID overrides; known
  predecessor collisions raise `IdentityConflictError`, a `CAGEValueError`.
- Portable Warrant v1 JSON export, readback, structural validation, file
  helpers, and SUMMARY and FULL disclosure profiles.
- `cage` CLI for local examples and portable Warrant inspection and
  validation, with disposable database, access, and payment scenarios.
- Quickstart, integration, recovery, semantic, and portable Warrant guides;
  CI test matrix and package checks.

### Security and compatibility notes

- CLI inspection escapes control characters in displayed Warrant identifiers.
- Portable records do not provide cryptographic authenticity or restore
  facade dispatch history. SUMMARY is not anonymization.
- Baseline v0.6 core modules, public signatures, and existing test functions
  remain present. The [release review](docs/v0.7-release-readiness.md)
  tracks evidence and remaining gates before v0.7 is declared ready.

## v0.6.0 â€” Consequence Custody

Extends the generic consequence model through controlled external execution,
adapter observation, verification, Effect, EffectProof, and Warrant lineage.

## v0.5.0 â€” Generic Consequence Core

Establishes consequence identity, evaluation Attempts, normalized assurance
inputs, Decision and Effect semantics, replay, idempotency, and proof
foundations.
