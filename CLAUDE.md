# CLAUDE.md — AI Agent Sandbox

Interview Task 003 · DevOps Engineer · HEALWELL AI / Intrahealth
Repository: https://github.com/mailtoamarjeet23-cyber/ai-sandbox

---

## What This Project Is

A Docker-based sandbox where AI agents run safely against two real applications:
- **eShopOnWeb** — ASP.NET Core / .NET 10 / in-memory DB (port 5001)
- **Medplum** — FHIR R4 healthcare platform / Node.js 22 / PostgreSQL / Redis (port 8103)
- **agent-runner** — Python 3.12 one-shot agent with safety controls enforced

---

## Key Commands

```bash
# Start everything
docker compose up -d

# Start with rebuild (after code changes)
docker compose up --build -d

# Graceful stop (keeps volumes)
docker compose down

# Full reset — stops + wipes all volumes and data
docker compose down -v

# Check status
docker compose ps --all

# Follow agent output
docker compose logs agent-runner

# Scripted start with health polling
bash scripts/run-sandbox.sh
```

---

## Credentials

- **Never hardcode credentials** — always use `${ENV_VAR}` references in docker-compose.yml
- Real values go in `.env` (gitignored — never commit this file)
- `.env.example` contains placeholders only — this is what gets committed
- Verify with: `git ls-files --others --ignored --exclude-standard | grep env`

---

## Network Architecture

Two bridge networks:
- `sandbox` — connects apps to their databases (external access allowed)
- `agent-net` (`internal: true`) — connects agent-runner to eshop + medplum only; **no internet egress, no database access**

agent-runner is on `agent-net` only. Databases (postgres, redis, sqlserver) are on `sandbox` only.

---

## Agent Safety Controls (agent-runner)

All implemented and verified at runtime:
- Non-root: `os.setuid(1000)` at top of `agent.py`
- Read-only filesystem: `read_only: true` in Compose
- No internet: `internal: true` on agent-net
- No DB access: agent-runner not on sandbox network
- No privilege escalation: `security_opt: no-new-privileges:true`
- Resource caps: `cpus: "0.50"`, `memory: 256m`
- Scratch space: `/tmp` via tmpfs only

Agent output → `output/agent_audit.log` (structured JSON)

---

## Key Technical Facts

- eShop requires **.NET SDK 10.0** — both Dockerfile stages use `mcr.microsoft.com/dotnet/sdk:10.0`
- eShop uses `ASPNETCORE_ENVIRONMENT=Docker` — not `Development` (avoids static asset loading crash)
- eShop tests use `dotnet vstest <dll>` not `dotnet test --no-build` (.NET 10 swallows output)
- eShop entrypoint must `cd` to DLL directory before `exec dotnet` (content root = CWD)
- SQL Server replaced with `mcr.microsoft.com/azure-sql-edge:latest` — native ARM64 for Apple Silicon
- Medplum requires **Node.js 22** — native WebSocket absent in Node 20
- Medplum config format: `file:/app/medplum.config.json` (type:path colon-separated)
- Medplum Jest tests must run from `packages/server/` — babel-jest resolves `<rootDir>` from there
- Jest 30 flag: `--testPathPatterns` (not `--testPathPattern`)

---

## Test Results (verified)

| Suite | Result |
|---|---|
| eShopOnWeb unit tests | 44/44 passed (dotnet vstest, 0.47s) |
| Medplum server tests | 236/236 passed (Jest, 14 suites, 4.22s) |
| agent-runner safety audit | 11/11 ok, 0 warn, 0 error |

Test output files (gitignored, written to `output/`):
- `eshop_tests.log`, `eshop_unit_tests.trx`
- `medplum_tests.log`, `medplum_tests.json`
- `agent_audit.log`

---

## GitHub CLI

`gh` is installed at `/Users/singh/.local/bin/gh` — use full path if not in PATH.

---

## Remaining Safety Gaps (not in scope for sandbox)

Documented in Section 4.4 of the design document:
1. Per-stack DB isolation (eshop-net / medplum-net)
2. Independent sidecar audit log (Fluent Bit)
3. API rate limiting (Nginx reverse proxy)
4. Secrets manager (Docker Secrets / Vault)
