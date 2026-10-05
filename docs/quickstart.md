# CAGE v0.7 Quickstart

This example runs entirely on your machine.

It creates a temporary SQLite database, inserts one record, evaluates a delete
request, executes the admitted operation once, verifies the database state
through a separate read, and then produces an Effect and Warrant.

The temporary database is removed when the example exits.

---

## Install

CAGE requires Python 3.11 or newer.

Install the published package:

```powershell
python -m pip install cage-assurance
```

Confirm the CLI:

```powershell
cage --version
```

If you are working from a source checkout instead, create a virtual environment
from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

The local examples do not require cloud credentials or an external service.

---

## Run the database example

From the repository:

```powershell
python examples/sqlite_delete.py
```

Or use the CLI from any directory where CAGE is installed:

```powershell
cage example database.delete
```

To export the final Warrant:

```powershell
cage example database.delete --warrant .\delete-warrant.json
```

The exported file uses `SUMMARY` disclosure by default.

CAGE refuses to overwrite an existing file unless replacement is explicitly
requested through the Warrant API.

A typical result looks like:

```text
Decision: admitted
Adapter: acknowledged
Verification: verified_bound
Effect: bound
Warrant ID: warrant_<generated identifier>
```

The generated identifiers vary between runs.

---

## What happened?

The example follows this lifecycle:

```text
delete request
    |
    v
evaluation
    |
    v
ADMITTED
    |
    v
ExecutionAttempt
    |
    v
SQLite delete
    |
    v
ACKNOWLEDGED
    |
    v
independent database read
    |
    v
VERIFIED_BOUND
    |
    v
BOUND
    |
    v
Warrant
```

The important distinction is:

```text
ACKNOWLEDGED != BOUND
```

`ACKNOWLEDGED` records what the adapter observed after dispatch.

A separate database connection checks whether the row is actually gone.

That verification is what supports the `BOUND` Effect.

The example therefore does not treat a database acknowledgement by itself as
proof of the external outcome.

---

## Try a NARROWED Decision

Run:

```powershell
cage example access.grant --warrant .\access-warrant.json
cage warrant inspect .\access-warrant.json
```

The example requests administrator access but permits only reader access.

At execution time, only the permitted reader grant reaches the adapter.

The resulting `BOUND` Effect refers to that reader grant, not to the broader
administrator request.

---

## Try an uncertain outcome

Run:

```powershell
cage example payment.release --warrant .\payment-warrant.json
cage warrant inspect .\payment-warrant.json
```

This example demonstrates an execution whose acknowledgement is unavailable.

The first verification is inconclusive:

```text
INCONCLUSIVE
    ->
EFFECT_UNKNOWN
```

Later, the same simulated ledger entry is observed again and the payment is
verified as `BOUND`.

The operation is not dispatched a second time.

The later Warrant links to the earlier uncertain Warrant through
`previous_warrant_id`.

The exported file contains the final Warrant only; it does not embed the earlier
snapshot.

---

## Inspect a portable Warrant

Use:

```powershell
cage warrant inspect .\delete-warrant.json
```

to view the main lifecycle identifiers and states.

Then validate the portable record:

```powershell
cage warrant validate .\delete-warrant.json
```

`inspect` avoids printing business payloads and reference contents by default.

`validate` checks the portable Warrant's structure and internal consistency.

A valid portable Warrant is still a detached assurance record.

It does not by itself prove that:

- its external claims are authentic;
- the target is still in the same state; or
- the record came from a trusted signer.

---

## Where to go next

For the underlying semantics, see the
[Decision and Effect guide](semantic-guide.md).

For adapters and verifiers, see the
[Integration guide](integration-guide.md).

For uncertain outcomes and callback failures, see
[Failure and recovery](failure-and-recovery.md).

For a step-by-step example of later verification without another execution, see
the [Reconciliation walkthrough](reconciliation-walkthrough.md).