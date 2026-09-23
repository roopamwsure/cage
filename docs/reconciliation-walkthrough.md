# Reconciliation walkthrough

Run the local SQLite example from an installed source checkout:

```powershell
python examples/sqlite_reconcile.py
```

The output has these states. The two Warrant ID lines contain the same
generated value:

```text
First verification: inconclusive
First effect: effect_unknown
Later verification: verified_bound
Later effect: bound
Adapter dispatches: 1
Previous warrant ID: warrant_<generated identifier>
Later warrant predecessor: warrant_<same identifier>
```

The example creates a temporary SQLite database and record, evaluates a
specific delete request, and executes it once. The adapter acknowledges the
attempt. The first verifier has no authoritative observation and returns
`INCONCLUSIVE`; its Effect is therefore `EFFECT_UNKNOWN`. That is a completed
historical assurance record, not proof that the delete failed or succeeded.

The later verifier reads the database through a separate connection. It finds
the record absent and returns `VERIFIED_BOUND`. `CAGE.reconcile()` creates a
new Effect, EffectProof, and Warrant linked to the first assurance Warrant. The
first record remains unchanged; the adapter is never called again. A real
integration must use a sufficiently authoritative observation source to make
the same claim. The temporary database is removed when the script exits.
