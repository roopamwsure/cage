# CAGE

**Control Assurance Governance Evaluation**

CAGE is a vendor-neutral assurance layer for consequential AI and automated
actions.

It helps answer two different questions:

1. Should this proposed action be allowed to cross into a real-world business
   operation?
2. After execution, what can we establish actually became effective?

The distinction matters because:

```text
Decision != Effect
```

An action can be permitted without ever taking effect.

Likewise, an execution request can fail, time out, or return an ambiguous
response without proving that the intended business consequence did not occur.

CAGE keeps those states separate and preserves the lineage and evidence needed
to reason about them.

---

## Install

Install the published package from PyPI:

```bash
python -m pip install cage-assurance
```

Confirm the CLI installation:

```bash
cage --version
```

Use the SDK from Python:

```python
from cage import CAGE
```

Current package release:

```text
v0.7.1
```

Supported Python version:

```text
Python >= 3.11
```

CAGE currently has no production runtime dependencies outside the Python
standard library.

For a working example, start with the
[v0.7 Quickstart](docs/quickstart.md).

---

## What CAGE provides

CAGE gives developers a structured lifecycle for consequential operations:

```text
Action
  |
  v
Consequence
  |
  v
Evaluation Attempt
  |
  v
Decision
  |
  v
DecisionProof
  |
  v
Consequence Custody
  |
  v
ExecutionAttempt
  |
  v
External Execution
  |
  v
Execution Observation
  |
  v
Verification
  |
  v
Effect
  |
  v
EffectProof
  |
  v
Warrant
```

The architecture protects several important distinctions:

```text
Decision            != Effect
Evaluation Attempt  != ExecutionAttempt
Replay              != Execution Retry
Adapter Result      != Effect
Execution           != Verification
Reconciliation      != Re-execution
```

These separations let CAGE reason about permission, execution, evidence, and
external outcome without collapsing them into one status.

---

## Core terminology

A few terms have specific meanings in CAGE.

**Action**  
The proposed operation, including the Principal, Agent, Resource, and
RequestedEffect.

**Consequence**  
One intended business consequence. Its identity remains stable across
evaluation, execution, verification, and reconciliation.

**Attempt**  
One evaluation of a Consequence.

**Decision**  
What CAGE permits for a particular evaluation Attempt.

**DecisionProof**  
The Decision together with references to the assurance inputs that supported
it.

**Consequence Custody**  
The controlled boundary that carries an eligible Decision toward external
execution.

**ExecutionAttempt**  
One identified attempt to carry a Decision into external execution. It is
separate from an evaluation Attempt.

**AdapterExecutionResult**  
The adapter's observation about an execution request. It is not an Effect.

**Effect**  
What authoritative verification establishes about the resulting external
business consequence.

**EffectProof**  
The Effect together with the verification lineage supporting it.

**Warrant**  
An assurance record preserving Decision provenance and, when available, Effect
provenance.

For the full model, see
[Architecture](docs/architecture.md).

---

## Evaluation

CAGE can evaluate normalized assurance inputs such as:

- `Evidence`
- `Standing`
- `Delegation`
- `Approval`
- `Context`

The evaluation path is:

```text
Action
  |
  v
Consequence
  |
  v
Attempt
  |
  +-- Evidence
  +-- Standing
  +-- Delegation
  +-- Approval
  +-- Context
  |
  v
Evaluation Rule
  |
  v
EvaluationOutcome
  |
  v
Decision
  |
  v
DecisionProof
```

The supplied evaluation logic decides how domain-specific assurance inputs are
interpreted.

CAGE does not impose one universal policy language or one universal set of
assurance requirements.

There is no implicit allow.

An `ADMITTED` Decision must be produced explicitly by valid evaluation logic.

---

## Decision states

CAGE defines five Decision states:

```text
ADMITTED
HELD
NARROWED
ESCALATED
REFUSED
```

A Decision describes what CAGE permits for a particular evaluation Attempt.

It does not describe what happened in the external system.

`NO_BIND`, for example, is not a Decision state.

---

## NARROWED Decisions

A `NARROWED` Decision preserves both the original request and the smaller
effect CAGE permits.

For example:

```text
Requested:
Global Admin for 480 minutes

Permitted:
Scoped Operator for 30 minutes
```

Whether one effect is genuinely narrower than another is domain-specific and
belongs to the supplied evaluation logic.

At execution time, only `permitted_effect` may reach the adapter.

The broader original request remains available for audit and lineage but is not
executed.

---

## Consequence Custody

A Decision does not automatically trigger external execution.

An eligible Decision enters **Consequence Custody**, where CAGE controls the
transition from permission to execution.

Conceptually:

```text
Decision
    |
    v
ExecutionAttempt
    |
    v
select_effect_for_custody()
    |
    v
validate_capability_for_custody()
    |
    v
EffectAdapter
    |
    v
External System
```

Custody determines which effect may be executed and validates the scope of the
execution authority before the adapter is invoked.

Current eligibility is:

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

Ineligible Decisions stop before external execution.

---

## ExecutionAttempt

An `ExecutionAttempt` is not the same thing as an evaluation `Attempt`.

An evaluation Attempt means:

> one evaluation of a Consequence

An ExecutionAttempt means:

> one identified attempt to carry an eligible Decision into external execution

This distinction allows CAGE to keep replay and execution retry separate.

A replay creates another evaluation Attempt.

An explicitly supported execution retry would create another ExecutionAttempt
while preserving the same Consequence.

---

## ExecutionCapability

`ExecutionCapability` represents the scope of authority presented to custody.

Its current scope includes:

```text
consequence_id
action_type
resource_id
```

The capability must match the Consequence, action type, and Resource being
executed.

It is not a credential container.

Provider-specific tokens, passwords, API keys, roles, IAM policies, and other
credential material remain outside generic CAGE Core.

---

## Execution observations

`EffectAdapter` attempts the external mutation.

The adapter returns an `AdapterExecutionResult` with one of these states:

```text
ACKNOWLEDGED
REJECTED
ERROR
UNKNOWN
```

These are observations about the execution request.

They are not Effect states.

```text
ACKNOWLEDGED != BOUND
REJECTED     != NO_BIND
ERROR        != NO_BIND
UNKNOWN      != EFFECT_UNKNOWN
```

For example, an external system may acknowledge a request before the business
change is actually visible.

An error response can also be ambiguous: the request may have reached the
external system even if the caller did not receive a successful response.

CAGE therefore verifies the resulting external state separately.

---

## Authoritative verification

Execution and verification have different jobs.

```text
EffectAdapter
    -> attempts the external mutation

EffectVerifier
    -> examines what became true afterward
```

Verification produces one of three results:

```text
VERIFIED_BOUND
VERIFIED_NO_BIND
INCONCLUSIVE
```

Those results map to CAGE Effect states:

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

## Effect states

CAGE defines three Effect states.

### BOUND

`BOUND` means authoritative verification supports the conclusion that the
permitted Consequence became effective.

An API acknowledgement or successful request submission is not enough by
itself.

### NO_BIND

`NO_BIND` means authoritative verification supports the conclusion that the
intended Consequence did not become effective.

A timeout, rejected request, transport failure, or missing response does not
automatically establish `NO_BIND`.

### EFFECT_UNKNOWN

`EFFECT_UNKNOWN` means the available evidence cannot establish either
`BOUND` or `NO_BIND`.

CAGE preserves that uncertainty instead of turning an incomplete observation
into a stronger assurance claim.

---

## Replay

Replay re-evaluates an existing Consequence.

```text
Consequence C1
    |
    +-- Attempt A1 -> ESCALATED
    |
    +-- Attempt A2 -> ADMITTED
```

The Consequence and business intent remain the same while a new evaluation
Attempt is created.

Replay does not execute the external operation.

```text
Replay != Execution Retry
```

---

## Consequence-level idempotency

CAGE treats idempotency as protection of the business Consequence, not simply
as HTTP retry handling.

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

Reusing the same key for materially different business intent produces an
explicit conflict.

Current business-intent equivalence includes:

- action type;
- Principal identity;
- Resource identity; and
- RequestedEffect.

Evaluation attempts, agent sessions, retry counters, and replay counters do not
by themselves create a new Consequence.

---

## Reconciliation

Sometimes execution has already happened but external reality cannot yet be
established.

CAGE can verify that same execution again later:

```text
existing AdapterExecutionResult
        |
        v
EffectVerifier
        |
        v
new EffectVerificationResult
        |
        v
new Effect
        |
        v
new Warrant
```

Reconciliation does not send the external operation again.

```text
Reconciliation != Re-execution
```

For example:

```text
one external execution
        |
        v
AdapterExecutionResult R1
        |
        +-- Verification V1 = INCONCLUSIVE
        |       |
        |       +-- Effect = EFFECT_UNKNOWN
        |       +-- Warrant W1
        |
        +-- later reconciliation
                |
                +-- Verification V2 = VERIFIED_BOUND
                        |
                        +-- Effect = BOUND
                        +-- Warrant W2
                            previous_warrant_id = W1
```

The external execution happened once.

What changed later was the evidence available to CAGE.

---

## Warrants

A Warrant preserves an assurance view of a Consequence.

`DecisionProof` and `EffectProof` remain separate because permission and
external outcome are separate facts.

A Warrant can therefore exist before an Effect has been established:

```text
DecisionProof
EffectProof = absent
```

That is different from:

```text
DecisionProof
EffectProof(EFFECT_UNKNOWN)
```

In the second case, execution and verification have occurred, but external
reality remains unresolved.

When EffectProof is available, the Warrant preserves execution and verification
lineage.

Later Warrants can link to earlier Warrants through:

```text
previous_warrant_id
```

Earlier assurance records are not rewritten when new evidence becomes
available.

---

## Vendor and domain neutrality

CAGE Core is designed to stay independent of a particular:

- cloud provider;
- AI model;
- agent framework;
- IAM platform;
- policy engine;
- policy language;
- execution provider; or
- business domain.

Provider and domain-specific behavior enters through evaluation logic,
normalized inputs, adapters, verifiers, and other integration boundaries.

CAGE does not attempt to replace the systems around it.

Identity systems, policy engines, approval systems, agent runtimes, execution
platforms, observability systems, and cloud-security controls can instead
provide inputs or integrations to CAGE.

---

## Developer documentation

For implementation and integration work, start with:

- [Quickstart](docs/quickstart.md)
- [Integration guide](docs/integration-guide.md)
- [Semantic guide](docs/semantic-guide.md)
- [Failure and recovery](docs/failure-and-recovery.md)
- [Portable Warrants and CLI](docs/portable-warrants-and-cli.md)

For the underlying architecture:

- [Architecture](docs/architecture.md)
- [Core invariants](docs/invariants.md)
- [Consequence Custody](docs/v0.6-consequence-custody.md)
- [v0.6 Definition of Done](docs/definition-of-done.md)
- [v0.7 public API](docs/v0.7-public-api.md)

Project governance:

- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [Changelog](CHANGELOG.md)

---

## Development setup

Clone the repository and create a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Run the full test suite:

```powershell
python -m pytest -q
```

---

## Release status

Current package release:

**v0.7.1 — PyPI Distribution**

v0.7.1 publishes CAGE through PyPI and adds Trusted Publishing support. It does
not change runtime semantics from v0.7.0.

Previous feature release:

**v0.7.0 — Developer Product**

v0.7.0 introduced the developer-facing SDK, facade, local examples, CLI,
portable Warrant inspection, and integration guidance.

Previous core release:

**v0.6.0 — Consequence Custody**

v0.6 established the controlled execution boundary, authoritative
verification, explicit uncertainty, reconciliation, and execution/verification
lineage.

The earlier v0.5 release established the Generic Consequence Core, including
Consequence identity, evaluation Attempts, Decision semantics, replay,
consequence-level idempotency, and proof foundations.

CAGE remains pre-v1.0.

---

## Current product boundary

The current release provides the local developer SDK and generic assurance
model.

CAGE does not yet include a hosted SaaS control plane, provider-specific
production suites, cryptographic Warrant signing, HSM/KMS integration,
post-quantum signing, or enterprise deployment infrastructure.

Those capabilities belong to later stages of the roadmap.

The current focus is keeping the core semantics stable while improving the
developer experience and integration model.

---

## License

CAGE source code is licensed under the
[Apache License 2.0](LICENSE).

For security issues, see [SECURITY.md](SECURITY.md).

For contributions, see [CONTRIBUTING.md](CONTRIBUTING.md).
