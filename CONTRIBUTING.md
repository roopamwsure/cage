# Contributing to CAGE

CAGE is a Python assurance library under active development. Start with the
[Quickstart](docs/quickstart.md), [semantic guide](docs/semantic-guide.md),
and [integration guide](docs/integration-guide.md). The
[release review](docs/v0.7-release-readiness.md) records unfinished v0.7
work; an implemented example is not a production integration.

## Before proposing a change

Describe the problem, the intended behavior, and which public contract it
affects in an issue or pull request. For security-sensitive findings, follow
[SECURITY.md](SECURITY.md) instead of disclosing them in an issue. Do not
include real credentials, customer data, or production Warrant files.

Preserve these distinctions when changing the SDK:

- A Decision permits or prevents a managed attempt; it does not establish an Effect.
- Adapter acknowledgement does not establish `BOUND`; rejection does not establish `NO_BIND`.
- Evaluation replay does not dispatch; reconciliation observes without redispatch.
- An unknown outcome remains unknown until suitable target verification resolves it.
- Portable Warrant validation establishes structure, not authenticity or current target state.

Changes to public states, import paths, Warrant format fields, or exception
categories need a compatibility review and migration notes. Use a new portable
format version for incompatible format changes.

## Set up and verify

Use Python 3.11 or newer. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
python -m pytest -q
python examples/sqlite_delete.py
python examples/sqlite_reconcile.py
```

On macOS or Linux, activate with `source .venv/bin/activate`. CI checks
Python 3.11 through 3.14, builds a wheel and source archive, and runs local
examples from an installed wheel. For focused changes, run relevant tests
first, then the full suite. Review `git diff --check` and the final diff
before submitting a pull request; explain what changed, how it was tested,
and any behavior that remains unverified.

The feature branch currently declares package version `0.6.0` while v0.7
is in development. A successful contribution or test run does not authorize
a release, tag, or package publication.
