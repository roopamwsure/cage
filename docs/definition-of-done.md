# CAGE v0.6 Definition of Done

CAGE v0.6 is complete when the Generic Consequence Core and Consequence
Custody boundary satisfy the applicable release gates in this document.

This is a release audit, not a feature backlog.

A gate is complete only when the implementation, tests, documentation,
packaging, and release evidence tell the same story.

---

## Release Gate 1 — Decision and Effect remain independent

CAGE preserves the distinction:

```text
Decision != Effect
```

A Decision records what CAGE permitted for an evaluation Attempt.

An Effect records what authoritative verification established about the
external business consequence.

These shortcuts are invalid:

```text
ADMITTED -> BOUND
REFUSED  -> NO_BIND
```

The test and verification evidence must show that Decision state alone cannot
establish Effect truth.

---

## Release Gate 2 — Execution result does not determine Effect

`AdapterExecutionResult` records what the adapter observed about an execution
request.

Its states are:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

None of these states determines the Effect directly.

```text
ACKNOWLEDGED -> BOUND
REJECTED     -> NO_BIND
ERROR        -> NO_BIND
UNKNOWN      -> EFFECT_UNKNOWN
```

These mappings are invalid.

Within the CAGE custody workflow, Effect creation is based on an
`EffectVerificationResult`.

A directly constructed `Effect` is only a value object. By itself, it does not
establish authoritative Effect provenance.

---

## Release Gate 3 — Canonical Decision semantics are preserved

The Decision state set remains:

```text
ADMITTED
HELD
NARROWED
ESCALATED
REFUSED
```

`NO_BIND` is an Effect state, not a Decision state.

CAGE also has no implicit allow.

An `ADMITTED` Decision must come from a valid `EvaluationOutcome`; missing or
invalid evaluation output cannot default to permission.

---

## Release Gate 4 — Canonical Effect semantics are preserved

The Effect state set remains:

```text
BOUND
NO_BIND
EFFECT_UNKNOWN
```

Execution failure, timeout, adapter rejection, a missing response, or the
absence of an execution attempt does not automatically establish `NO_BIND`.

When external reality cannot be established, the Effect is:

```text
EFFECT_UNKNOWN
```

---

## Release Gate 5 — NO_BIND requires authoritative evidence

`NO_BIND` means authoritative verification supports the conclusion that the
intended Consequence did not become effective.

The following are not enough by themselves:

- adapter rejection;
- adapter error;
- timeout;
- transport failure;
- missing acknowledgement;
- lost response; or
- no execution attempt.

`VERIFIED_NO_BIND` therefore requires verification references.

---

## Release Gate 6 — Explicit uncertainty is preserved

An `INCONCLUSIVE` verification maps to:

```text
EFFECT_UNKNOWN
```

If the evidence cannot establish either `BOUND` or `NO_BIND`, CAGE preserves
that uncertainty rather than making a stronger claim.

---

## Release Gate 7 — Consequence identity remains stable

One intended business operation keeps one Consequence identity across:

- repeated evaluation;
- replay;
- multiple ExecutionAttempts;
- adapter observations;
- verification;
- reconciliation;
- Effect creation;
- EffectProof creation; and
- later Warrants.

A new Attempt, ExecutionAttempt, verification result, Effect, EffectProof, or
Warrant does not by itself create a new business Consequence.

General execution-retry orchestration is outside v0.6. Any explicitly supported
retry must preserve the existing Consequence identity.

---

## Release Gate 8 — Evaluation Attempt and ExecutionAttempt remain distinct

An evaluation `Attempt` represents one evaluation of a Consequence.

An `ExecutionAttempt` represents one identified attempt to carry an eligible
Decision into external execution.

They are different lifecycle events and keep separate identities.

```text
Evaluation Attempt != ExecutionAttempt
```

---

## Release Gate 9 — Replay remains evaluation-only

Replay:

- preserves the same Consequence;
- creates a new evaluation Attempt;
- preserves the original business intent;
- may link to the previous Attempt; and
- does not automatically execute the external operation.

Therefore:

```text
Replay != Execution Retry
Replay != Reconciliation
```

---

## Release Gate 10 — Consequence-level idempotency remains enforced

Equivalent requests using the same idempotency key resolve to the same
Consequence.

If the same key is reused for materially different business intent, CAGE fails
explicitly rather than silently treating the requests as the same operation.

Current business-intent equivalence includes:

- action type;
- Principal identity;
- Resource identity; and
- RequestedEffect.

It does not depend on:

- Action identity;
- proposed Consequence identity;
- Agent identity;
- Attempt identity;
- session identity;
- retry number; or
- replay number.

---

## Release Gate 11 — Custody eligibility is explicit

Custody allows only eligible Decisions to reach execution.

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

An ineligible Decision stops before `EffectAdapter` invocation.

---

## Release Gate 12 — NARROWED executes only permitted_effect

A `NARROWED` Decision preserves the original RequestedEffect for audit and
lineage, but execution receives only `permitted_effect`.

The broader original request must never reach the `EffectAdapter`.

Tests must verify the exact effect passed to the adapter.

---

## Release Gate 13 — ExecutionCapability scope is enforced

`ExecutionCapability` remains scoped to the custody operation it authorizes.

Current scope includes:

```text
consequence_id
action_type
resource_id
```

Custody rejects a capability that refers to a different:

- Consequence;
- action type; or
- Resource.

A scope mismatch stops execution before the `EffectAdapter` is called.

---

## Release Gate 14 — ExecutionCapability does not become credential storage

`ExecutionCapability` represents execution-authority scope.

It does not store provider credential material such as:

- OAuth tokens;
- API keys;
- passwords;
- cloud credentials;
- role material;
- IAM policies;
- secrets; or
- permission documents.

Credential management remains outside the generic Core.

---

## Release Gate 15 — Execution requires explicit custody

Evaluation does not trigger an external mutation automatically.

Execution begins only through the explicit custody path:

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

This keeps evaluation and external execution as separate lifecycle operations.

---

## Release Gate 16 — Adapter result lineage is validated

The adapter must return an `AdapterExecutionResult`.

That result must belong to the expected `ExecutionAttempt`.

A mismatched result is a contract failure and must be rejected explicitly.

Custody does not create an Effect directly from an adapter result.

---

## Release Gate 17 — Verification is separate from execution

Execution and verification remain separate responsibilities.

```text
EffectAdapter
    -> attempts the external mutation

EffectVerifier
    -> examines the resulting external state
```

The generic Core must not collapse these into a single semantic step.

An execution observation is not the same thing as authoritative verification.

---

## Release Gate 18 — Effect creation is verification-backed

Within the CAGE custody workflow, an `EffectVerificationResult` provides the
basis for creating an Effect.

A directly constructed `Effect` is only a value object. It does not by itself
establish authoritative provenance.

That provenance is established when the Effect is tied to its verification
lineage through `EffectProof`.

The mapping remains:

```text
VERIFIED_BOUND
    -> BOUND

VERIFIED_NO_BIND
    -> NO_BIND

INCONCLUSIVE
    -> EFFECT_UNKNOWN
```

There is no direct:

```text
AdapterExecutionResult -> Effect
```

shortcut.

---

## Release Gate 19 — Conclusive verification requires references

The conclusive verification states:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
```

require verification references.

`INCONCLUSIVE` may have no references.

The references stored on the resulting Effect must match those carried by the
`EffectVerificationResult` used to create it.

---

## Release Gate 20 — Reconciliation does not execute

Reconciliation works from an existing `AdapterExecutionResult`.

It does not:

- invoke an `EffectAdapter`;
- create another external execution;
- create an execution retry; or
- create an evaluation replay.

Therefore:

```text
Reconciliation != Replay
Reconciliation != Execution Retry
Reconciliation != Re-execution
```

Reconciliation changes what CAGE can establish about an earlier execution. It
does not send the operation again.

---

## Release Gate 21 — Reconciliation preserves execution lineage

A later reconciliation may create a new:

- `EffectVerificationResult`;
- Effect;
- `EffectProof`; and
- Warrant.

It preserves the same underlying:

- Consequence;
- evaluation lineage;
- `ExecutionAttempt`; and
- `AdapterExecutionResult`.

The implemented reconciliation scenario is:

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

The adapter invocation count remains:

```text
1
```

The test must demonstrate that later verification can change the assurance
state without causing another external execution.

---

## Release Gate 22 — EffectProof preserves authoritative lineage

`EffectProof` must be backed by an `EffectVerificationResult`.

It validates three relationships.

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

The proof also derives:

```text
verification_id
adapter_result_id
execution_attempt_id
```

Together, these checks keep the Effect claim connected to the verification
lineage that supports it.

---

## Release Gate 23 — Warrant preserves Decision and Effect provenance

A Warrant always preserves Decision lineage.

A decision-only Warrant remains valid:

```text
DecisionProof
EffectProof = absent
```

When an `EffectProof` is present, the Warrant also derives:

```text
consequence_id
action_id
attempt_id
execution_attempt_id
adapter_result_id
verification_id
```

A Warrant must reject a `DecisionProof` and `EffectProof` that refer to
different Consequences.

---

## Release Gate 24 — Historical Warrant lineage is preserved

Later verification adds to the assurance history rather than rewriting it.

A later Warrant may reference an earlier one through:

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

`W1` remains a valid record of what CAGE could establish at the earlier point
in time.

`W2` records the later assurance state after additional verification.

---

## Release Gate 25 — Domain neutrality is preserved

The same Core must support materially different Consequence types.

Cross-domain tests should continue to exercise examples such as:

```text
database.delete
access.grant
payment.release
```

Generic Core must not hardcode production business logic for any one domain.

Domain-specific behavior belongs in supplied inputs, evaluation logic, or
integration layers.

---

## Release Gate 26 — Vendor neutrality is preserved

Generic Core must not depend on provider-specific behavior or production
dependencies tied to:

- AWS;
- Azure;
- GCP;
- OpenAI;
- Anthropic;
- MCP;
- Cedar;
- OPA;
- AuthZEN;
- a specific AI model;
- a specific agent runtime;
- a specific IAM platform; or
- a specific execution provider.

Provider-specific behavior belongs at integration boundaries, not inside the
generic Core.

---

## Release Gate 27 — CAGE does not become IAM

CAGE may consume normalized identity, policy, delegation, approval, and scoped
execution-authority information.

Generic Core does not recreate:

- provider IAM semantics;
- credential systems;
- policy engines;
- approval workflow systems; or
- authorization platforms.

Those systems remain external sources or integration points.

---

## Release Gate 28 — Local operation remains possible

CAGE Core remains usable as a local library.

The production package does not require CAGE Cloud or another hosted CAGE
service.

The v0.6 release target supports:

```text
Python >= 3.11
```

No unintended production runtime dependency is introduced.

---

## Release Gate 29 — Documentation matches implementation

The following documents must describe the implemented v0.6 behavior
consistently:

```text
README.md
docs/architecture.md
docs/invariants.md
docs/v0.6-consequence-custody.md
docs/definition-of-done.md
```

Implemented custody and reconciliation behavior must not be described as future
work.

Likewise, later-release capabilities must not be presented as part of v0.6.

---

## Release Gate 30 — Automated tests pass

The full automated test suite must pass for the release audit to succeed.

The final v0.6 Definition-of-Done checkpoint was:

```text
279 passed
```

The suite was rerun after the documentation and release-hardening work.

Command used:

```powershell
python -m pytest -q
```

A failing test would have blocked the v0.6 release.

---

## Release Gate 31 — Production-core contamination scan passes

The release audit included a production-Core contamination check for accidental
provider, framework, infrastructure, or domain coupling.

Production code was checked for dependencies or hardcoded behavior involving:

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

Domain names and provider references in tests or documentation remain acceptable
when they are used to demonstrate generic behavior.

---

## Release Gate 32 — Packaging and installation pass

The v0.6 release audit covered:

- package imports;
- Python >= 3.11 support;
- runtime-dependency review;
- editable installation;
- wheel build;
- clean wheel installation;
- clean-environment import smoke testing; and
- version metadata.

These checks passed against the v0.6.0 release artifact.

The installed package reported:

```text
0.6.0
```

as its package metadata version.

---

## Release Gate 33 — v0.6 scope remains disciplined

v0.6 establishes the Generic Consequence Core and Consequence Custody model.

The release does not require:

- CAGE Cloud;
- SaaS;
- billing;
- REST APIs;
- database persistence;
- provider-specific production adapters;
- MCP integration;
- provider credential custody;
- general execution-retry orchestration;
- cryptographic Warrant signatures;
- canonical Warrant serialization;
- independent cryptographic Warrant verification;
- HSM or KMS integration;
- post-quantum cryptography;
- AI risk intelligence;
- enterprise deployment;
- a new IAM system;
- a new policy language;
- full consequence graphs; or
- advanced consequence lineage.

Those capabilities belong to later releases, integration packages, or separate
product layers.

---

## v0.6 Audit Record

The v0.6 Definition-of-Done audit was completed successfully.

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
v0.6.0 release                             COMPLETE
```

Release-hardening evidence recorded during the audit:

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
Release artifact package metadata           0.6.0
v0.6 scope-discipline audit                 PASS
```

All 33 v0.6 Release Gates were satisfied by the implementation, tests,
documentation, packaging, installation, and audit evidence available at release.

The v0.6.0 wheel was built, installed in a clean environment, imported
successfully, and reported package metadata version `0.6.0`.

The final regression checkpoint was:

```text
279 passed
```

No production semantic failures were identified during the v0.6
Definition-of-Done audit.

---

## Release Rule

For v0.6.0, release required every applicable gate in this document to be
satisfied.

No single passing test, document, or packaging check was sufficient on its own.

The release decision depended on consistent evidence across:

```text
semantics
implementation
tests
documentation
packaging
installation
version metadata
```

That rule remains useful for future CAGE releases: a release should be judged
from the combined evidence, not from any one artifact in isolation.