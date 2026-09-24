# Changelog

This file summarizes released versions and work on the v0.7 feature branch.
Version 0.7.0 is a release candidate until it is tagged and published.

## 0.7.0 — Developer Product (release candidate)

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

## v0.6.0 — Consequence Custody

Extends the generic consequence model through controlled external execution,
adapter observation, verification, Effect, EffectProof, and Warrant lineage.

## v0.5.0 — Generic Consequence Core

Establishes consequence identity, evaluation Attempts, normalized assurance
inputs, Decision and Effect semantics, replay, idempotency, and proof
foundations.
