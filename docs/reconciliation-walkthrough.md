# Reconciliation Walkthrough

This example shows how CAGE can move from an uncertain Effect to a later
verified Effect without executing the external operation again.

Run the local SQLite example from a source checkout:

```powershell
python examples/sqlite_reconcile.py
```

A typical run produces:

```text
First verification: inconclusive
First effect: effect_unknown
Later verification: verified_bound
Later effect: bound
Adapter dispatches: 1
Previous warrant ID: warrant_<generated identifier>
Later warrant predecessor: warrant_<same identifier>
```

The generated Warrant ID changes between runs. The predecessor ID on the later
Warrant matches the first Warrant.

---

## First observation

The example creates a temporary SQLite database and inserts one record.

CAGE evaluates a delete request and executes that operation once.

The adapter reports:

```text
ACKNOWLEDGED
```

The first verifier does not yet have enough authoritative evidence to establish
the external outcome, so it returns:

```text
INCONCLUSIVE
```

CAGE therefore records:

```text
Effect = EFFECT_UNKNOWN
```

This is a complete assurance snapshot.

It means the available evidence could not establish whether the intended
Consequence became effective.

It does not mean the delete failed.

It also does not mean the delete succeeded.

---

## Later reconciliation

Later, a verifier reads the same database through a separate connection.

The record is now observed to be absent, so the verifier returns:

```text
VERIFIED_BOUND
```

CAGE maps that result to:

```text
Effect = BOUND
```

and creates a new:

```text
EffectProof
Warrant
```

The new Warrant points back to the earlier one through:

```text
previous_warrant_id
```

The first Warrant is not modified.

---

## One execution, two assurance snapshots

The important part of the example is the adapter count:

```text
Adapter dispatches: 1
```

The lifecycle is:

```text
one external execution
        |
        v
AdapterExecutionResult
        |
        v
Verification #1 = INCONCLUSIVE
        |
        v
Effect #1 = EFFECT_UNKNOWN
        |
        v
Warrant #1
        |
        v
later reconciliation
        |
        v
Verification #2 = VERIFIED_BOUND
        |
        v
Effect #2 = BOUND
        |
        v
Warrant #2
        previous_warrant_id = Warrant #1
```

The second assurance state comes from new evidence about the existing
execution.

It does not come from another execution.

```text
Reconciliation != Re-execution
```

---

## What this example demonstrates

Reconciliation is useful when execution has already occurred but the first
verification cannot establish the outcome.

CAGE preserves the uncertain state rather than forcing a premature conclusion.

When better evidence becomes available later, `CAGE.reconcile()` can produce a
new assurance snapshot while preserving the original execution and earlier
Warrant history.

The SQLite verifier used here is only a local example.

A production integration must use evidence that is authoritative enough for
the external system and business operation being verified.

The temporary database is removed when the example exits.