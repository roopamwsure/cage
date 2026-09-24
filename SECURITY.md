# Security reporting and scope

If you find a vulnerability, please do not publish exploit steps, private
data, credentials, or affected Warrant files in a public issue. Use GitHub's
**Report a vulnerability** option on this repository's Security page if it
is available. If private vulnerability reporting is unavailable, contact
the repository maintainer through an existing private contact method before
sending sensitive details. This project does not currently advertise a
dedicated security email address or a guaranteed response time.

Please include the affected commit or package version, a minimal reproduction
using disposable data, expected and observed behavior, and the security
impact. Redact tokens, business identifiers, customer records, and provider
payloads. Maintainers can follow up privately about verification and fixes.

## Current trust boundaries

- CAGE controls calls made through its facade instance; it does not enforce
  a distributed lock or prevent a caller from bypassing the facade.
- Adapter responses and verifier callbacks are supplied by applications.
  CAGE validates their record links, but cannot independently guarantee the
  truth of a target system's claims.
- A portable Warrant is an inspection record. Its structural validation does
  not establish provenance, authenticity, permission to act, or a current
  external Effect. It is not signed in this release.
- SUMMARY disclosure omits selected parameters and reference arrays, but
  still exposes identifiers, action types, states, and counts. Treat both
  SUMMARY and FULL files as potentially sensitive.
- An `UNKNOWN` execution outcome requires target observation, not a blind
  execution retry. Application-owned durable correlation and idempotency
  remain necessary across process restarts.

For application recovery practices, see the
[failure and recovery guide](docs/failure-and-recovery.md). This document
describes current behavior and a reporting route; it is not a claim of a
completed security audit.
