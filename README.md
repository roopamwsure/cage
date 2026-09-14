# CAGE

**CAGE — Control Assurance Governance Evaluation**

CAGE is a vendor-neutral consequence-assurance layer for consequential actions taken by AI agents and autonomous systems.

CAGE focuses on one question:

> Should a proposed autonomous action be allowed to become a real-world business consequence, and can we later prove what actually became effective?

CAGE operates at the **business consequence boundary**.

It does not replace agent runtimes, IAM, authorization systems, policy engines, approval systems, guardrails, observability platforms, or cloud security controls.

Those systems can provide normalized assurance inputs to CAGE.

---

## Status

Current release target:

**v0.5 — Generic Consequence Core**

v0.5 establishes the foundational domain model and assurance semantics required to reason about consequential autonomous actions independently of any particular cloud provider, agent framework, IAM platform, or business domain.

---

## Core Idea

Traditional security systems can establish that an authenticated and authorized principal or agent invoked an allowed operation.

CAGE adds a separate assurance layer around the resulting business consequence.

CAGE distinguishes between:

1. what was proposed;
2. what CAGE permitted;
3. what actually became true in the external world;
4. what evidence supports those claims.

The central rule is:

```text
Decision != Effect
```

For example:

```text
ADMITTED does not imply BOUND.
REFUSED does not imply NO_BIND.
```

---

## Core Model

```text
Principal
Agent
Resource
RequestedEffect
        |
        v
      Action
        |
        v
   Consequence
        |
        +---- Attempt 1
        +---- Attempt 2
        +---- Attempt 3
```

A **Consequence** represents one intended business consequence.

An **Attempt** represents one evaluation of that Consequence.

Multiple Attempts may refer to the same Consequence.

---

## Evaluation Flow

CAGE v0.5 supports normalized assurance inputs:

* Evidence
* Standing
* Delegation
* Approval
* Context

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
Deterministic Evaluation Rule
  |
  v
EvaluationOutcome
  |
  v
Decision
  |
  v
DecisionProof
  |
  v
Warrant
```

The supplied evaluation logic is responsible for interpreting domain-specific assurance requirements.

Generic CAGE Core does not become a policy language or IAM system.

---

## Decision States

CAGE defines five canonical Decision states:

* `ADMITTED`
* `HELD`
* `NARROWED`
* `ESCALATED`
* `REFUSED`

A Decision describes what CAGE permitted for a specific Attempt.

`NO_BIND` is not a Decision state.

---

## Effect States

CAGE defines three canonical Effect states:

* `BOUND`
* `NO_BIND`
* `EFFECT_UNKNOWN`

An Effect describes what has been established about the external business consequence.

CAGE must not claim `NO_BIND` merely because:

* execution was not attempted;
* execution returned an error;
* an API timed out;
* a response was lost;
* no confirmation was received.

If external reality cannot be established, the correct state is:

```text
EFFECT_UNKNOWN
```

---

## NARROWED Decisions

A `NARROWED` Decision preserves both:

* the originally requested effect;
* an explicit permitted effect intended to be more constrained.

For example:

```text
Requested:
Global Admin for 480 minutes

Permitted:
Scoped Operator for 30 minutes
```

Determining whether one effect is semantically more constrained than another is domain-specific and belongs to supplied evaluation logic rather than generic CAGE Core.

---

## Safe Replay

Replay means re-evaluating the same Consequence using a new Attempt.

```text
Consequence C1
    |
    +-- Attempt A1
    |      -> ESCALATED
    |
    +-- Attempt A2
           -> ADMITTED
```

Replay preserves the original Consequence and business intent.

Replay does **not** automatically execute the external action again.

---

## Consequence-Level Idempotency

CAGE treats idempotency as business-consequence safety rather than merely HTTP retry handling.

For v0.5:

```text
same idempotency key
+
equivalent business intent
=
same Consequence
```

Reusing the same idempotency key for materially different business intent results in an explicit conflict.

v0.5 consequence equivalence considers:

* action type;
* principal identity;
* resource identity;
* requested effect.

Attempt identity, agent identity, retry number, replay number, and proposed replacement Consequence identity do not independently create a new Consequence.

---

## Warrant Foundation

A CAGE Warrant preserves the available assurance state for a Consequence.

The v0.5 Warrant separates:

```text
DecisionProof
```

from:

```text
EffectProof
```

A valid DecisionProof does not prove that the external consequence became effective.

A Warrant may legitimately exist with a DecisionProof and no EffectProof.

That state is different from an EffectProof containing `EFFECT_UNKNOWN`.

---

## Domain Neutrality

The same Generic Consequence Core supports materially different consequence types.

v0.5 tests include examples such as:

```text
database.delete
access.grant
payment.release
```

There is no database-specific, access-specific, or payment-specific business logic inside production CAGE Core.

Domain-specific parameters are carried through generic `RequestedEffect` data and interpreted by supplied evaluation logic.

---

## Vendor Neutrality

CAGE Core does not depend on:

* AWS
* Azure
* GCP
* MCP
* OpenAI
* Anthropic
* any specific AI model
* any specific agent runtime
* any specific IAM system
* any specific policy engine
* any specific policy language

Provider-specific identity, policy, approval, risk, observability, and security results should be normalized before entering CAGE.

CAGE consumes those results rather than recreating those systems.

---

## Local Operation

CAGE v0.5 has no runtime dependencies outside the Python standard library.

Requirements:

```text
Python >= 3.11
```

Development currently uses:

```text
pytest
```

CAGE Core does not require CAGE Cloud or any hosted CAGE service.

---

## Installation for Development

Clone the repository and create a virtual environment.

On Windows PowerShell:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install CAGE in editable mode with development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run the test suite:

```powershell
python -m pytest -q
```

---

## Current v0.5 Core Modules

```text
action.py
assurance.py
attempt.py
consequence.py
decision.py
effect.py
evaluation.py
idempotency.py
identity.py
replay.py
warrant.py
```

---

## v0.5 Scope

v0.5 includes:

* generic Principal, Agent, and Resource identity contracts;
* generic Action and RequestedEffect;
* stable Consequence identity;
* Attempt identity;
* normalized assurance inputs;
* canonical Decision semantics;
* canonical Effect semantics;
* deterministic evaluation orchestration;
* no-implicit-allow behavior;
* NARROWED permitted-effect semantics;
* safe replay;
* consequence-level idempotency;
* DecisionProof;
* EffectProof;
* minimal Warrant foundation;
* minimal Attempt and Warrant lineage.

---

## Not Included in v0.5

v0.5 does not implement:

* CAGE Cloud;
* SaaS;
* billing;
* REST APIs;
* database persistence;
* AWS, Azure, or GCP adapters;
* MCP integration;
* execution credential custody;
* protected Effect Adapters;
* target-system execution;
* authoritative target-state reconciliation;
* cryptographic Warrant signatures;
* canonical Warrant JSON;
* independent Warrant verification;
* HSM or KMS integration;
* post-quantum cryptography;
* AI risk intelligence;
* enterprise deployment;
* a new IAM system;
* a new policy language;
* full consequence graphs or advanced consequence lineage.

Those capabilities belong to later releases.

---

## Project Principle

When deciding whether functionality belongs inside CAGE Core, ask:

> Does this help CAGE determine, preserve, verify, or prove the status of an intended business consequence?

If not, it probably belongs outside Core.
