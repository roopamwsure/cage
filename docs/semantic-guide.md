# CAGE decision and effect semantics

CAGE evaluates a proposed business action, controls an execution attempt,
and records what an independent observation can establish afterward. The
decision to permit an attempt and evidence of its external effect answer
different questions. This guide describes the states developers see through
the v0.7 facade. Start with the [Quickstart](quickstart.md) for runnable code
and the [integration guide](integration-guide.md) for callback contracts.

## Identity and evaluation

An `Action` names the principal, agent, resource, action type, and requested
effect. A `Consequence` names the intended business outcome. Each evaluation
has its own `Attempt`; repeated evaluations of one Consequence can have
different Attempts. Supply a stable, application-owned `idempotency_key`
when calling `CAGE.evaluate(...)`. Passing `previous=...` re-evaluates the
same Consequence with a new Attempt and preserves its lineage. It does not
invoke an adapter. Reusing a key with a conflicting action or overriding an
existing identity with a conflicting value fails before dispatch.

The application rule consumes normalized evidence, standing, delegations,
approvals, and context and returns an `EvaluationOutcome`. The resulting
`DecisionProof` records the basis of the decision; it is not an observation
of the target system. The five Decision states mean:

| Decision | Meaning at the execution boundary |
| --- | --- |
| `ADMITTED` | The originally requested effect may be attempted. |
| `NARROWED` | Only the explicitly permitted effect may be attempted; the broader request is not substituted. |
| `HELD` | Do not execute under custody yet. |
| `ESCALATED` | Do not execute under custody; further authority or review is needed. |
| `REFUSED` | Do not execute under custody. This does not prove that nothing changed elsewhere. |

## Custody and adapter observation

For `ADMITTED` or `NARROWED`, `CAGE.execute(...)` checks a scoped capability
and invokes an application adapter under custody. The `EvaluationAttempt`
and `ExecutionAttempt` are different records. A single facade instance
reserves dispatch by Consequence to prevent another dispatch through that
instance. This memory is not shared across processes or restored after a
restart; the target integration still needs durable idempotency and
correlation.

An adapter can report `ACKNOWLEDGED`, `REJECTED`, `ERROR`, or `UNKNOWN`.
These are reports about an execution attempt, not verified external effects.
An acknowledgement alone does not establish `BOUND`; a rejection or error
alone does not establish `NO_BIND`. If a callback fails or returns an
unusable result after dispatch, the SDK preserves an `UNKNOWN` recovery
observation so a verifier can inspect the target. See the
[failure and recovery guide](failure-and-recovery.md) for the resulting
exceptions and recovery context.

## Verification and effect

`CAGE.verify(execution, verifier=...)` asks an application verifier to
observe the target using the execution record and its correlation data.
The verifier must supply meaningful evidence appropriate to that target;
CAGE checks record consistency but cannot certify the truth of a provider's
claim. Verification leads to the following Effect states:

| Verification | Effect | Interpretation |
| --- | --- | --- |
| `VERIFIED_BOUND` | `BOUND` | The verifier reports the intended selected effect became effective. |
| `VERIFIED_NO_BIND` | `NO_BIND` | The verifier reports the selected effect did not become effective. |
| `INCONCLUSIVE` | `EFFECT_UNKNOWN` | The available observation cannot establish either result. |

Before verification, do not infer an Effect state from the adapter report.
`ADMITTED` is permission to try, not proof that a target changed. `REFUSED`
blocks a CAGE-managed execution attempt, not proof of `NO_BIND` in all
external systems.

The assurance contains an `EffectProof` and a `Warrant` linked to the
decision and execution history. A decision-only Warrant can have a
`DecisionProof` without an `EffectProof`; it does not imply execution.
Portable JSON Warrants are detached views of this history; see the
[portable Warrant guide](portable-warrants-and-cli.md) for disclosure and
validation limits.

## Reconcile without another execution

When the first verification is inconclusive, call
`CAGE.reconcile(previous_assurance, verifier=...)` to observe again. It
uses the earlier execution and produces a new assurance snapshot whose
Warrant names the preceding Warrant. It does not dispatch the adapter a
second time. The [reconciliation walkthrough](reconciliation-walkthrough.md)
shows one execution followed by a later bound observation.

Recovery after a process restart requires application-owned durable
execution and correlation records. A portable Warrant file alone cannot
restore the facade's dispatch guard or authorize an execution retry. Treat
an unknown outcome as unknown until suitable verification resolves it.
