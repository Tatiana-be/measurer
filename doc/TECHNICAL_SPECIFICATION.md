# Technical Specification: DevEco hvigor Performance Measurer

**Document ID:** TS-DEVECO-MEASURER-001  
**Version:** 1.0.0  
**Status:** Draft for Review  
**Date:** 2026-04-12  
**Author:** System Engineering & Quality Assurance Team  
**Classification:** Internal — Engineering Use Only  

---

## Table of Contents

1. [Purpose and Scope](#1-purpose-and-scope)  
2. [Functional Requirements](#2-functional-requirements)  
3. [Non-Functional Requirements](#3-non-functional-requirements)  
4. [Measurement Methodology: Time & Memory](#4-measurement-methodology-time--memory)  
5. [Cross-Platform Metric Specifics](#5-cross-platform-metric-specifics)  
6. [OHOS SDK Version Management](#6-ohos-sdk-version-management)  
7. [Data Schema and Storage Format](#7-data-schema-and-storage-format)  
8. [Failure Handling and Validation](#8-failure-handling-and-validation)  
9. [Assumptions, Constraints & Trade-offs](#9-assumptions-constraints--trade-offs)  
10. [Acceptance Criteria and Validation Plan](#10-acceptance-criteria-and-validation-plan)  

**Appendices**  
- [A. Glossary](#a-glossary)  
- [B. Reference Documents](#b-reference-documents)  
- [C. Revision History](#c-revision-history)  

---

## 1. Purpose and Scope

### 1.1 Purpose

This document defines the technical specification for an automated, cross-platform performance measurement tool targeting the `hvigor` build system (Node.js-based) used in DevEco Studio for HarmonyOS application development. The tool shall provide repeatable, auditable benchmarks for build duration and memory consumption (RSS, PSS, USS) across the complete process tree, supporting multiple OHOS SDK versions and host operating systems.

### 1.2 In-Scope

| ID | Capability | Description |
|----|------------|-------------|
| IS-01 | CLI Orchestrator | Command-line interface for initiating, scheduling, and monitoring build runs with metric collection |
| IS-02 | Process-Tree Metric Collector | Recursive discovery and sampling of all child processes spawned by `hvigor`, capturing CPU time and memory at configurable intervals |
| IS-03 | SDK Version Manager | Automated provisioning, isolation, and switching between ≥3 OHOS SDK versions without project modification |
| IS-04 | Data Export & Storage | Structured export to JSON, CSV, and relational/NoSQL databases with schema versioning |
| IS-05 | Cross-Platform Support | Native execution on Windows 10/11 (x86_64) and Ubuntu 20.04–24.04 (x86_64/aarch64) |
| IS-06 | Failure Resilience | Timeout enforcement, retry logic, graceful degradation on partial metric loss |
| IS-07 | CI/CD Integration | Headless operation, machine-readable output, exit codes, and compatibility with GitHub Actions, GitLab CI, Jenkins |

### 1.3 Out-of-Scope

| ID | Exclusion | Rationale |
|----|-----------|-----------|
| OS-01 | Modification of `hvigor` or DevEco Studio source code | Tool operates as an external observer; no upstream patches |
| OS-02 | Runtime profiling of HarmonyOS applications or IDE UI components | Scope is limited to build-system performance only |
| OS-03 | Full BI/Analytics platform | Tool provides data export; visualization is deferred to downstream consumers |
| OS-04 | Benchmarking of compilers/linkers outside `hvigor` context | Metrics cover only processes directly spawned by the build orchestrator |
| OS-05 | macOS support | Not required by current stakeholder mandate; may be added in future releases |

---

## 2. Functional Requirements

### 2.1 CLI / Script Interface

| Req ID | Requirement | Priority | Acceptance Note |
|--------|-------------|----------|-----------------|
| FR-CLI-01 | Tool shall expose a CLI entry point: `deveco-measurer` | Must | `deveco-measurer --help` prints usage and exits 0 |
| FR-CLI-02 | CLI shall accept subcommands: `run`, `schedule`, `sdk`, `export`, `report` | Must | Each subcommand has dedicated `--help` |
| FR-CLI-03 | `run` subcommand shall accept: `--project <path>`, `--sdk-version <ver>`, `--target <assembleDebug\|assembleRelease>`, `--output <path>`, `--config <path>` | Must | Missing required flags yield exit code 2 with usage hint |
| FR-CLI-04 | `schedule` subcommand shall accept cron-like expressions or CI webhook URLs | Should | Integration tests verify scheduler triggers |
| FR-CLI-05 | `sdk` subcommand shall support: `list`, `install <version>`, `use <version>`, `validate` | Must | `sdk validate` checks integrity of installed SDK |
| FR-CLI-06 | `export` subcommand shall convert stored results to JSON, CSV, or SQLite | Must | Schema version included in all exports |
| FR-CLI-07 | Tool shall support `--verbose` / `--quiet` logging levels | Should | Default: info-level to stderr |
| FR-CLI-08 | Tool shall write structured logs (JSON lines) to `~/.deveco-measurer/logs/` | Should | Log rotation at 10 MB |

### 2.2 Build Execution

| Req ID | Requirement | Priority | Acceptance Note |
|--------|-------------|----------|-----------------|
| FR-BLD-01 | Tool shall invoke `hvigor` via spawned subprocess, capturing root PID | Must | Root PID used for process-tree traversal |
| FR-BLD-02 | Tool shall set `OHOS_SDK_HOME` and related env-vars per selected SDK version | Must | Verified via `sdk validate` pre-run |
| FR-BLD-03 | Tool shall enforce a configurable build timeout (default: 3600s) | Must | Timeout triggers SIGTERM (Unix) / TerminateJobObject (Win), then SIGKILL after 10s grace |
| FR-BLD-04 | Tool shall support clean (`hvigor clean`) before each run to ensure cache neutrality | Should | `--skip-clean` flag disables |
| FR-BLD-05 | Tool shall capture build exit code, stdout, stderr | Must | Stored alongside metrics |

### 2.3 Metric Collection

| Req ID | Requirement | Priority | Acceptance Note |
|--------|-------------|----------|-----------------|
| FR-MET-01 | Tool shall sample the full process tree (root `hvigor` + all descendants) at configurable intervals (default: 250ms) | Must | Interval configurable via `--sample-interval-ms` |
| FR-MET-02 | Tool shall capture per-sample: RSS, PSS (Linux), approximated PSS (Windows), USS (Linux), approximated USS (Windows), CPU user/system time | Must | Windows approximations documented (§5) |
| FR-MET-03 | Tool shall aggregate samples into: min, max, mean, p50, p90, p95, p99, sum for each metric per process and for the tree aggregate | Must | Aggregation algorithm: linear interpolation between samples |
| FR-MET-04 | Tool shall record build wall-clock time, CPU time (user + system), and GC pauses (Node.js `--trace-gc` parsing) | Must | GC pause data stored as array of {timestamp, duration_ms, heap_before, heap_after} |
| FR-MET-05 | Tool shall attach metadata: OS name/version, architecture, SDK version, project identifier, tool version, timestamp (ISO 8601, UTC, with milliseconds), run ID (UUIDv4) | Must | Metadata block included in every output record |

### 2.4 SDK Management

| Req ID | Requirement | Priority | Acceptance Note |
|--------|-------------|----------|-----------------|
| FR-SDK-01 | Tool shall maintain an SDK registry at `~/.deveco-measurer/sdks/` | Must | Each version in isolated subdirectory |
| FR-SDK-02 | Tool shall download and extract SDK archives from configurable mirror URLs | Must | SHA-256 checksum verification mandatory |
| FR-SDK-03 | Tool shall generate environment configuration files (`.env`) per SDK version | Must | Includes `OHOS_SDK_HOME`, `PATH` amendments, version-specific vars |
| FR-SDK-04 | Tool shall validate SDK compatibility with project `hvigor` version via dry-run before metric collection | Should | Incompatibility logged as warning, run proceeds unless `--strict-sdk` set |
| FR-SDK-05 | Tool shall support offline SDK registration from local archives | Should | `sdk install --from-file <path>` |

### 2.5 Data Export

| Req ID | Requirement | Priority | Acceptance Note |
|--------|-------------|----------|-----------------|
| FR-EXP-01 | Tool shall store raw samples and aggregates in an internal SQLite database by default | Must | DB location: `~/.deveco-measurer/data/metrics.db` |
| FR-EXP-02 | Tool shall export to JSON (array of records), CSV (header + rows), or direct SQL INSERT scripts | Must | `export --format json\|csv\|sql --output <path>` |
| FR-EXP-03 | Tool shall support direct push to external databases via connection string (PostgreSQL, MySQL) | Should | `export --db-url postgresql://...` |
| FR-EXP-04 | Exported data shall include schema version identifier | Must | Field: `schema_version` (semver) |
| FR-EXP-05 | Tool shall support filtering exports by: date range, SDK version, project, OS, run ID | Should | Combinable filters |

---

## 3. Non-Functional Requirements

### 3.1 Measurement Accuracy

| Req ID | Requirement | Target | Verification |
|--------|-------------|--------|--------------|
| NFR-ACC-01 | Monitoring overhead on build wall-clock time | ≤3% delta vs. uninstrumented run | Baseline comparison over 10 identical runs |
| NFR-ACC-02 | Metric reproducibility (±variance) under identical conditions | ±5% for p50/p90, ±8% for p99 | 5 consecutive runs, same project/SDK/OS |
| NFR-ACC-03 | Timestamp accuracy | ±10ms from system clock | Validated against `date +%s%N` |

### 3.2 Idempotency

| Req ID | Requirement | Behavior |
|--------|-------------|----------|
| NFR-IDM-01 | Re-running `deveco-measurer run` with identical parameters shall produce independent result sets | Each run generates unique `run_id`; no data overwrite |
| NFR-IDM-02 | SDK installation shall be idempotent | Re-installing existing version verifies checksums, skips download |
| NFR-IDM-03 | Export operations shall not mutate source database | Exports are read-only snapshots |

### 3.3 Timeouts & Retries

| Req ID | Requirement | Default | Configurable |
|--------|-------------|---------|--------------|
| NFR-TO-01 | Build execution timeout | 3600s | `--build-timeout <seconds>` |
| NFR-TO-02 | SDK download timeout | 600s per file | `--sdk-download-timeout <seconds>` |
| NFR-TO-03 | Metric sampling timeout (stale process detection) | 30s without data | Internal; triggers partial-result flush |
| NFR-RT-01 | Retry count on transient hvigor failure (exit code ≠ 0, ≠ timeout) | 0 (fail fast) | `--retries <n>` (max 3) |
| NFR-RT-02 | Retry backoff strategy | Fixed 5s delay | Not configurable in v1.0 |

### 3.4 Host Load

| Req ID | Requirement | Limit |
|--------|-------------|-------|
| NFR-HL-01 | CPU overhead of metric collector | ≤2% of single core |
| NFR-HL-02 | Memory overhead of metric collector | ≤50 MB RSS |
| NFR-HL-03 | Disk I/O impact (sampling writes) | Buffered; flush ≤1 MB per run |

### 3.5 Cross-Platform Support

| Req ID | Requirement | Platforms |
|--------|-------------|-----------|
| NFR-CP-01 | Supported OS | Windows 10/11 (x86_64), Ubuntu 20.04–24.04 (x86_64, aarch64) |
| NFR-CP-02 | Runtime | Node.js ≥18.0 LTS or Python ≥3.10 (implementation-dependent) |
| NFR-CP-03 | No native compilation required at install time | Pre-built binaries or pure managed-runtime dependencies |
| NFR-CP-04 | Path separators, env-var syntax, signal handling abstracted | Unified internal API |

---

## 4. Measurement Methodology: Time & Memory

### 4.1 Process Tree Coverage

1. **Root Process Identification:** Upon spawning `hvigor`, the tool records the root PID.
2. **Recursive Discovery:** At each sampling interval, the tool enumerates all direct and transitive child PIDs:
   - **Linux:** Parse `/proc/<pid>/stat` for `ppid`; build tree via reverse mapping.
   - **Windows:** Use `NtQuerySystemInformation(SystemProcessInformation)` or WMI `Win32_Process` to construct parent-child relationships. Job Object assignment recommended if `hvigor` supports it.
3. **Lifecycle Tracking:** Processes appearing/disappearing between samples are tracked with `start_time` and `end_time`. Metrics are interpolated for partial lifetimes.
4. **Exclusions:** System processes (PID < 100 on Linux, `System`/`Idle` on Windows) are excluded from aggregation.

### 4.2 Sampling Frequency

| Phase | Interval | Rationale |
|-------|----------|-----------|
| Default | 250ms | Balances accuracy (captures short-lived workers) vs. overhead |
| Configurable Range | 100ms – 1000ms | User-tunable via `--sample-interval-ms` |
| GC Trace Parsing | Event-driven (not sampled) | Node `--trace-gc` output parsed line-by-line |

### 4.3 Node.js GC Pause Accounting

- `hvigor` shall be invoked with `NODE_OPTIONS="--trace-gc --trace-gc-ignore-scavenger"`.
- GC events parsed from stderr; each pause yields: `{phase: "GC", timestamp_us, duration_us, heap_type, bytes_before, bytes_after}`.
- GC pauses are **subtracted** from effective CPU utilization metrics but **included** in wall-clock time.
- Aggregate GC stats: total pause time, pause count, max pause, p50/p95 pause duration.

### 4.4 Metric Aggregation

For each process and each metric (RSS, PSS, USS, CPU_user, CPU_sys):

| Aggregate | Formula |
|-----------|---------|
| `min` | Minimum sample value |
| `max` | Maximum sample value |
| `mean` | Arithmetic mean of all samples |
| `p50`, `p90`, `p95`, `p99` | Percentiles via linear interpolation (nearest-rank method) |
| `sum` | Σ (value × interval_duration) — approximates byte-seconds for memory, cpu-seconds for CPU |
| `peak` | Alias for `max`; used for OOM risk assessment |

**Tree Aggregate:** Sum of per-process aggregates for all processes alive during overlapping intervals. Memory peak is **not** the sum of individual peaks (they may not coincide); instead, compute `max(t) Σ memory_i(t)` across synchronized sample timestamps.

### 4.5 Valid Run Criteria

A run is considered **valid** if and only if:

1. Build process completed (exit code 0) or failed with captured error (non-zero).
2. ≥80% of expected samples were collected (≤20% gap tolerance).
3. Process tree was successfully rooted at `hvigor` PID (orphaned runs are invalid).
4. Metadata block is complete (all required fields present).
5. No timeout or external kill signal interrupted the run (unless explicitly testing timeout behavior).

Invalid runs are flagged in output with `status: "INVALID"` and a reason code but are **not discarded** from storage (audit trail).

---

## 5. Cross-Platform Metric Specifics

### 5.1 Metric Availability Matrix

| Metric | Linux (Ubuntu) | Windows 10/11 | Notes |
|--------|----------------|---------------|-------|
| **RSS** (Resident Set Size) | ✅ `/proc/<pid>/statm` × page_size | ✅ `GetProcessMemoryInfo().WorkingSetSize` | Direct mapping; comparable |
| **PSS** (Proportional Set Size) | ✅ `/proc/<pid>/smaps` — Σ (`Shared / share_count`) | ⚠️ Approximated | See §5.2 |
| **USS** (Unique Set Size) | ✅ `/proc/<pid>/smaps` — `Private_*` lines | ⚠️ Approximated | See §5.2 |
| **CPU User Time** | ✅ `/proc/<pid>/stat` (utime) | ✅ `GetProcessTimes()` | Microsecond precision |
| **CPU System Time** | ✅ `/proc/<pid>/stat` (stime) | ✅ `GetProcessTimes()` | Microsecond precision |
| **GC Pauses** | ✅ Node `--trace-gc` | ✅ Node `--trace-gc` | OS-independent |
| **Wall-Clock Time** | ✅ `hrtime()` / `perf_counter()` | ✅ `hrtime()` / `perf_counter()` | OS-independent |

### 5.2 Windows PSS/USS Approximation Strategy

Windows does not expose per-page sharing semantics required for exact PSS/USS. The tool shall implement the following approximation:

| Metric | Approximation Method | Source API | Expected Error |
|--------|---------------------|------------|----------------|
| **PSS_approx** | `Private Bytes` + (`Working Set Size` − `Private Bytes`) / `N_shared_processes` | `GetProcessMemoryInfo()`, `psutil.Process().memory_info()`, `EnumProcesses()` | ±5–7% vs. true PSS (validated on Linux baseline) |
| **USS_approx** | `Private Bytes` (from `PROCESS_MEMORY_COUNTERS_EX`) | `GetProcessMemoryInfo()` | ±3–5%; excludes shared pages entirely (conservative) |

**Mitigations:**
- Document approximation error bounds in all reports targeting Windows.
- Provide `--metric-mode strict|approximated` flag; `strict` excludes PSS/USS on Windows (emits `null`), `approximated` uses formulas above.
- Cross-validate on dual-boot systems with identical projects; publish delta in release notes.

### 5.3 Platform-Specific Limitations

| Limitation | Platform | Impact | Workaround |
|------------|----------|--------|------------|
| `/proc/<pid>/smaps` requires `ptrace`-equivalent permissions on hardened kernels | Linux | May return 0 for shared fields | Run as user owning processes; note in warnings |
| Job Objects not enforced by `hvigor` | Windows | Child processes may escape tracking | Recommend `--use-job-object` flag (requires project support) |
| High-frequency sampling increases context-switch overhead | Both | May inflate build time >3% overhead | Use adaptive interval; warn if overhead exceeds threshold |
| Antivirus/Defender scan hooks | Windows | Spurious I/O delays inflate metrics | Add exclusion for project build directories |

---

## 6. OHOS SDK Version Management

### 6.1 SDK Isolation Architecture

```
~/.deveco-measurer/
└── sdks/
    ├── 5.0.3.900/
    │   ├── sdk/            # Extracted SDK tree
    │   ├── metadata.json   # {version, checksum, install_date, source_url}
    │   └── .env            # Environment vars for this version
    ├── 6.0.0.100/
    │   ├── sdk/
    │   ├── metadata.json
    │   └── .env
    └── registry.json       # {installed_versions, active_version}
```

### 6.2 Switching Mechanism

1. **Selection:** `deveco-measurer sdk use <version>` updates `registry.json` → `active_version`.
2. **Environment Resolution:** Before each build, the tool sources the `.env` file of the active SDK version and merges with the runtime environment.
3. **No Project Modification:** SDK paths are injected via environment variables (`OHOS_SDK_HOME`, `PATH`, `NODE_PATH`), **not** by rewriting `hvigor` config files or `build-profile.json5`.

### 6.3 Validation & Compatibility

| Check | Method | Failure Action |
|-------|--------|----------------|
| SDK integrity | SHA-256 of `metadata.json` + critical binaries | Flag as corrupted; block runs unless `--force` |
| hvigor ↔ SDK compatibility | `hvigor --version` + SDK `build-tools` presence | Warning; proceed unless `--strict-sdk` |
| Disk space | Check ≥2× SDK size free | Abort install with message |
| Conflicting SDK env | Detect stale `OHOS_SDK_HOME` from external sources | Warn and override |

### 6.4 Concurrent SDK Versions

- Multiple versions coexist in `sdks/`; only one is `active` at a time.
- `deveco-measurer run --sdk-version <ver>` temporarily overrides active version for a single run without mutating registry.
- SDK garbage collection: `sdk prune` removes versions not used in ≥30 days (configurable).

---

## 7. Data Schema and Storage Format

### 7.1 Internal Storage (SQLite)

**Database:** `~/.deveco-measurer/data/metrics.db`  
**Schema Version:** `1.0.0`

#### Tables

```sql
CREATE TABLE runs (
    run_id          TEXT PRIMARY KEY,       -- UUIDv4
    schema_version  TEXT NOT NULL,          -- Semver
    tool_version    TEXT NOT NULL,
    timestamp_start TEXT NOT NULL,          -- ISO 8601 UTC, with milliseconds
    timestamp_end   TEXT NOT NULL,
    status          TEXT NOT NULL,          -- SUCCESS | FAILED | INVALID | TIMEOUT
    os_name         TEXT NOT NULL,
    os_version      TEXT NOT NULL,
    arch            TEXT NOT NULL,
    sdk_version     TEXT NOT NULL,
    project_id      TEXT NOT NULL,          -- User-defined or derived from path hash
    build_target    TEXT NOT NULL,
    build_exit_code INTEGER,
    metadata        TEXT,                   -- JSON blob (env, git sha, etc.)
    overhead_pct    REAL                    -- Monitoring overhead estimate
);

CREATE TABLE processes (
    process_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    pid             INTEGER NOT NULL,
    ppid            INTEGER,
    executable      TEXT NOT NULL,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE samples (
    sample_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    process_id      INTEGER NOT NULL REFERENCES processes(process_id),
    timestamp       TEXT NOT NULL,
    rss_bytes       INTEGER,
    pss_bytes       REAL,                   -- NULL on Windows strict mode
    uss_bytes       REAL,                   -- NULL on Windows strict mode
    cpu_user_us     INTEGER,
    cpu_system_us   INTEGER
);

CREATE TABLE gc_events (
    event_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    timestamp_us    INTEGER NOT NULL,
    duration_us     INTEGER NOT NULL,
    heap_type       TEXT,
    bytes_before    INTEGER,
    bytes_after     INTEGER
);

CREATE TABLE aggregates (
    agg_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(run_id),
    scope           TEXT NOT NULL,          -- 'process:<pid>' | 'tree'
    metric          TEXT NOT NULL,          -- rss, pss, uss, cpu_user, cpu_sys
    min_val         REAL,
    max_val         REAL,
    mean_val        REAL,
    p50_val         REAL,
    p90_val         REAL,
    p95_val         REAL,
    p99_val         REAL,
    sum_val         REAL,
    peak_val        REAL
);
```

### 7.2 JSON Export Format

```json
{
  "schema_version": "1.0.0",
  "export_timestamp": "2026-04-12T14:30:00Z",
  "runs": [
    {
      "run_id": "a1b2c3d4-...",
      "tool_version": "1.0.0",
      "timestamp_start": "2026-04-12T10:00:00.45Z",
      "timestamp_end": "2026-04-12T10:05:23.678Z",
      "status": "SUCCESS",
      "metadata": {
        "os_name": "Linux",
        "os_version": "Ubuntu 22.04.3 LTS",
        "arch": "x86_64",
        "sdk_version": "5.0.3.900",
        "project_id": "my-app",
        "build_target": "assembleDebug",
        "build_exit_code": 0,
        "git_commit": "abc1234",
        "overhead_pct": 1.8
      },
      "build_duration_ms": 323000,
      "cpu_user_ms": 580000,
      "cpu_system_ms": 42000,
      "gc_summary": {
        "total_pause_ms": 1200,
        "pause_count": 15,
        "max_pause_ms": 350,
        "p50_pause_ms": 45,
        "p95_pause_ms": 120
      },
      "tree_aggregates": {
        "rss": {"min": 120000000, "max": 890000000, "mean": 520000000, "p50": 480000000, "p90": 780000000, "p95": 820000000, "p99": 870000000, "peak": 890000000},
        "pss": {"min": 95000000, "max": 620000000, "mean": 380000000, "p50": 350000000, "p90": 560000000, "p95": 590000000, "p99": 610000000, "peak": 620000000},
        "uss": {"min": 60000000, "max": 340000000, "mean": 210000000, "p50": 190000000, "p90": 300000000, "p95": 320000000, "p99": 335000000, "peak": 340000000}
      },
      "processes": [
        {
          "pid": 12345,
          "ppid": 12340,
          "executable": "node",
          "aggregates": { ... }
        }
      ]
    }
  ]
}
```

### 7.3 CSV Export Format

| run_id | timestamp_start | os_name | sdk_version | project_id | build_target | status | build_duration_ms | tree_rss_peak | tree_pss_peak | tree_uss_peak | gc_total_pause_ms | schema_version |
|--------|-----------------|---------|-------------|------------|--------------|--------|-------------------|---------------|---------------|---------------|-------------------|----------------|
| a1b2... | 2026-04-12T10:00:00Z | Linux | 5.0.3.900 | my-app | assembleDebug | SUCCESS | 323000 | 890000000 | 620000000 | 340000000 | 1200 | 1.0.0 |

### 7.4 Dataset Versioning

- Schema changes follow **semantic versioning**: `MAJOR` for breaking changes (column removal/rename), `MINOR` for additive changes, `PATCH` for corrections.
- Exports include `schema_version`; importers must check compatibility.
- Migration scripts provided for schema upgrades (e.g., `migrate --from 1.0.0 --to 1.1.0`).

---

## 8. Failure Handling and Validation

### 8.1 Build Failure Scenarios

| Scenario | Detection | Response |
|----------|-----------|----------|
| `hvigor` exits non-zero | Exit code ≠ 0 | Capture stderr/stdout; mark run `FAILED`; retry if `--retries > 0` |
| Build timeout | Wall-clock exceeds `--build-timeout` | SIGTERM → 10s grace → SIGKILL; mark `TIMEOUT`; flush partial metrics |
| Metric collector crash | Sampling thread dies | Attempt restart; if unrecoverable, flush collected samples; mark `INVALID` with reason |
| Orphaned processes | Root PID exits but children persist | Warn; optionally kill subtree (`--kill-orphans`); close run |
| Disk full during sampling | I/O error on DB write | Abort run; log critical; do not corrupt DB |

### 8.2 Logging

| Level | Use Case |
|-------|----------|
| `ERROR` | Unrecoverable failures (SDK corruption, DB corruption, permission denied) |
| `WARN` | Approximations used, missing metrics, retries, timeout warnings |
| `INFO` | Run start/end, SDK switch, export completion |
| `DEBUG` | Per-sample values, process tree enumeration, env-var dumps |
| `TRACE` | Raw `/proc` or WinAPI responses (implementation-level) |

Logs written to stderr (human-readable) and `~/.deveco-measurer/logs/` (JSON lines, machine-parseable).

### 8.3 Metric Integrity Checks

| Check | Criteria | Action on Failure |
|-------|----------|-------------------|
| Completeness | ≥80% samples present | Flag as `INVALID`; reason: `SAMPLE_GAP` |
| Monotonicity | CPU time samples non-decreasing | Warn; clamp if violated (clock skew) |
| Range | RSS/PSS/USS > 0 and < physical RAM | Flag as `INVALID`; reason: `METRIC_OUT_OF_RANGE` |
| Root PID validity | Root process executable matches `hvigor` | Flag as `INVALID`; reason: `ROOT_MISMATCH` |
| Timestamp consistency | `timestamp_end` ≥ `timestamp_start` | Flag as `INVALID`; reason: `TS_INVERSION` |

### 8.4 Graceful Degradation

If a subset of metrics is unavailable (e.g., PSS on Windows in strict mode, GC trace parsing failure):

1. Emit `null` for missing fields.
2. Log warning with metric name and reason.
3. Complete the run with partial data; do **not** abort.
4. Report includes `metric_completeness_pct` field.

---

## 9. Assumptions, Constraints & Trade-offs

### 9.1 Hardware Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16+ GB |
| Disk (free) | 5 GB (SDK + DB) | 20 GB |
| Network | Required for SDK download | Proxy-configurable |

### 9.2 Monitoring Impact

| Concern | Mitigation |
|---------|------------|
| Sampling overhead inflates build time | Adaptive interval; overhead measurement reported in metadata; target ≤3% |
| Buffering delays metric visibility | Near-real-time flush to SQLite (≤1s lag) |
| Large process trees (>100 nodes) | Sampling time increases; warn if tree depth > 5 |

### 9.3 OS Limitations

| Limitation | Platform | Trade-off |
|------------|----------|-----------|
| No native PSS/USS | Windows | Approximation with documented ±5–7% error; `strict` mode omits fields |
| Process enumeration race conditions | Both | Missed short-lived processes (<sampling interval) not captured; acceptable per §4.2 |
| Permission restrictions (sandboxed builds) | Linux | May require `CAP_SYS_PTRACE` or matching UID; tool warns and proceeds |
| Antivirus interference | Windows | I/O hooks may add 2–5% to build times; document in reports |

### 9.4 Design Trade-offs

| Decision | Alternative | Chosen Approach | Rationale |
|----------|-------------|-----------------|-----------|
| Sampling vs. instrumentation | eBPF, ETW tracing | Sampling (250ms default) | Cross-platform, lower complexity, no kernel dependencies |
| SQLite vs. embedded TSDB | InfluxDB, Prometheus | SQLite | Zero-config, portable, sufficient for single-host runs |
| CLI-only vs. GUI | Web dashboard | CLI + export | Fits CI/CD pipelines; visualization deferred to consumers |
| Node.js vs. Python runtime | Either | Implementation-agnostic (specifies API contract) | Allows team discretion; requirements valid for either |

---

## 10. Acceptance Criteria and Validation Plan

### 10.1 Unit Test Scenarios

| Component | Test Cases | Pass Criteria |
|-----------|-----------|---------------|
| Process tree builder | Known PID hierarchy; orphan detection; rapid spawn/exit | 100% tree reconstruction accuracy |
| Metric sampler | Mock `/proc` and WinAPI responses; missing fields | Correct values; graceful `null` emission |
| GC event parser | Sample `--trace-gc` output; malformed lines | Parsed events match known counts/durations |
| SDK manager | Install, switch, validate, corrupt SDK | Correct env resolution; integrity checks trigger |
| Aggregation engine | Synthetic sample series; edge cases (1 sample, gaps) | Percentiles within ±1% of reference (NumPy/R) |
| Export module | JSON/CSV/SQL output; schema version mismatch | Valid syntax; correct filtering; version check |
| Timeout handler | Simulated long build; SIGTERM delivery | Process killed within 10s grace; partial metrics flushed |

### 10.2 Integration Scenarios

| Scenario | Steps | Expected Result |
|----------|-------|-----------------|
| **End-to-end run (Linux)** | `deveco-measurer run --project samples/app1 --sdk-version 5.0.3.900` | Run completes; JSON/DB output with all fields; overhead ≤3% |
| **End-to-end run (Windows)** | Same as above on Win11 | Run completes; PSS/USS approximated or `null` (strict mode); warning logged |
| **SDK matrix validation** | Loop over 3 SDK versions on same project | 3 independent runs; metadata reflects correct SDK; reproducible within ±5% |
| **CI headless execution** | GitHub Actions workflow with tool install + run | Exit 0 on success; artifacts uploaded; no interactive prompts |
| **Retry on failure** | Inject flaky build (fails 1/3 times); `--retries 2` | Run succeeds by attempt 2 or 3; retry count in metadata |
| **Export & re-import** | Export to JSON, import to fresh DB | Data round-trips without loss; schema version preserved |

### 10.3 Baseline & Reproducibility

| Test | Procedure | Acceptance Threshold |
|------|-----------|----------------------|
| **Reproducibility** | 5 consecutive runs, identical project/SDK/OS, `--skip-clean` disabled | p50/p90 metrics within ±5%; p99 within ±8% |
| **Overhead measurement** | Compare wall-clock: (a) `hvigor` alone, (b) via `deveco-measurer` | Delta ≤3% (mean over 10 runs) |
| **Cross-platform parity** | Same project on Linux + Windows; compare RSS (closest analog) | Delta within ±15% (accounts for OS/loader differences) |
| **Long-run stability** | 50 runs over 24 hours on CI runner | No memory leaks in collector; DB size growth linear; 0 crashes |

### 10.4 Validation Checklist

| # | Criterion | Verified By | Status |
|---|-----------|-------------|--------|
| AC-01 | CLI subcommands functional | Integration tests | ☐ |
| AC-02 | Process tree coverage ≥95% | Synthetic workload + `/proc` audit | ☐ |
| AC-03 | Memory metric accuracy (Linux) | Cross-check with `smem -p <pid>` | ☐ |
| AC-04 | Memory metric accuracy (Windows) | Cross-check with Process Explorer | ☐ |
| AC-05 | GC pause capture | Compare with Node `--trace-gc` raw log | ☐ |
| AC-06 | SDK switching without project edits | Manual verification + env dump | ☐ |
| AC-07 | Export schema compliance | JSON Schema / CSV header validation | ☐ |
| AC-08 | Timeout & retry behavior | Fault injection tests | ☐ |
| AC-09 | Monitoring overhead ≤3% | Baseline comparison (10 runs) | ☐ |
| AC-10 | Reproducibility ±5% (p50/p90) | 5-run variance analysis | ☐ |
| AC-11 | Idempotent SDK installs | Re-run `sdk install`; verify no-op | ☐ |
| AC-12 | Invalid run flagging | Kill build mid-run; check status field | ☐ |

---

## A. Glossary

| Term | Definition |
|------|------------|
| **hvigor** | Node.js-based build system for HarmonyOS projects, analogous to Gradle in Android |
| **RSS** | Resident Set Size — total physical memory pages held in RAM by a process |
| **PSS** | Proportional Set Size — RSS adjusted by dividing shared pages by number of processes sharing them |
| **USS** | Unique Set Size — memory pages exclusive to a process (not shared with any other) |
| **OHOS SDK** | OpenHarmony/HarmonyOS Software Development Kit |
| **DevEco Studio** | JetBrains-based IDE for HarmonyOS application development |
| **Job Object** | Windows kernel object for grouping and managing processes as a unit |
| **ETW** | Event Tracing for Windows — kernel-level event logging facility |
| **OOM** | Out-Of-Memory — process termination due to memory exhaustion |
| **p50/p90/p95/p99** | Percentiles — value below which 50%/90%/95%/99% of observations fall |

## B. Reference Documents

| Document | Purpose |
|----------|---------|
| `PROBLEM_STATEMENT.md` | Business case and stakeholder alignment |
| `ARCHITECTURE.md` (TBD) | System design, component diagrams, ADRs |
| IEEE 29148-2018 | Systems and software engineering — Life cycle processes — Requirements engineering |
| Node.js `--trace-gc` documentation | GC event format specification |
| Linux `proc(5)` man page | `/proc/<pid>/smaps` format reference |
| Windows Process Status API | `GetProcessMemoryInfo` and related functions |

## C. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-04-12 | System Engineering & QA Team | Initial draft for review |
