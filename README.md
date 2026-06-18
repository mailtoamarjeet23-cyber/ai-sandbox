# AI Agent Sandbox (Docker-Based)

A Docker-based sandbox for AI coding agents to clone repositories, build code, run tests, and capture structured output — without affecting the host machine. Supports two real-world open-source projects with different technology stacks.

---

## Quick Start

```bash
cp .env.example .env       # fill in credentials
bash scripts/run-sandbox.sh
```

| Service  | URL                               |
|----------|-----------------------------------|
| eShop    | http://localhost:5001             |
| Medplum  | http://localhost:8103/healthcheck |

---

## Project Structure

```
ai-sandbox/
├── docker-compose.yml        # orchestrates all services
├── .env                      # credentials (gitignored)
├── .env.example              # safe template to commit
├── .gitignore
├── eshop/
│   ├── Dockerfile            # build + runtime image
│   └── entrypoint.sh         # migrations → tests → start
├── medplum/
│   ├── Dockerfile            # build + runtime image
│   └── entrypoint.sh         # config generation → start
├── scripts/
│   └── run-sandbox.sh        # spin up + health polling
└── output/                   # structured test results (gitignored)
    ├── eshop_unit_tests.trx
    └── eshop_tests.log
```

---

## Design Decisions

### 1. One Sandbox or Two?

**Decision: Single Docker Compose environment with isolated services.**

Both projects share one `docker-compose.yml` with separate containers per service. This gives:
- Simpler orchestration and a single `docker compose up` entry point
- Centralized lifecycle management (`docker compose down -v` resets everything)
- Easier integration with AI pipelines that expect one command to spin up the environment

The tradeoff is higher memory usage (SQL Server + PostgreSQL both running simultaneously). Per-agent isolation would require separate Compose files or dynamic container spawning — too complex for this scope.

### 2. Database Strategy

**Decision: Run both database engines — SQL Server for eShop, PostgreSQL + Redis for Medplum.**

The two projects have incompatible database requirements:
- eShopOnWeb requires SQL Server (EF Core migrations, identity schema)
- Medplum requires PostgreSQL and Redis (TypeORM + caching layer)

Consolidating onto one engine would require rewriting ORM configurations in both projects — out of scope. Schema isolation is handled naturally since each DB engine runs in its own container on its own port with separate credentials.

### 3. Clean State Between Runs

**Decision: `docker compose down -v` destroys all volumes; `docker compose up --build` rebuilds from scratch.**

The `run-sandbox.sh` script starts with `docker compose down -v` to remove named volumes and any persisted state. This guarantees every run starts from a clean database. The `-v` flag is the key — without it, data volumes survive between runs and migrations or seed data may be skipped on the second run.

For faster iteration (preserve image layer cache but reset data only):
```bash
docker compose down -v && docker compose up -d
```

### 4. Non-Interactive Execution

**Decision: All interactive assumptions are eliminated at the Dockerfile and entrypoint level.**

Known interactive assumptions handled:
- **SQL Server EULA**: accepted via `ACCEPT_EULA: "Y"` environment variable
- **dotnet CLI telemetry prompts**: suppressed by default in non-interactive shells
- **npm**: `npm ci` (not `npm install`) is deterministic and prompt-free
- **EF Core migrations**: run via `dotnet ef database update` in `entrypoint.sh` — no interactive input required
- **Medplum config**: generated from environment variables at container start — no manual file editing required

### 5. Build Performance

**Decision: `--depth=1` git clone + multi-stage builds + Turborepo filter.**

Key strategies:
- `git clone --depth=1` skips the full commit history — significantly reduces clone time for large repos
- Multi-stage Dockerfiles separate build from runtime — layer cache is preserved on rebuilds when only the entrypoint changes
- Medplum uses `npx turbo build --filter=@medplum/server` — builds only the server package and its local workspace dependencies, not the full React app and all other packages
- `dotnet build --no-restore` and `dotnet test --no-build` reuse already-compiled artifacts without triggering unnecessary rebuilds

### 6. Output Capture

**Decision: Structured output written to `/output` volume, mounted from `./output` on the host.**

Both services mount `./output:/output`. Test results are written there:
- `output/eshop_unit_tests.trx` — Visual Studio test results XML (machine-readable by CI and AI agents)
- `output/eshop_tests.log` — plain text log (human-readable)

The `.trx` format is parseable without scraping terminal output. Medplum test output can similarly write to `/output/medplum_tests.json` when a test step is added to its entrypoint.

### 7. Resource Management

**Decision: Memory limits set per service via `deploy.resources.limits`.**

| Service    | Memory Limit | Rationale                                    |
|------------|-------------|----------------------------------------------|
| SQL Server | 2 GB        | Minimum recommended; will OOM-kill below this |
| eShop      | 1 GB        | .NET SDK + build tooling at runtime           |
| PostgreSQL | 512 MB      | Sufficient for Medplum schema                 |
| Medplum    | 1 GB        | Node.js monorepo runtime                      |
| Redis      | 256 MB      | Cache layer only                              |

**Total: ~4.75 GB minimum.** Requires a host with at least 6 GB available for Docker. Limits use `deploy.resources` syntax supported by Docker Compose v2 (CLI plugin).

### 8. Security and Isolation

**Decision: All services run on an isolated Docker bridge network (`sandbox`); credentials injected via environment variables only.**

- Containers communicate only via the `sandbox` network — not reachable from outside except on explicitly published ports
- Credentials are never hardcoded in Dockerfiles or Compose files — all passed via `.env` (gitignored)
- `.env.example` with placeholder values is what gets committed to source control
- AI-generated code runs inside containers — it cannot access the host filesystem, host network, or other Docker networks

Known limitation: containers share a single bridge network, so eShop could theoretically reach the Medplum database. Stricter isolation would require per-project networks with explicit service aliases — a reasonable next step for a production sandbox.

---

## What "Works" Means

**eShopOnWeb:**
- Application builds (dotnet build Release)
- EF Core migrations run (CatalogContext + AppIdentityDbContext)
- Seed data loads on first startup (via SeedData class in Web startup)
- Web app starts and responds at http://localhost:5001
- Unit test suite passes with output in `./output/eshop_unit_tests.trx`

**Medplum:**
- Server package builds via Turborepo filter
- Config generated from environment at runtime
- Database migrations run automatically on server start (TypeORM)
- API health check responds at http://localhost:8103/healthcheck

---

## Resetting the Sandbox

```bash
docker compose down -v          # stop all containers and wipe all volumes
docker compose up --build -d    # rebuild images and start fresh
```

---

## Known Limitations and Next Steps

- **Integration tests for eShop** require the app to be running — currently only unit tests run in the entrypoint. A post-startup test runner script would be needed.
- **Medplum signing keys** — a production Medplum setup requires JWT signing key configuration. The minimal config here starts the server; full auth requires additional config fields.
- **Per-agent isolation** — for running multiple agents concurrently, each would need its own container set with isolated volumes and ports. This would require dynamic Compose generation or a container orchestrator.
- **Image size** — SDK images are large (~800 MB each). A future optimization is to run tests in a sidecar container and use a smaller runtime image for the web app itself.
