from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import init_workspace, run_demo, run_resilient_demo, run_live_proposal_demo
from .proxy import run_stdio_proxy
from .receipt import write_trust_receipt
from .verifier import verify_wal


def _print_demo(summary: dict[str, object]) -> None:
    checks = summary["checks"]
    assert isinstance(checks, dict)
    print(f"DRF + OMTIR MCP Flight Recorder v0.1")
    print(f"Status: {summary['Status']}")
    print(f"delete_index             -> {'DENY' if checks['delete_index_DENY'] else 'FAIL'}")
    print(f"search_logs              -> {'ALLOW' if checks['search_logs_ALLOW'] else 'FAIL'}")
    print(
        "unsupported CONFIRMED    -> "
        f"{'REJECTED_HYPOTHESIS' if checks['unsupported_CONFIRMED_REJECTED_HYPOTHESIS'] else 'FAIL'}"
    )
    print(f"evidence-linked claim    -> {'CONFIRMED' if checks['evidence_linked_claim_CONFIRMED'] else 'FAIL'}")
    print(f"restart_service          -> {'REQUEST_REVIEW' if checks['restart_service_REQUEST_REVIEW'] else 'FAIL'}")
    print(f"WAL records              -> {5 if checks['wal_records'] else 'FAIL'}")
    print(f"Verifier                 -> {'PASS' if checks['verifier_PASS'] else 'FAIL'}")
    print(f"Trust Receipt            -> {'generated' if checks['trust_receipt_generated'] else 'FAIL'}")
    print(f"WAL: {summary['wal_path']}")
    print(f"Trust Receipt: {summary['trust_receipt_path']}")


def _print_resilient_demo(summary: dict[str, object]) -> None:
    checks = summary["checks"]
    assert isinstance(checks, dict)
    print("DRF + OMTIR Resilient Agent Trial v0.1")
    print(f"Status: {summary['Status']}")
    print(f"provider_route              -> {summary['provider_route']}")
    print(f"model                       -> {summary['model']}")
    print(f"aws_bedrock                 -> {summary['aws_bedrock']}")
    print(f"gateway_failure             -> {summary['gateway_failure']}")
    print(f"rate_limit_rule             -> {summary['rate_limit_rule']}")
    print(f"first_request               -> {summary['first_request']}")
    print(f"second_request              -> {summary['second_request']}")
    print(f"unsafe_action               -> {'DENY' if checks['unsafe_action_DENY'] else 'FAIL'}")
    print(f"read_only_tool              -> {'ALLOW' if checks['read_only_tool_ALLOW'] else 'FAIL'}")
    print(f"bad_tool_result             -> {'QUARANTINED' if checks['bad_tool_result_QUARANTINED'] else 'FAIL'}")
    print(
        "unsupported_claim           -> "
        f"{'REJECTED_HYPOTHESIS' if checks['unsupported_claim_REJECTED_HYPOTHESIS'] else 'FAIL'}"
    )
    print(f"evidence_linked_claim       -> {'CONFIRMED' if checks['evidence_linked_claim_CONFIRMED'] else 'FAIL'}")
    print(f"risky_remediation           -> {'REQUEST_REVIEW' if checks['risky_remediation_REQUEST_REVIEW'] else 'FAIL'}")
    print(f"authority_trace             -> {'recorded' if checks['authority_trace_recorded'] else 'FAIL'}")
    print(f"review_queue                -> {'generated' if checks['review_queue_generated'] else 'FAIL'}")
    print(f"WAL records                 -> {summary['wal_records'] if checks['wal_records'] else 'FAIL'}")
    print(f"verifier                    -> {summary['verifier_status'] if checks['verifier_PASS'] else 'FAIL'}")
    print(f"trust_receipt               -> {'generated' if checks['trust_receipt_generated'] else 'FAIL'}")
    print(f"WAL: {summary['wal_path']}")
    print(f"Review Queue: {summary['review_queue_path']}")
    print(f"Trust Receipt: {summary['trust_receipt_path']}")


def _print_live_proposal_demo(summary: dict[str, object]) -> None:
    print("DRF + OMTIR Live Proposal Trial v0.2")
    print(f"Status: {summary['Status']}")
    if summary["Status"] != "PASS":
        print(f"reason                      -> {summary.get('reason')}")
        if "missing" in summary:
            print(f"missing                     -> {summary['missing']}")
        if "error" in summary:
            print(f"error                       -> {summary['error']}")
        return
    print(f"provider_route              -> {summary['provider_route']}")
    print(f"model                       -> {summary['model']}")
    print(f"agent_proposal_source       -> {summary['agent_proposal_source']}")
    print(f"policy_evaluation           -> {summary['policy_evaluation']}")
    print(f"raw_model_output_sha256     -> {summary['raw_model_output_sha256']}")
    print(f"parsed_action               -> {summary['parsed_action']}")
    print(f"drf_decision                -> {summary['drf_decision']}")
    print(f"tool_execution              -> {summary['tool_execution']}")
    print(f"tool_execution_boundary     -> {summary['tool_execution_boundary']}")
    print(f"claim_status                -> {summary['claim_status']}")
    print(f"WAL records                 -> {summary['wal_records']}")
    print(f"verifier                    -> {summary['verifier_status']}")
    print(f"trust_receipt               -> generated")
    print(f"WAL: {summary['wal_path']}")
    print(f"Verifier Report: {summary['verifier_report_path']}")
    if summary.get("review_queue_path"):
        print(f"Review Queue: {summary['review_queue_path']}")
    print(f"Trust Receipt: {summary['trust_receipt_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="drf-omtir")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init")
    init_parser.add_argument("--root", default=".")
    init_parser.add_argument("--force", action="store_true")

    demo_parser = subparsers.add_parser("demo")
    demo_parser.add_argument("--root", default=".")
    demo_parser.add_argument("--policy")

    resilient_parser = subparsers.add_parser("resilient-demo")
    resilient_parser.add_argument("--root", default=".")
    resilient_parser.add_argument("--provider-route", default="TRUEFOUNDRY_GATEWAY")
    resilient_parser.add_argument("--model", default="GEMINI_FLASH_LITE")

    live_parser = subparsers.add_parser("live-proposal-demo")
    live_parser.add_argument("--root", default=".")

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("wal")
    verify_parser.add_argument("--root", default=".")

    receipt_parser = subparsers.add_parser("receipt")
    receipt_parser.add_argument("wal")
    receipt_parser.add_argument("--root", default=".")
    receipt_parser.add_argument("--output")

    wrap_parser = subparsers.add_parser("wrap")
    wrap_parser.add_argument("--root", default=".")
    wrap_parser.add_argument("--policy", required=True)
    wrap_parser.add_argument("--wal")
    wrap_parser.add_argument("server_command", nargs=argparse.REMAINDER)

    args = parser.parse_args(argv)

    if args.command == "init":
        print(json.dumps(init_workspace(args.root, force=args.force), indent=2, sort_keys=True))
        return 0

    if args.command == "demo":
        summary = run_demo(args.root, args.policy)
        _print_demo(summary)
        return 0 if summary["Status"] == "PASS" else 1

    if args.command == "resilient-demo":
        summary = run_resilient_demo(args.root, provider_route=args.provider_route, model=args.model)
        _print_resilient_demo(summary)
        return 0 if summary["Status"] == "PASS" else 1

    if args.command == "live-proposal-demo":
        summary = run_live_proposal_demo(args.root)
        _print_live_proposal_demo(summary)
        return 0 if summary["Status"] == "PASS" else 1

    if args.command == "verify":
        report = verify_wal(args.wal, root=args.root)
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
        return 0 if report.status == "PASS" else 1

    if args.command == "receipt":
        wal_path = Path(args.wal)
        output = args.output or str(Path(args.root) / "receipts" / f"{wal_path.stem}-trust-receipt.md")
        write_trust_receipt(wal_path, output, root=args.root)
        print(f"Trust Receipt: {output}")
        return 0

    if args.command == "wrap":
        command = list(args.server_command)
        if command and command[0] == "--":
            command = command[1:]
        if not command:
            parser.error("wrap requires a server command after --")
        wal_path = args.wal or PolicyWalPath.default(args.policy)
        return run_stdio_proxy(root=args.root, policy_path=args.policy, wal_path=wal_path, command=command)

    parser.error("unknown command")
    return 2


class PolicyWalPath:
    @staticmethod
    def default(policy_path: str) -> str:
        policy_root = Path(policy_path).resolve().parent
        return str(policy_root / "wal" / "proxy.jsonl")


if __name__ == "__main__":
    raise SystemExit(main())
