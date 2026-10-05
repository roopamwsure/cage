# Portable Warrants and the `cage` CLI

Portable Warrant v1 is a versioned JSON representation of a CAGE Decision or
completed assurance state.

It is designed for inspection, storage, exchange, and tooling.

A portable Warrant is detached data. Loading one does not:

- recreate an `ExecutionResult`;
- restore the facade's in-memory dispatch history;
- recreate an `ExecutionCapability`;
- authorize execution; or
- contact the external target.

For the exact field and state contract, see sections 18–21 of the
[v0.7 Public API](v0.7-public-api.md).

---

## Create and inspect a local Warrant

Install the published package:

```powershell
python -m pip install cage-assurance
```

Confirm the CLI:

```powershell
cage --version
cage --help
```

Run an example and export its final Warrant:

```powershell
cage example database.delete --warrant .\delete-warrant.json
```

Then inspect and validate it:

```powershell
cage warrant inspect .\delete-warrant.json
cage warrant validate .\delete-warrant.json
```

You can also use:

```text
access.grant
payment.release
```

The examples use local disposable fixtures. They do not require cloud
credentials, external accounts, or a live business system.

Use a new output filename for each run unless you explicitly intend to replace
an existing file.

By default, exported Warrants use `SUMMARY` disclosure.

The `payment.release` example demonstrates an inconclusive first observation
followed by later reconciliation to `BOUND`, while keeping a single external
dispatch.

Its final exported Warrant references the earlier Warrant through
`previous_warrant_id`. The earlier snapshot is not embedded inside the later
file.

---

## Inspecting a Warrant

`cage warrant inspect PATH` displays the main assurance metadata, including:

- identifiers;
- Decision state;
- Effect state;
- adapter state;
- verification state;
- disclosure mode;
- observation origin; and
- lineage warnings.

The command does not print action parameters or reference values by default,
even when the file was exported using `FULL` disclosure.

It also escapes control characters in displayed identifiers.

That does not make the output anonymous. Identifiers and action types can still
be sensitive if an application places business information inside them.

---

## Validating a Warrant

Use:

```powershell
cage warrant validate .\delete-warrant.json
```

Validation checks whether the portable record is structurally and semantically
consistent with the v1 format.

It can detect problems such as:

- missing or unknown fields;
- invalid state combinations;
- broken lineage references within the record;
- invalid disclosure metadata;
- unsupported format versions; and
- malformed field values.

Validation does **not** establish that:

- the external system actually changed;
- the external state is still current;
- the verifier's external claim was truthful;
- the file came from a trusted party; or
- the file has cryptographic integrity.

In other words:

```text
valid portable Warrant
!=
verified external truth
```

and:

```text
valid portable Warrant
!=
authenticated Warrant
```

Cryptographic authenticity is outside the v0.7 portable format.

---

## Exporting from an application

Import the Warrant helpers from `cage.warrants`:

```python
from cage.warrants import (
    WarrantDisclosure,
    dump_warrant,
    export_warrant,
)
```

Given an `AssuranceResult` returned by `verify()` or `reconcile()`:

```python
document = export_warrant(assurance)
dump_warrant(document, "assurance-warrant.json")
```

`SUMMARY` is the default disclosure mode.

To export the supported full record:

```python
full = export_warrant(
    assurance,
    disclosure=WarrantDisclosure.FULL,
)
```

`FULL` can contain business-sensitive values and references.

`export_warrant()` can also export:

- an `EvaluationResult`, producing a Decision-only record; or
- an internally consistent Core `Warrant`.

An `ExecutionResult` is not a valid export source.

Exporting never calls an adapter or verifier.

---

## Writing files safely

`dump_warrant()` validates and serializes the portable record before writing
the destination.

It:

- writes UTF-8;
- does not create missing parent directories automatically; and
- refuses to replace an existing file unless `overwrite=True` is supplied.

For example:

```python
dump_warrant(
    document,
    "assurance-warrant.json",
    overwrite=True,
)
```

Replacing a local JSON file does not mean the new assurance record supersedes
the old one in the external system.

When investigating uncertain outcomes, preserve earlier snapshots whenever
their history matters.

---

## Reading a portable Warrant

Use:

```python
from cage.warrants import (
    load_warrant,
    parse_warrant,
    validate_warrant,
)
```

For a file:

```python
detached = load_warrant("assurance-warrant.json")

print(
    detached.warrant_id,
    detached.decision_state,
    detached.effect_state,
)
```

For JSON already held in memory:

```python
detached = parse_warrant(json_text_or_utf8_bytes)
```

Malformed portable data raises `WarrantFormatError`.

An unsupported format version raises
`UnsupportedWarrantVersionError`.

File access problems are reported through `WarrantIOError`.

---

## Validation reports

`validate_warrant()` returns a `WarrantValidationReport`.

For example:

```python
report = validate_warrant(detached)

for issue in report.issues:
    print(
        issue.severity,
        issue.code,
        issue.path,
        issue.message,
    )
```

Malformed record content is represented through validation issues.

An invalid API argument type is different and raises `CAGETypeError`.

A record may be structurally valid and still contain warnings.

For example, a `SUMMARY` Warrant may intentionally omit verification reference
contents, so those values cannot be compared.

Likewise, `previous_warrant_id` can refer to a Warrant that is not contained in
the current file.

That unresolved predecessor reference is not automatically a validation
failure.

---

## SUMMARY and FULL disclosure

Portable Warrant v1 supports two disclosure modes.

| Disclosure | Parameters and subject/resource IDs | Proof reference arrays | Still visible |
| --- | --- | --- | --- |
| `SUMMARY` | Selected fields become `null` | Selected arrays become `null`; their paths appear in `disclosure.omitted_fields` | IDs, action type, states, origin, reference counts, predecessor IDs |
| `FULL` | Supported Warrant values are preserved | Arrays retain their values, order, and duplicates | All supported portable values, including potentially sensitive business data |

`SUMMARY` reduces disclosure.

It is not anonymization.

A SUMMARY Warrant can still expose information through identifiers, action
types, states, counts, timestamps or lineage values, depending on the record.

`FULL` preserves more of the native Warrant data supported by portable v1.

It does not add credentials, assurance-input payloads, or other data that was
never present in the native Warrant.

Both formats should be protected according to the sensitivity of the
information they contain.

---

## What a portable Warrant does not contain

A portable Warrant is an assurance artifact, not an execution token.

It does not recreate:

```text
ExecutionCapability
live adapter state
live verifier state
facade dispatch reservations
external credentials
restart authorization
```

Loading a Warrant therefore does not make it safe to resume an interrupted
operation.

If execution may already have occurred, determine the outcome through durable
application correlation and target-system evidence.

---

## Format compatibility

Portable Warrant v1 uses:

```text
format = "cage.warrant"
format_version = "1"
```

The native Warrant's `schema_version` is separate metadata.

The v1 reader rejects:

- duplicate JSON keys;
- invalid UTF-8;
- non-finite numbers;
- missing fields;
- unknown fields;
- unsupported format versions;
- inconsistent lineage or state combinations; and
- disclosure inconsistencies.

Input and serialized output are limited to:

```text
8 MiB UTF-8 JSON
nesting depth 64
```

`PortableWarrant.to_dict()` returns a fresh JSON-compatible representation.

`to_json()` provides JSON for display or storage.

It is not a cryptographic canonicalization format.

---

## Relationship to v0.6 Warrants

v0.6 Core Warrants are runtime objects.

Portable Warrant v1 was added in the v0.7 developer SDK as a detached JSON
representation.

This does not change the existing v0.6 Core object model or imports.

A legacy Core Warrant without a separate observation-origin field is exported
with:

```text
adapter_result.origin = "unspecified"
```

unless the reserved SDK recovery marker establishes `SDK_RECOVERY`
provenance.

For an unspecified origin, the detached object's `observation_origin` property
is `None`.

---

## Format evolution

Portable Warrant v1 is a closed format.

Existing v1 fields should not be silently reinterpreted.

If a future release needs incompatible fields or semantics, it should use a new
format version together with explicit migration guidance.

A v1 reader rejects a future unsupported version instead of guessing how to
interpret it.

v0.7 does not provide:

- Warrant signatures;
- hashing profiles;
- signer identity;
- trust-chain validation; or
- cryptographic authenticity checking.

Those belong to later cryptographic Warrant work.

---

## CLI exit codes

The CLI uses these exit codes:

| Code | Meaning |
| --- | --- |
| `0` | Command completed successfully; for validation, the portable record is structurally valid |
| `1` | File access, example, or runtime failure |
| `2` | Invalid command arguments or an invalid/unsupported portable record |

An example can exit with `0` while its Effect is:

```text
EFFECT_UNKNOWN
```

Therefore:

```text
CLI exit 0 != BOUND
```

A successful CLI command means the command completed according to its own
contract.

It does not strengthen the assurance represented by the Warrant.

CLI errors are summarized on stderr without exposing provider tracebacks or
business payloads by default.

For SDK recovery behavior, see
[Failure and recovery](failure-and-recovery.md).