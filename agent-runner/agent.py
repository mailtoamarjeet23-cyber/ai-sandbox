#!/usr/bin/env python3
"""
Sandbox Exploration Agent
- Verifies its own safety controls (UID, read-only FS, network egress)
- Explores eShopOnWeb and Medplum FHIR APIs via HTTP
- Writes a structured JSON audit log to /output/agent_audit.log
"""
import json
import os
import time
import requests
from datetime import datetime, timezone

# Drop from root to UID 1000 (agent / users) immediately — before any work.
# The entrypoint runs as root to fix /output ownership, then exec's this script.
if os.getuid() == 0:
    os.setgroups([])
    os.setgid(100)   # users group
    os.setuid(1000)

ESHOP_BASE   = os.getenv("ESHOP_BASE_URL",  "http://eshop:80")
MEDPLUM_BASE = os.getenv("MEDPLUM_BASE_URL", "http://medplum:8103")
AUDIT_LOG    = "/output/agent_audit.log"
MAX_WAIT_S   = 120
POLL_S       = 5

_entries = []


def log(action, status, detail=None):
    entry = {"ts": datetime.now(timezone.utc).isoformat(),
             "action": action, "status": status}
    if detail:
        entry["detail"] = detail
    _entries.append(entry)
    icon = "✓" if status == "ok" else ("⚠" if "warn" in status else "✗")
    suffix = f"  ({detail})" if detail else ""
    print(f"[agent] {icon} {action}: {status}{suffix}", flush=True)


# ── Safety self-checks ─────────────────────────────────────────────────────────

def check_uid():
    uid = os.getuid()
    if uid == 0:
        log("safety:uid", "warn_root", "running as root — non-root not enforced")
    else:
        log("safety:uid", "ok", f"UID={uid} (non-root)")


def check_readonly_fs():
    # Overlay FS (/app) must be read-only when read_only:true is set in Compose.
    try:
        with open("/app/.write_probe", "w") as f:
            f.write("x")
        os.unlink("/app/.write_probe")
        log("safety:readonly_fs", "warn_writable", "/app is writable — read_only not enforced")
    except (PermissionError, OSError):
        log("safety:readonly_fs", "ok", "/app is read-only")


def check_tmp_writable():
    # /tmp must be writable (tmpfs mount).
    try:
        probe = "/tmp/.agent_probe"
        with open(probe, "w") as f:
            f.write("x")
        os.unlink(probe)
        log("safety:tmp_writable", "ok", "/tmp writable via tmpfs")
    except Exception as exc:
        log("safety:tmp_writable", "error", str(exc))


def check_egress():
    # Attempt internet access — must be blocked when agent-net has internal:true.
    try:
        requests.get("https://example.com", timeout=4)
        log("safety:egress", "warn_open",
            "internet reachable — internal:true not set on agent-net")
    except Exception:
        log("safety:egress", "ok", "internet not reachable — egress blocked")


# ── Service health polling ─────────────────────────────────────────────────────

def wait_healthy(name, url):
    deadline = time.time() + MAX_WAIT_S
    attempt  = 0
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code < 500:
                log(f"health:{name}", "ok",
                    f"HTTP {r.status_code} after {attempt * POLL_S}s")
                return True
        except Exception:
            pass
        attempt += 1
        time.sleep(POLL_S)
    log(f"health:{name}", "timeout", f"not reachable after {MAX_WAIT_S}s")
    return False


# ── eShopOnWeb exploration ─────────────────────────────────────────────────────

def explore_eshop():
    try:
        r = requests.get(f"{ESHOP_BASE}/", timeout=10)
        log("eshop:homepage", "ok", f"HTTP {r.status_code}, {len(r.content)} bytes")
    except Exception as exc:
        log("eshop:homepage", "error", str(exc))
        return

    try:
        r = requests.get(f"{ESHOP_BASE}/api/catalog/items?pageSize=5", timeout=10)
        if r.status_code == 200:
            data  = r.json()
            items = data.get("data", [])
            names = [i.get("name", "?") for i in items[:3]]
            log("eshop:catalog_api", "ok", f"{len(items)} items — e.g. {names}")
        else:
            log("eshop:catalog_api", f"http_{r.status_code}", r.text[:120])
    except Exception as exc:
        log("eshop:catalog_api", "error", str(exc))


# ── Medplum FHIR exploration ───────────────────────────────────────────────────

def explore_medplum():
    try:
        r    = requests.get(f"{MEDPLUM_BASE}/healthcheck", timeout=10)
        body = r.json()
        log("medplum:healthcheck", "ok", f"ok={body.get('ok')}")
    except Exception as exc:
        log("medplum:healthcheck", "error", str(exc))
        return

    # FHIR capability statement (public, no auth required)
    try:
        r = requests.get(f"{MEDPLUM_BASE}/fhir/R4/metadata", timeout=10)
        if r.status_code == 200:
            meta    = r.json()
            version = meta.get("fhirVersion", "?")
            n_types = len(meta.get("rest", [{}])[0].get("resource", []))
            log("medplum:fhir_metadata", "ok",
                f"FHIR {version}, {n_types} resource types supported")
        else:
            log("medplum:fhir_metadata", f"http_{r.status_code}", r.text[:120])
    except Exception as exc:
        log("medplum:fhir_metadata", "error", str(exc))

    # Patient list — expects 401 (auth required), not 500
    try:
        r = requests.get(f"{MEDPLUM_BASE}/fhir/R4/Patient", timeout=10)
        if r.status_code == 401:
            log("medplum:fhir_patient_list", "ok",
                "HTTP 401 — auth required as expected (server healthy)")
        else:
            log("medplum:fhir_patient_list", f"http_{r.status_code}", r.text[:80])
    except Exception as exc:
        log("medplum:fhir_patient_list", "error", str(exc))


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("[agent] ════════════════════════════════════════", flush=True)
    print("[agent]  Sandbox Exploration Agent v1.0", flush=True)
    print("[agent] ════════════════════════════════════════", flush=True)
    log("agent:start", "ok", f"UID={os.getuid()}")

    print("\n[agent] ── Safety self-checks ──────────────", flush=True)
    check_uid()
    check_readonly_fs()
    check_tmp_writable()
    check_egress()

    print("\n[agent] ── eShopOnWeb (.NET / in-memory DB) ─", flush=True)
    if wait_healthy("eshop", f"{ESHOP_BASE}/"):
        explore_eshop()

    print("\n[agent] ── Medplum FHIR (Node / PostgreSQL) ─", flush=True)
    if wait_healthy("medplum", f"{MEDPLUM_BASE}/healthcheck"):
        explore_medplum()

    ok_n   = sum(1 for e in _entries if e["status"] == "ok")
    warn_n = sum(1 for e in _entries if "warn" in e["status"])
    err_n  = sum(1 for e in _entries if e["status"] in ("error", "timeout"))

    summary = {
        "agent":       "sandbox-exploration-agent-v1",
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "totals":      {"ok": ok_n, "warn": warn_n, "error": err_n},
        "actions":     _entries,
    }
    with open(AUDIT_LOG, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n[agent] ════════════════════════════════════════", flush=True)
    print(f"[agent]  {ok_n} ok  {warn_n} warn  {err_n} error", flush=True)
    print(f"[agent]  Audit log → {AUDIT_LOG}", flush=True)
    print("[agent] ════════════════════════════════════════", flush=True)


if __name__ == "__main__":
    main()
