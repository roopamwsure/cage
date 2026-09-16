# CAGE v0.6 Definition of Done

CAGE v0.6 is complete only when the Generic Consequence Core and the Consequence Custody boundary satisfy every applicable release gate in this document.

This Definition of Done is a release audit, not a feature backlog. A criterion is complete only when the implementation, tests, documentation, packaging, and release evidence agree.

---

## Release Gate 1 — Decision and Effect remain independent

CAGE must preserve:

```text
Decision != Effect
```

A Decision describes what CAGE permitted for an evaluation Attempt.

An Effect describes what authoritative verification established about external reality.

The following shortcuts are forbidden:

```text
ADMITTED -> BOUND
REFUSED  -> NO_BIND
```

Verification evidence must demonstrate that Decision state alone cannot create Effect truth.

---

## Release Gate 2 — Execution result does not determine Effect

`AdapterExecutionResult` is a request-level execution observation only.

Current adapter states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

The following mappings are forbidden:

```text
ACKNOWLEDGED -> BOUND
REJECTED     -> NO_BIND
ERROR        -> NO_BIND
UNKNOWN      -> EFFECT_UNKNOWN
```

Within the authoritative CAGE custody workflow, Effect creation must be based on `EffectVerificationResult`.

A directly constructed `Effect` is only a value object and does not by itself constitute authoritative proof.

---

## Release Gate 3 — Canonical Decision semantics are preserved

Only these Decision states exist:

```text
ADMITTED
HELD
NARROWED
ESCALATED
REFUSED
```

`NO_BIND` is not a Decision state.

No implicit allow is permitted.

A missing or invalid `EvaluationOutcome` must not default to `ADMITTED`.

---

## Release Gate 4 — Canonical Effect semantics are preserved

Only these Effect states exist:

```text
BOUND
NO_BIND
EFFECT_UNKNOWN
```

Execution failure, timeout, missing response, adapter rejection, or absence of execution must not automatically become `NO_BIND`.

If external reality cannot be established, the correct Effect state is:

```text
EFFECT_UNKNOWN
```

---

## Release Gate 5 — NO_BIND requires authoritative evidence

`NO_BIND` requires authoritative verification supporting the claim that the intended consequence did not become effective.

`VERIFIED_NO_BIND` must require verification references.

The following are insufficient by themselves:

- adapter rejection;
- adapter error;
- timeout;
- transport failure;
- missing acknowledgement;
- lost response;
- no execution attempt.

---

## Release Gate 6 — Explicit uncertainty is preserved

`INCONCLUSIVE` verification must map to:

```text
EFFECT_UNKNOWN
```

CAGE must not manufacture certainty when external reality remains unresolved.

---

## Release Gate 7 — Consequence identity remains stable

One intended business consequence must preserve one Consequence identity across:

- repeated evaluation;
- replay;
- execution attempts;
- adapter execution observations;
- verification;
- reconciliation;
- Effect creation;
- EffectProof creation;
- later Warrants.

Creating a new Attempt, ExecutionAttempt, verification, Effect, EffectProof, or Warrant must not silently create a new business Consequence.

Broad execution-retry orchestration is outside v0.6. Any future execution-retry mechanism must preserve the existing Consequence identity.

---

## Release Gate 8 — Evaluation Attempt and ExecutionAttempt remain distinct

An evaluation `Attempt` represents one evaluation of a Consequence.

An `ExecutionAttempt` represents one identified attempt to carry an eligible Decision into external execution.

These identities must remain separate.

```text
Evaluation Attempt != ExecutionAttempt
```

---

## Release Gate 9 — Replay remains evaluation-only

Replay must:

- preserve the same Consequence;
- create a new evaluation Attempt;
- preserve the original business intent;
- optionally link to the previous Attempt;
- never automatically execute the external action.

Therefore:

```text
Replay != Execution Retry
Replay != Reconciliation
```

---

## Release Gate 10 — Consequence-level idempotency remains enforced

Equivalent requests using the same idempotency key must resolve to the same Consequence identity.

The same idempotency key with materially different business intent must fail explicitly.

Current business-intent equivalence includes:

- action type;
- principal identity;
- resource identity;
- requested effect.

It deliberately does not depend on:

- action identity;
- proposed Consequence identity;
- agent identity;
- Attempt identity;
- session identity;
- retry number;
- replay number.

---

## Release Gate 11 — Custody eligibility is explicit

Custody must enforce:

```text
ADMITTED
    -> original RequestedEffect

NARROWED
    -> Decision.permitted_effect

HELD
ESCALATED
REFUSED
    -> custody ineligible
```

Ineligible Decisions must fail before EffectAdapter invocation.

---

## Release Gate 12 — NARROWED executes only permitted_effect

A `NARROWED` Decision must preserve the original requested effect for auditability while executing only `permitted_effect`.

The original broader request must never reach the EffectAdapter.

Tests must prove the exact selected effect received by the adapter.

---

## Release Gate 13 — ExecutionCapability scope is enforced

`ExecutionCapability` must remain structurally scoped to the custody operation.

Current scope includes:

```text
consequence_id
action_type
resource_id
```

Custody must reject a capability for a different:

- Consequence;
- action type;
- resource.

A scope mismatch must fail before adapter invocation.

---

## Release Gate 14 — ExecutionCapability does not become credential storage

Generic Core must not store provider credential material in `ExecutionCapability`.

Examples that remain outside the generic capability model include:

- OAuth tokens;
- API keys;
- passwords;
- provider credentials;
- cloud role material;
- IAM policies;
- secrets;
- permission documents.

CAGE models execution-authority scope, not provider credential custody.

---

## Release Gate 15 — Execution requires explicit custody

Evaluation must never automatically execute an external action.

External mutation may occur only through an explicit custody execution path.

Current orchestration is:

```text
ExecutionAttempt
      |
      v
Decision
      |
      v
select_effect_for_custody()
      |
      v
validate_capability_for_custody()
      |
      v
EffectAdapter.execute(...)
      |
      v
AdapterExecutionResult
```

---

## Release Gate 16 — Adapter result lineage is validated

The adapter must return an `AdapterExecutionResult`.

The result must refer to the expected `ExecutionAttempt`.

A mismatched result must fail explicitly.

Custody must not create an Effect directly from an adapter result.

---

## Release Gate 17 — Verification is separate from execution

Execution and verification must remain separate responsibilities.

```text
EffectAdapter
    -> attempts external mutation

EffectVerifier
    -> determines external reality
```

The generic Core must not collapse these responsibilities into one semantic step.

---

## Release Gate 18 — Effect creation is verification-backed

Within the authoritative CAGE custody workflow, `EffectVerificationResult` provides the basis for Effect creation.

A directly constructed `Effect` does not by itself establish authoritative effect provenance.

Authoritative provenance is established when the Effect is bound to its verification lineage through `EffectProof`.

The mapping is:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

There must be no direct:

```text
AdapterExecutionResult -> Effect
```

shortcut.

---

## Release Gate 19 — Conclusive verification requires references

The following verification states must require verification references:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
```

`INCONCLUSIVE` may have no references.

Effect verification references must match the references from the verification result used to create the Effect.

---

## Release Gate 20 — Reconciliation does not execute

Reconciliation must operate on an existing `AdapterExecutionResult`.

It must not:

- invoke an EffectAdapter;
- create another external execution;
- create an execution retry;
- create an evaluation replay.

Therefore:

```text
Reconciliation != Replay
Reconciliation != Execution Retry
Reconciliation != Re-execution
```

---

## Release Gate 21 — Reconciliation preserves execution lineage

A later reconciliation may create a new:

- EffectVerificationResult;
- Effect;
- EffectProof;
- Warrant.

It must preserve the same underlying:

- Consequence;
- evaluation lineage;
- ExecutionAttempt;
- AdapterExecutionResult.

The v0.6 reconciliation Warrant test must demonstrate one adapter execution with multiple verification/Warrant states.

Current implemented scenario:

```text
one external execution
        |
        v
AdapterExecutionResult R1
        |
        +-- Verification V1 = INCONCLUSIVE
        |       |
        |       +-- Effect E1 = EFFECT_UNKNOWN
        |       +-- Warrant W1
        |
        +-- reconciliation of the same R1
                |
                +-- Verification V2 = VERIFIED_BOUND
                        |
                        +-- Effect E2 = BOUND
                        +-- Warrant W2
                            previous_warrant_id = W1
```

The adapter invocation count must remain:

```text
1
```

---

## Release Gate 22 — EffectProof preserves authoritative lineage

`EffectProof` must be backed by an `EffectVerificationResult`.

It must validate:

### Same Consequence

```text
Effect.consequence
==
EffectVerificationResult.consequence
```

### Matching state

```text
VERIFIED_BOUND   <-> BOUND
VERIFIED_NO_BIND <-> NO_BIND
INCONCLUSIVE     <-> EFFECT_UNKNOWN
```

### Matching verification evidence

```text
Effect.verification_refs
==
EffectVerificationResult.references
```

It must derive:

```text
verification_id
adapter_result_id
execution_attempt_id
```

---

## Release Gate 23 — Warrant preserves decision and effect provenance

A Warrant must preserve Decision lineage.

A decision-only Warrant must remain valid:

```text
DecisionProof
EffectProof = absent
```

When an EffectProof exists, Warrant must derive:

```text
consequence_id
action_id
attempt_id
execution_attempt_id
adapter_result_id
verification_id
```

A Warrant must reject DecisionProof and EffectProof objects that refer to different Consequences.

---

## Release Gate 24 — Historical Warrant lineage is preserved

Later verification must not rewrite earlier assurance history.

A later Warrant may reference an earlier Warrant using:

```text
previous_warrant_id
```

For example:

```text
Warrant W1
Effect = EFFECT_UNKNOWN
```

may later be followed by:

```text
Warrant W2
Effect = BOUND
previous_warrant_id = W1
```

The earlier uncertainty remains historically valid for the evidence available at that time.

---

## Release Gate 25 — Domain neutrality is preserved

The same Core must support materially different consequence types.

Cross-domain tests should continue to cover examples such as:

```text
database.delete
access.grant
payment.release
```

No payment-specific, database-specific, or access-specific production business logic may be hardcoded into generic Core.

---

## Release Gate 26 — Vendor neutrality is preserved

Generic Core must not require provider-specific assumptions or production dependencies on:

- AWS;
- Azure;
- GCP;
- OpenAI;
- Anthropic;
- MCP;
- Cedar;
- OPA;
- AuthZEN;
- any specific AI model;
- any specific agent runtime;
- any specific IAM platform;
- any specific execution provider.

Provider-specific integrations belong outside generic Core.

---

## Release Gate 27 — CAGE does not become IAM

CAGE may consume normalized identity, policy, delegation, approval, and constrained execution-authority inputs.

Generic Core must not recreate:

- provider IAM semantics;
- provider credential systems;
- policy engines;
- approval workflow systems;
- authorization platforms.

---

## Release Gate 28 — Local operation remains possible

CAGE Core must remain usable locally.

The production package must not require CAGE Cloud or another hosted CAGE service.

Current release target must remain compatible with:

```text
Python >= 3.11
```

No unintended production runtime dependency may be introduced.

---

## Release Gate 29 — Documentation matches implementation

Before release, the following must describe the implemented v0.6 semantics consistently:

```text
README.md
docs/architecture.md
docs/invariants.md
docs/v0.6-consequence-custody.md
docs/definition-of-done.md
```

Documentation must not claim that implemented v0.6 custody or reconciliation functionality is still future work.

Documentation must not describe unimplemented later-release functionality as already available.

---

## Release Gate 30 — Automated tests pass

The full automated test suite must pass before release.

Final Definition-of-Done audit checkpoint:

```text
Full suite: 279 passed
```

The full suite was rerun after documentation and release-hardening changes.

Required command:

```powershell
python -m pytest -q
```

Any failing test blocks the v0.6 release.

---

## Release Gate 31 — Production-core contamination scan passes

Before release, inspect production Core for accidental provider, framework, infrastructure, or domain coupling.

Production code must not accidentally depend on or hardcode:

```text
AWS
Azure
GCP
OpenAI
Anthropic
MCP
Cedar
OPA
AuthZEN
FastAPI
Redis
Kubernetes
KMS
HSM
PQC
payment-specific production logic
database-specific production logic
access-control-specific production logic
```

Domain strings in tests and documentation are acceptable where they demonstrate generic behavior.

---

## Release Gate 32 — Packaging and installation pass

Before release, verify:

- package imports;
- Python >= 3.11 support;
- no unintended runtime dependencies;
- editable installation;
- wheel build;
- clean wheel installation;
- clean-environment import smoke test;
- correct version metadata.

These checks are part of release hardening and must pass before tagging v0.6.0.

Packaging, dependency, clean-install, and import checks have passed against the current pre-release artifact.

The final version-metadata check remains pending until the explicit v0.6.0 release step updates package metadata to `0.6.0`, rebuilds the release artifact, and revalidates that artifact.

---

## Release Gate 33 — v0.6 scope remains disciplined

v0.6 does not require:

- CAGE Cloud;
- SaaS;
- billing;
- REST APIs;
- database persistence;
- provider-specific production adapters;
- MCP integration;
- provider credential custody;
- broad execution retry orchestration;
- cryptographic Warrant signatures;
- canonical Warrant serialization;
- independent cryptographic Warrant verification;
- HSM or KMS integration;
- post-quantum cryptography;
- AI risk intelligence;
- enterprise deployment;
- a new IAM system;
- a new policy language;
- full consequence graphs;
- advanced consequence lineage.

Those capabilities belong to later releases or integration packages.

---

## Current v0.6 Audit Status

The v0.6 Definition-of-Done audit is complete.

```text
v0.5 Generic Consequence Core              COMPLETE
v0.6 Consequence Custody implementation    COMPLETE
v0.6 authoritative verification            COMPLETE
v0.6 reconciliation                        COMPLETE
v0.6 Warrant lineage                       COMPLETE
v0.6 reconciliation Warrant lineage        COMPLETE
v0.6 documentation hardening               COMPLETE
v0.6 Definition-of-Done audit              COMPLETE
v0.6 pre-release hardening validation       COMPLETE
v0.6.0 release                             NOT STARTED
```

Release-hardening evidence collected during the audit:

```text
Full automated test suite                   279 passed
Idempotency focused test suite              11 passed
Production-core provider contamination      0 matches
Production-core domain contamination        0 matches
Python validation environment               Python 3.13.2
Required Python version                     >= 3.11
Production runtime dependencies             none
Wheel build                                 PASS
Clean-environment wheel installation        PASS
Installed package import                    PASS
Core module imports                         PASS
Pre-release installed package metadata      0.5.0
v0.6 scope-discipline audit                 PASS
```

Release Gates 1-31 and 33 are satisfied by the current implementation, tests, documentation, and audit evidence.

Release Gate 32 has passed its packaging, installation, dependency, and clean-import checks. Its final version-metadata requirement remains pending until the explicit v0.6.0 release step changes the package version from `0.5.0` to `0.6.0`, rebuilds the release artifact, and revalidates that artifact before tagging.

The final regression checkpoint for the Definition-of-Done audit is:

```text
279 passed
```

No production semantic failures were identified during the v0.6 Definition-of-Done audit.

---

## Final Release Rule

CAGE v0.6.0 may be released only when every Release Gate above is satisfied and the final release-hardening checks pass.

No single passing test or document is sufficient by itself.

The release decision must be based on consistent evidence across:

```text
semantics
implementation
tests
documentation
packaging
installation
version metadata
```
