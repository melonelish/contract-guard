#!/usr/bin/env python3
"""Phase 5 smoke test — real end-to-end contract review pipeline.

Usage:
    python scripts/smoke_phase5.py

Environment variables (all optional, sensible defaults):
    SMOKE_API_URL      — Backend base URL  (default: http://localhost:8000)
    SMOKE_EMAIL        — Test user email   (default: smoke@test.com)
    SMOKE_PASSWORD     — Test password     (default: smokepass123)
    SMOKE_TIMEOUT      — Max seconds to wait for review (default: 180)
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API_URL = "http://localhost:8000"
EMAIL = "smoke@test.com"
PASSWORD = "smokepass123"
TIMEOUT = 180
TEST_PDF = Path(__file__).resolve().parent / "_test.pdf"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def api(method: str, path: str, token: str | None = None, *, data=None, files=None) -> dict:
    """Simple HTTP client using stdlib urllib."""
    url = f"{API_URL}{path}"
    headers: dict[str, str] = {}
    body: bytes | None = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if files:
        # multipart/form-data
        boundary = "----SmokeTestBoundary"
        lines = []
        for key, (filename, file_bytes, content_type) in files.items():
            lines.append(f"--{boundary}".encode())
            disp = f'Content-Disposition: form-data; name="{key}"; filename="{filename}"'
            lines.append(disp.encode())
            lines.append(f"Content-Type: {content_type}".encode())
            lines.append(b"")
            lines.append(file_bytes)
        if data:
            for key, value in data.items():
                lines.append(f"--{boundary}".encode())
                lines.append(f'Content-Disposition: form-data; name="{key}"'.encode())
                lines.append(b"")
                lines.append(str(value).encode())
        lines.append(f"--{boundary}--".encode())
        lines.append(b"")
        body = b"\r\n".join(lines)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    elif data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode() if exc.fp else ""
        try:
            err_json = json.loads(err_body)
        except (json.JSONDecodeError, ValueError):
            err_json = {"detail": err_body}
        raise RuntimeError(f"HTTP {exc.code}: {err_json}") from exc


def log(stage: str, msg: str) -> None:
    ts = time.strftime("%H:%M:%S")
    print(f"  [{ts}] {stage}: {msg}")


def log_ok(msg: str) -> None:
    log("OK", msg)


def log_step(msg: str) -> None:
    log(">>", msg)


def log_fail(msg: str) -> None:
    log("FAIL", msg)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("  ContractGuard Phase 5 — Smoke Test")
    print("=" * 60)
    print()

    start = time.time()

    # ---- Step 1: Health check ----
    log_step("Checking backend health...")
    try:
        health = api("GET", "/api/v1/health")
        assert health["data"]["status"] == "healthy", f"Unhealthy: {health}"
        log_ok(f"Backend healthy — {health['data']['checks']}")
    except Exception as exc:
        log_fail(f"Backend unreachable: {exc}")
        return 1

    # ---- Step 2: Register / login ----
    log_step("Registering test user...")
    token: str | None = None
    try:
        reg = api("POST", "/api/v1/auth/register", data={
            "email": EMAIL,
            "password": PASSWORD,
            "name": "Smoke Tester",
            "tenant_name": "SmokeTenant",
        })
        token = reg["data"]["access_token"]
        log_ok(f"Registered: {reg['data']['user']['email']}")
    except RuntimeError as exc:
        if "409" in str(exc) or "already" in str(exc).lower():
            log_ok("User exists, logging in instead...")
            login = api("POST", "/api/v1/auth/login", data={
                "email": EMAIL,
                "password": PASSWORD,
            })
            token = login["data"]["access_token"]
            log_ok(f"Logged in: {login['data']['user']['email']}")
        else:
            log_fail(f"Auth failed: {exc}")
            return 1

    assert token is not None

    # ---- Step 3: Upload contract ----
    log_step("Uploading test contract...")
    if not TEST_PDF.exists():
        log_fail(f"Test PDF not found: {TEST_PDF}")
        return 1

    pdf_bytes = TEST_PDF.read_bytes()
    upload = api("POST", "/api/v1/contracts/upload", token, data={
        "title": "Smoke测试合同",
    }, files={
        "file": ("_test.pdf", pdf_bytes, "application/pdf"),
    })
    contract_id = upload["data"]["id"]
    log_ok(f"Uploaded: contract_id={contract_id}")

    # ---- Step 4: Trigger review ----
    log_step("Triggering review...")
    trigger = api("POST", f"/api/v1/contracts/{contract_id}/review", token)
    review_id = trigger["data"]["id"]
    initial_status = trigger["data"]["status"]
    log_ok(f"Review triggered: review_id={review_id}, status={initial_status}")

    assert initial_status == "queued", f"Expected queued, got {initial_status}"

    # ---- Step 5: Poll until terminal ----
    log_step(f"Polling status (timeout={TIMEOUT}s)...")
    poll_start = time.time()
    last_status = ""
    terminal = False

    while time.time() - poll_start < TIMEOUT:
        status_resp = api("GET", f"/api/v1/reviews/{review_id}/status", token)
        data = status_resp["data"]
        cur_status = data["status"]
        progress = data["progress"]

        if cur_status != last_status:
            elapsed = time.time() - poll_start
            log("STATUS", f"{cur_status} ({progress}%) at +{elapsed:.0f}s")
            last_status = cur_status

        if cur_status in ("completed", "failed"):
            terminal = True
            break

        time.sleep(2)

    if not terminal:
        log_fail(f"Timeout after {TIMEOUT}s, last status={last_status}")
        return 1

    elapsed_total = time.time() - poll_start

    # ---- Step 6: Fetch report ----
    log_step("Fetching full report...")
    report = api("GET", f"/api/v1/reviews/{review_id}", token)
    report_data = report["data"]

    final_status = report_data["status"]
    summary = report_data.get("summary") or {}
    risk_count = summary.get("total_risks", 0)
    high = summary.get("high", 0)
    medium = summary.get("medium", 0)
    low = summary.get("low", 0)
    error_detail = report_data.get("error_detail")
    has_disclaimer = bool(report_data.get("disclaimer"))
    contradictions = len(report_data.get("contradictions", []))
    missing = len(report_data.get("missing_clauses", []))

    # ---- Summary ----
    print()
    print("=" * 60)
    if final_status == "completed":
        print("  [PASS] SMOKE TEST PASSED")
    else:
        print("  [FAIL] SMOKE TEST FAILED")
    print("=" * 60)
    print(f"  Contract ID : {contract_id}")
    print(f"  Review ID   : {review_id}")
    print(f"  Final status: {final_status}")
    print(f"  Poll time   : {elapsed_total:.1f}s")
    if final_status == "completed":
        print(f"  Risks       : {risk_count} (high={high}, medium={medium}, low={low})")
        print(f"  Contradictions: {contradictions}")
        print(f"  Missing     : {missing}")
        print(f"  Disclaimer  : {has_disclaimer}")
        llm = report_data.get("llm_meta") or {}
        if llm:
            print(f"  Model       : {llm.get('provider_model', '?')}")
            p_tok = llm.get("prompt_tokens", 0)
            c_tok = llm.get("completion_tokens", 0)
            print(f"  Tokens      : in={p_tok} out={c_tok}")
    if error_detail:
        print(f"  Error       : {error_detail[:200]}")
    print("=" * 60)
    print()

    # ---- Write report JSON ----
    report_path = Path(__file__).resolve().parent / "_smoke_report.json"
    report_path.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    log_ok(f"Report saved to {report_path}")

    total_elapsed = time.time() - start
    print(f"\n  Total wall time: {total_elapsed:.1f}s")

    return 0 if final_status == "completed" else 1


if __name__ == "__main__":
    sys.exit(main())
