# CONTEXT.md

## 1. Goal & Metric (1 line)
Automated cross-platform collection of `hvigor` build performance metrics (duration, RSS/PSS/USS/CPU, GC) with ≤3% monitoring overhead and ±5% reproducibility (p50/p90).

## 2. Stack (YAML)
```yaml
runtime:
  python: ">=3.10"
  node: ">=18.0 LTS (hvigor execution runtime, not instrumented)"
core_libraries:
  - psutil: ">=6.0.0 (critical for native USS on Windows)"
  - sqlite3: "stdlib"
  - argparse: "stdlib"
  - json: "stdlib"
  - csv: "stdlib"
storage:
  primary: "SQLite (WAL mode enabled, PRAGMA journal_mode=WAL)"
  external: "PostgreSQL / MySQL (optional, via SQLAlchemy)"
os_support:
  - "Windows 10/11 (x86_64)"
  - "Ubuntu 20.04–24.04 (x86_64/aarch64)"
logging:
  format: "JSON lines"
  rotation: "10 MB"
  output: ["stderr", "~/.deveco-measurer/logs/"]
ci_cd:
  targets: ["GitHub Actions", "GitLab CI", "Jenkins"]
  mode: "headless"
  exit_codes: [0, 1, 2]
```

## 3. 🚫 Hard Constraints (verifiable)
- Monitoring overhead on build wall-clock time: ≤3% (verified via 10-run baseline comparison).
- Metric reproducibility under identical conditions: ±5% for p50/p90, ±8% for p99 (5 consecutive runs).
- Timestamp accuracy: deviation ≤10 ms from system clock (`date +%s%N`).
- Collector resource limits: CPU ≤2% of a single core, RAM ≤50 MB RSS.
- Default sampling interval: 250 ms (allowed range: 100–1000 ms via `--sample-interval-ms`).
- Build timeout: 3600 s default. Termination sequence: `SIGTERM`/`TerminateJobObject` → 10 s grace → `SIGKILL`/`TerminateProcess`.
- Process tree rooting: Strictly anchored to the PID of `node` executing `hvigorw.js`. Validation requires cmdline match + spawn time correlation (±2 s tolerance).
- Valid run criteria: ≥80% collected samples, successful root PID match, complete metadata block.
- Zero modification of `hvigor` source, DevEco Studio binaries, or project configuration files.
- Windows PSS: approximated (±5–7% error) or returns `null` in `--metric-mode strict`; USS is native on both platforms.
- Database writes: strictly append-only; transactions atomic; exports read-only.
- All DB records and export payloads must contain `schema_version` (semver).

## 4. 📐 Architectural Rules (structure, layer separation, naming)
- **Layer Separation:** `Orchestrator` (lifecycle) → `SDK Manager` → `Build Runner` → `Process Monitor` → `Metrics Aggregator` → `Storage/Exporter`. Components are isolated; communication strictly via defined interfaces.
- **Cross-Platform Abstraction:** Interfaces `ITreeBuilder`, `ISampler`, `ITerminator` with platform-specific implementations (`linux.py`, `windows.py`) registered in `platform_registry.py`.
- **Package Structure:** `src/{cli, orchestrator, sdk_manager, build_runner, process_monitor, metrics, storage, export, logging}`.
- **Naming Contracts:** `run_id` → UUIDv4; timestamps → ISO 8601 UTC with milliseconds; versions (`schema_version`, `tool_version`) → semver; DB/JSON fields → `snake_case`.
- **State Management:** `RunConfig` is immutable; `RunContext` is updated exclusively by the Orchestrator. Direct cross-component state access is prohibited.
- **Environment Injection:** Variables (`OHOS_SDK_HOME`, `PATH`, `NODE_PATH`) resolved from SDK `.env` files and merged with host environment. Project files remain unmodified.
- **Logging:** Dual-channel: human-readable stderr (ERROR/WARN/INFO/DEBUG/TRACE) + machine-parseable JSON lines in `~/.deveco-measurer/logs/` with 10 MB rotation.
- **Tree Memory Aggregation:** Peak computed as `max(t) Σ memory_i(t)` across synchronized sample timestamps, never as the sum of individual process peaks.

## 5. ✅ DoD for Components/API/DB
| Component / Layer | Acceptance Criteria (DoD) |
|---|---|
| **CLI** | Subcommands `run`, `schedule`, `sdk`, `export`, `report` with `--help`. Missing required flags → exit code 2 + usage hint. `--verbose`/`--quiet` toggle output levels. |
| **Process Monitor** | 100% PID tree reconstruction accuracy in unit tests. System processes filtered (PID<100 Linux, System/Idle Windows). Orphans & short-lived processes handled gracefully without crashes. |
| **Metrics & Aggregation** | Percentiles (p50/p90/p95/p99) via linear interpolation. GC parser (`--trace-gc`) returns `{phase, timestamp_us, duration_us, heap_type, bytes_before, bytes_after}`. Aggregates: min, max, mean, p*, sum, peak. |
| **Storage & DB** | SQLite schema strictly matches DDL (`runs`, `processes`, `samples`, `gc_events`, `aggregates`). `uss_bytes` → `INTEGER NOT NULL`, `pss_bytes` → `REAL` (nullable allowed). FKs with `ON DELETE CASCADE`. WAL mode enforced. |
| **Export API** | JSON/CSV/SQL outputs include `schema_version`. Filtering by date, SDK, project, OS, run_id supported. Validated against JSON Schema / CSV headers. Export operations are strictly read-only. |
| **SDK Manager** | Mandatory `sha256` verification of archives & `metadata.json`. `sdk validate` blocks runs on mismatch unless `--force` is passed. Supports `--from-file` for offline registration. |
| **Failure Handling** | Statuses: `SUCCESS` / `FAILED` / `INVALID` / `TIMEOUT`. `sample_gap > 20%` or `ROOT_MISMATCH` → `INVALID`. Partial metric loss does not abort runs; recorded in `metric_completeness_pct`. |
| **CI Integration** | Headless mode: exit 0/1/2, structured stderr, zero interactive prompts. Round-trip export→import preserves 100% data integrity. 5 consecutive runs → p50/p90 deviation ≤5%. |

## 6. 🔄 Changelog
| Date | Version | Author | Description of Changes |
|---|---|---|---|
| | | | |
