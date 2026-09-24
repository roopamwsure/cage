# Portable Warrants and the `cage` CLI

Portable Warrant v1 is a versioned JSON inspection view of a CAGE evaluation
or completed assurance. It is detached data: loading it does not recreate an
`ExecutionResult`, restore the facade's in-memory dispatch history, grant
authority, or contact the target. The exact field and state contract is in
the [v0.7 public API](v0.7-public-api.md), sections 18–21.

## Create and inspect a local record

From a source checkout with an active virtual environment, install the
current branch once with `python -m pip install -e .` as described in the
[Quickstart](quickstart.md). To test a locally built wheel in a clean
environment, install its path with `python -m pip install --no-deps PATH_TO_WHEEL`.
The v0.7 package has not been published to PyPI.

In PowerShell, use a new filename for each example because export refuses an
existing file by default:

```powershell
cage --version
cage --help
cage example database.delete --warrant .\delete-warrant.json
cage warrant inspect .\delete-warrant.json
cage warrant validate .\delete-warrant.json
```

You can replace `database.delete` with `access.grant` or `payment.release`.
Each command runs a disposable local fixture, with no account, credentials,
or live business system. The exported file records the **final** assurance
snapshot at SUMMARY disclosure. `payment.release` prints an inconclusive
first observation and a later bound observation with one adapter dispatch.
Its exported final Warrant names the earlier Warrant as a predecessor but
does not contain that earlier snapshot.

`inspect` prints identifiers, Decision and Effect states, adapter and
verification states, disclosure, origin, and unresolved lineage warnings.
It does not print action parameters or reference values by default, even
when the file was exported as FULL. Identifiers and action types may
themselves reveal information if an application assigns sensitive values.
`validate` reports structural validity, disclosed omissions, and warnings;
it does not verify that a target system changed, remains changed, or that
the record came from a trusted signer.

## Export from an application

Import the functions from `cage.warrants`. Given an `EvaluationResult` or
`AssuranceResult` returned by the public facade:

```python
from cage.warrants import WarrantDisclosure, dump_warrant, export_warrant

document = export_warrant(assurance)  # SUMMARY by default
dump_warrant(document, "assurance-warrant.json")

# Explicit FULL disclosure can contain business data and reference values.
full = export_warrant(assurance, disclosure=WarrantDisclosure.FULL)
```

Here `assurance` is an existing `AssuranceResult`, for example the result of
`cage.verify(...)` or `cage.reconcile(...)`. You may instead export an
`EvaluationResult` for a decision-only record, or an internally consistent
core `Warrant`. An `ExecutionResult` is not an export source. Export never
dispatches an adapter or invokes a verifier.

`dump_warrant()` validates and serializes before touching its destination,
uses UTF-8, does not create missing parent directories, and refuses an
existing path unless `overwrite=True`. Replacing a file explicitly does not
imply that the new record supersedes it in the target system. Preserve
historical snapshots when investigating uncertain effects.

## Read, validate, and share carefully

```python
from cage.warrants import load_warrant, parse_warrant, validate_warrant

detached = load_warrant("assurance-warrant.json")
print(detached.warrant_id, detached.decision_state, detached.effect_state)
report = validate_warrant(detached)
for issue in report.issues:
    print(issue.severity, issue.code, issue.path, issue.message)

# For data already in memory, parse_warrant(json_text_or_utf8_bytes) raises
# WarrantFormatError on malformed content.
```

`load_warrant()` raises for invalid data. `validate_warrant()` returns a
`WarrantValidationReport`; malformed content is reported through error
issues, while an unsupported input *argument type* raises `CAGETypeError`.
Valid records can also carry warnings. In SUMMARY, hidden verification
reference contents cannot be compared; predecessor IDs name records outside
the file and are reported as unresolved. A warning does not make a
structurally consistent file invalid.

| Disclosure | Parameters and subject/resource IDs | Proof reference arrays | What is still visible |
| --- | --- | --- | --- |
| SUMMARY (default) | Specified fields become null | Specified arrays become null, with paths listed in `disclosure.omitted_fields` | IDs, action type, states, origin, reference counts, predecessor IDs |
| FULL | Supported Warrant values preserved | Arrays retain order and duplicates; omitted-fields list empty | All supported values, including potentially sensitive business data |

SUMMARY is disclosure, not anonymization. FULL does not include adapter
credentials or assurance-input payloads that were never in the native
Warrant. Protect either file in proportion to the identifiers and values it
contains. A parsed document is not a proof of authenticity or a safe way to
resume an interrupted operation.

## Format compatibility and migration

Portable v1 requires `format="cage.warrant"` and `format_version="1"`.
The native Warrant's `schema_version` is separate metadata. The reader
rejects duplicate JSON keys, invalid UTF-8, nonfinite numbers, unknown or
missing fields, unsupported versions, inconsistent links and states, and
undisclosed omissions. Input and serialized output are limited to 8 MiB
of UTF-8 JSON and nesting depth 64. `PortableWarrant.to_dict()` returns
a fresh JSON-compatible copy; `to_json()` is for display or storage, not
cryptographic canonicalization.

v0.6 core Warrants are runtime objects, not portable v1 files. The v0.7
SDK adds export and readback without changing a v0.6 application's core
imports. A bare legacy core Warrant that has no separate origin field is
stored with `adapter_result.origin="unspecified"`, unless the reserved SDK
recovery marker establishes recovery provenance. The detached object's
`observation_origin` property is `None` for that unspecified case.

Format v1 is closed: adding or reinterpreting fields requires a new
format version and explicit migration guidance. A v1 reader rejects a
future format version rather than guessing its meaning. No signature,
hashing profile, key identity, or cryptographic authenticity check is
provided in v0.7.

## CLI exit codes

| Code | Meaning |
| --- | --- |
| `0` | Command completed; for validation, the record is structurally valid |
| `1` | File access or example/runtime failure |
| `2` | Invalid arguments or invalid/unsupported portable record |

An example may finish successfully while displaying `EFFECT_UNKNOWN`;
exit `0` alone never means `BOUND`. CLI errors are summarized on stderr
without provider tracebacks. For SDK error classes and observation-only
recovery, see the [failure and recovery guide](failure-and-recovery.md).
