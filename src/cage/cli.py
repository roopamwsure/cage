"""Local CAGE examples and portable Warrant inspection commands."""

import argparse
from importlib.metadata import version
import sys

from cage.errors import WarrantFormatError, WarrantIOError
from cage.warrants import load_warrant, validate_warrant


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cage", description="Run local examples and inspect portable Warrants."
    )
    parser.add_argument("--version", action="version", version=f"cage {version('cage-assurance')}")
    command = parser.add_subparsers(dest="command", required=True)
    example = command.add_parser("example", help="Run a disposable local example")
    examples = example.add_subparsers(dest="scenario", required=True)
    examples.add_parser("database.delete", help="Delete a record in local SQLite").add_argument(
        "--warrant", metavar="PATH", help="Write a SUMMARY portable Warrant"
    )
    examples.add_parser("access.grant", help="Grant narrowed local access").add_argument(
        "--warrant", metavar="PATH", help="Write a SUMMARY portable Warrant"
    )
    examples.add_parser("payment.release", help="Reconcile a simulated payment").add_argument(
        "--warrant", metavar="PATH", help="Write a SUMMARY portable Warrant"
    )
    warrant = command.add_parser("warrant", help="Read a portable Warrant")
    operation = warrant.add_subparsers(dest="operation", required=True)
    for name in ("inspect", "validate"):
        operation.add_parser(name, help=f"{name.title()} a portable Warrant").add_argument("path")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Return documented CLI exit codes; argparse handles usage errors."""
    args = _parser().parse_args(argv)
    try:
        if args.command == "example":
            if args.scenario == "database.delete":
                from cage._sqlite_example import main as run_example
            elif args.scenario == "access.grant":
                from cage._access_example import main as run_example
            else:
                from cage._payment_example import main as run_example
            run_example(warrant_path=args.warrant)
            return 0
        document = load_warrant(args.path)
        report = validate_warrant(document)
        if args.operation == "inspect":
            data = document.to_dict()
            print(f"Warrant ID: {document.warrant_id}")
            print(f"Consequence ID: {document.consequence_id}")
            print(f"Previous Warrant ID: {document.previous_warrant_id or 'none'}")
            print(f"Decision: {document.decision_state.value}")
            print(f"Effect: {document.effect_state.value if document.effect_state else 'none'}")
            print(f"Execution attempt ID: {document.execution_attempt_id or 'none'}")
            print(f"Adapter: {data['adapter_result']['state'] if data['adapter_result'] else 'none'}")
            print(f"Verification: {data['verification']['state'] if data['verification'] else 'none'}")
            print(f"Disclosure: {document.disclosure.value}")
            print(f"Observation origin: {document.observation_origin or 'none'}")
        else:
            print("Structural validity: valid")
            print(f"Disclosure: {document.disclosure.value}")
            omitted = document.to_dict()["disclosure"]["omitted_fields"]
            print("Omitted fields: " + (", ".join(omitted) if omitted else "none"))

        for issue in report.issues:
            print(f"{issue.severity.title()} ({issue.code}) at {issue.path}: {issue.message}")
        return 0
    except WarrantFormatError:
        print("Invalid portable Warrant record.", file=sys.stderr)
        return 2
    except WarrantIOError:
        print("Could not read or write portable Warrant file.", file=sys.stderr)
        return 1
    except Exception:
        print("Could not complete Warrant command.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
