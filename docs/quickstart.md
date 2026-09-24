# CAGE v0.7 local Quickstart

This example runs entirely on your machine. It creates a temporary SQLite
database, inserts one record, evaluates a delete request, executes the admitted
request once, and checks the database independently before producing an Effect
and Warrant. The temporary database is removed when the script exits.

## Run from a source checkout

Use Python 3.11 or newer. In PowerShell, from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python examples/sqlite_delete.py
```

If you already have this repository installed in an active virtual environment,
run only the final command. This example does not require a network service or
credentials. It uses Python's standard-library `sqlite3` module.

The output has these states; the Warrant ID varies per run:

```text
Decision: admitted
Adapter: acknowledged
Verification: verified_bound
Effect: bound
Warrant ID: warrant_<generated identifier>
```

The evaluation rule admits only the local operator's delete request for record
1 in the example resource. The capability is scoped to the evaluated
Consequence, action type, and resource. It is a local teaching fixture; a real
application must obtain capabilities and trusted identity facts through its own
authority system.

`ACKNOWLEDGED` records what the adapter reported after dispatch. A separate
database connection checks whether the row still exists. Only that verification
produces the `BOUND` Effect and its Warrant. The example makes no claim that a
database acknowledgement alone establishes the external effect.

For a first observation that is inconclusive and a later observation without
another delete, see the [reconciliation walkthrough](reconciliation-walkthrough.md).

## Inspect an exported portable Warrant

After your application has exported a Warrant with `dump_warrant()` from
`cage.warrants`, inspect its lifecycle metadata and check its file structure:

```powershell
cage warrant inspect .\assurance-warrant.json
cage warrant validate .\assurance-warrant.json
```

`inspect` shows lifecycle IDs and states without printing business payloads or
reference contents. `validate` reports structural consistency, omitted fields,
and unresolved predecessor links. A valid file is an inspection record, not
proof that its claims are authentic or that an external effect still holds.
