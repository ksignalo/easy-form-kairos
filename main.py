"""
Entry point for Candidate Intake Automation.

Default mode:
    python main.py
    Starts lightweight web UI at http://127.0.0.1:8000

CLI modes are still available:
    python main.py paste
    python main.py upload path/to/resume.pdf
    python main.py serve --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.extractors import orchestrator
from src.extractors.types import ParseStatus
from src.input_handler import InputError, acquire_from_file, acquire_from_paste
from src.logger import RunLogger
from src.submitter import SubmitResult, submit
from src.web_app import run_server


def _run_paste(logger: RunLogger) -> int:
    print("Paste candidate details below. Press Enter twice when done:")
    lines: list[str] = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    raw_text = "\n".join(lines)

    try:
        text = acquire_from_paste(raw_text)
    except InputError as exc:
        print(f"[INPUT ERROR] {exc}", file=sys.stderr)
        return 1

    return _extract_and_submit(text, resume_path=None, logger=logger)


def _run_upload(file_path: str | None, logger: RunLogger) -> int:
    if not file_path:
        print("No file path provided.", file=sys.stderr)
        return 1

    try:
        text, resolved = acquire_from_file(file_path, logger)
    except InputError as exc:
        print(f"[INPUT ERROR] {exc}", file=sys.stderr)
        return 1

    return _extract_and_submit(text, resume_path=resolved, logger=logger)


def _extract_and_submit(
    raw_text: str,
    resume_path: Path | None,
    logger: RunLogger,
) -> int:
    # --- Extraction ---
    parse_result = orchestrator.run(raw_text, logger)

    if parse_result.status != ParseStatus.VALID:
        print("\n[EXTRACTION FAILED] Could not extract required fields.", file=sys.stderr)
        for err in parse_result.errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nPlease correct the input or fill missing fields manually.",
            file=sys.stderr,
        )
        return 1

    candidate = parse_result.candidate
    provider = parse_result.provider
    print(f"\n[OK] Extracted via '{provider}':")
    print(f"     Name:  {candidate.name}")
    print(f"     Phone: {candidate.phoneNumber}")
    print(f"     Email: {candidate.email}")

    # --- Submission ---
    result: SubmitResult = submit(candidate, logger, resume_path=resume_path)

    if result.success:
        print(f"\n[SUCCESS] {result.message}")
        return 0
    else:
        print(f"\n[FAILED] {result.message}", file=sys.stderr)
        return 1


def main() -> None:
    # No args: start web UI directly for simple day-to-day usage.
    if len(sys.argv) == 1:
        run_server()
        return

    parser = argparse.ArgumentParser(
        description="Candidate Intake Automation — add candidates to the portal."
    )
    subparsers = parser.add_subparsers(dest="mode", required=True)

    serve_parser = subparsers.add_parser("serve", help="Start web UI server.")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8000)

    subparsers.add_parser("paste", help="Paste candidate text interactively.")

    upload_parser = subparsers.add_parser("upload", help="Upload a resume file.")
    upload_parser.add_argument("file", nargs="?", help="Path to PDF/DOC/DOCX resume.")

    args = parser.parse_args()
    logger = RunLogger()

    if args.mode == "paste":
        sys.exit(_run_paste(logger))
    elif args.mode == "upload":
        file_path = getattr(args, "file", None)
        sys.exit(_run_upload(file_path, logger))
    elif args.mode == "serve":
        run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
