from __future__ import annotations

import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request

from src.extractors import orchestrator
from src.extractors.types import ParseStatus
from src.input_handler import InputError, acquire_from_file, acquire_from_paste
from src.logger import RunLogger
from src.schema import CandidateData, from_dict, validate
from src.submitter import submit

# Directory that uploaded resumes are temporarily stored in between
# /extract and /confirm.  We validate paths are inside this dir on confirm.
_TEMP_DIR = Path(tempfile.gettempdir())


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
    )

    @app.get("/")
    def index():
        return render_template("index.html")

    # ------------------------------------------------------------------
    # Stage 1: Extract — parse input, return review form
    # ------------------------------------------------------------------
    @app.post("/extract")
    def extract_candidate():
        logger = RunLogger()
        mode = (request.form.get("mode") or "paste").strip().lower()

        try:
            raw_text, resume_temp_path = _resolve_input(mode, logger)
        except InputError as exc:
            return render_template(
                "index.html",
                error=str(exc),
            )
        except Exception as exc:
            logger.error("web.unhandled_exception", error=str(exc)[:300])
            return render_template("index.html", error="Unexpected error reading input.")

        parse_result = orchestrator.run(raw_text, logger)

        if parse_result.status != ParseStatus.VALID:
            return render_template(
                "index.html",
                error="Extraction failed — required fields could not be found.",
                details=parse_result.errors,
            )

        c = parse_result.candidate
        extracted = {
            "name": c.name or "",
            "phoneNumber": c.phoneNumber or "",
            "email": c.email or "",
            "gender": str(c.gender) if c.gender is not None else "",
            "dob": str(c.dob) if c.dob is not None else "",
            "tag": str(c.tag) if c.tag is not None else "",
            "currentAddress": c.currentAddress or "",
            "totalExperience": str(c.totalExperience) if c.totalExperience is not None else "",
            "jewelleryExperience": str(c.jewelleryExperience) if c.jewelleryExperience is not None else "",
            "expectedSalary": str(c.expectedSalary) if c.expectedSalary is not None else "",
            "currentOrganisation": c.currentOrganisation or "",
            "currentDesignation": c.currentDesignation or "",
            "preferredLocation": c.preferredLocation or "",
            "currentInhandSalary": str(c.currentInhandSalary) if c.currentInhandSalary is not None else "",
        }

        return render_template(
            "index.html",
            review=True,
            extracted=extracted,
            provider=parse_result.provider,
            resume_temp_path=str(resume_temp_path) if resume_temp_path else "",
        )

    # ------------------------------------------------------------------
    # Stage 2: Confirm — user-edited fields → validate → POST to API
    # ------------------------------------------------------------------
    @app.post("/confirm")
    def confirm_candidate():
        logger = RunLogger()

        # Rebuild CandidateData from user-submitted (possibly edited) form values.
        def _f(key: str) -> str:
            return (request.form.get(key) or "").strip()

        def _num(key: str):
            val = _f(key)
            try:
                return float(val) if val else None
            except ValueError:
                return None

        candidate = CandidateData(
            name=_f("name") or None,
            phoneNumber=_f("phoneNumber") or None,
            email=_f("email") or None,
            gender=_f("gender") or None,
            dob=_f("dob") or None,
            tag=_f("tag") or None,
            currentAddress=_f("currentAddress") or None,
            totalExperience=_num("totalExperience"),
            jewelleryExperience=_num("jewelleryExperience"),
            expectedSalary=_num("expectedSalary"),
            currentOrganisation=_f("currentOrganisation") or None,
            currentDesignation=_f("currentDesignation") or None,
            preferredLocation=_f("preferredLocation") or None,
            currentInhandSalary=_num("currentInhandSalary"),
        )
        provider = _f("provider")

        # Validate before hitting the API.
        vr = validate(candidate)
        if not vr.valid:
            # Return to review form with same values so user can fix.
            extracted = {
                "name": candidate.name or "",
                "phoneNumber": candidate.phoneNumber or "",
                "email": candidate.email or "",
                "gender": str(candidate.gender) if candidate.gender else "",
                "dob": str(candidate.dob) if candidate.dob else "",
                "tag": str(candidate.tag) if candidate.tag else "",
                "currentAddress": candidate.currentAddress or "",
                "totalExperience": str(candidate.totalExperience) if candidate.totalExperience is not None else "",
                "jewelleryExperience": str(candidate.jewelleryExperience) if candidate.jewelleryExperience is not None else "",
                "expectedSalary": str(candidate.expectedSalary) if candidate.expectedSalary is not None else "",
                "currentOrganisation": candidate.currentOrganisation or "",
                "currentDesignation": candidate.currentDesignation or "",
                "preferredLocation": candidate.preferredLocation or "",
                "currentInhandSalary": str(candidate.currentInhandSalary) if candidate.currentInhandSalary is not None else "",
            }
            return render_template(
                "index.html",
                review=True,
                extracted=extracted,
                provider=provider,
                resume_temp_path=_f("resume_temp_path"),
                validation_errors=vr.errors,
            )

        # Resolve resume temp path safely.
        resume_path: Path | None = None
        raw_temp = _f("resume_temp_path")
        if raw_temp:
            candidate_path = Path(raw_temp).resolve()
            # Security: only allow paths inside the system temp directory.
            if candidate_path.is_relative_to(_TEMP_DIR) and candidate_path.exists():
                resume_path = candidate_path

        try:
            submit_result = submit(candidate, logger, resume_path=resume_path)
        finally:
            # Always clean up temp file once we're done with it.
            if resume_path and resume_path.exists():
                resume_path.unlink(missing_ok=True)

        if submit_result.success:
            return render_template(
                "index.html",
                result={"ok": True, "message": submit_result.message, "provider": provider},
            )

        return render_template(
            "index.html",
            result={"ok": False, "error": submit_result.message, "provider": provider},
        )

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    app = create_app()
    print(f"Web UI running at http://{host}:{port}")
    print("Open this URL in your browser and choose Paste or Upload mode.")
    app.run(host=host, port=port, debug=False)


def _resolve_input(mode: str, logger: RunLogger) -> tuple[str, Path | None]:
    if mode == "upload":
        file_storage = request.files.get("resume_file")
        if not file_storage or not file_storage.filename:
            raise InputError("Please choose a resume file for upload mode.")

        suffix = Path(file_storage.filename).suffix.lower()
        # Use delete=False so the file persists until /confirm cleans it up.
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, dir=_TEMP_DIR) as tmp:
            file_storage.save(tmp.name)
            temp_path = Path(tmp.name)

        text, resolved = acquire_from_file(temp_path, logger)
        # Return resolved path (used later for attaching to multipart).
        return text, resolved

    raw_text = request.form.get("raw_text", "")
    text = acquire_from_paste(raw_text)
    return text, None
