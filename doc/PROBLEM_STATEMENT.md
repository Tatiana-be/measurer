# PROBLEM_STATEMENT.md

## 1. Problem Statement
The `hvigor` build system (Node.js-based, HarmonyOS/DevEco Studio) lacks a standardized, automated mechanism for collecting reproducible, cross-platform performance benchmarks. Current profiling approaches are manual, environment-dependent, and introduce uncontrolled overhead, making it impossible to:
- Objectively evaluate build duration and memory consumption across multiple OHOS SDK versions.
- Establish reliable CI/CD quality gates for build regressions or toolchain upgrades.
- Compare memory (RSS/PSS/USS) and CPU utilization consistently across Windows and Ubuntu.
- Track Node.js GC impact and full process-tree resource consumption at scale.
- Maintain auditable, versioned datasets for long-term trend analysis and engineering reviews.

## 2. Business Case & Value Proposition
**Why it matters:** Build performance directly impacts developer productivity, CI/CD pipeline throughput, and SDK release velocity. Without deterministic, low-overhead metrics, engineering teams cannot confidently upgrade SDKs, optimize build scripts, or enforce performance budgets in automated workflows.

**Value delivered:**
- **Data-Driven Optimization:** Provides immutable, versioned datasets to identify bottlenecks (CPU, memory, GC) before they impact developers.
- **CI/CD Automation:** Enables headless, machine-readable performance gates (exit codes `0/1/2`, structured logs, JSON/CSV/SQL export) compatible with GitHub Actions, GitLab CI, and Jenkins.
- **Cross-Platform Parity:** Unified sampling methodology across Windows 10/11 and Ubuntu 20.04–24.04 ensures benchmarks are comparable regardless of host OS.
- **Zero-Intrusion Design:** Operates strictly as an external observer—no patches to `hvigor`, DevEco Studio, or project configs—preserving upstream integrity and reducing maintenance debt.
- **SDK Lifecycle Safety:** Isolates, verifies, and switches between ≥3 OHOS SDK versions without modifying project files, enabling safe matrix testing and rapid rollback.

## 3. Key Success Metrics (Non-Negotiable)
| Metric | Target | Verification |
|---|---|---|
| Monitoring Overhead | ≤3% wall-clock delta vs uninstrumented baseline | 10-run baseline comparison (NFR-ACC-01) |
| Reproducibility | ±5% (p50/p90), ±8% (p99) | 5 consecutive identical runs (NFR-ACC-02) |
| Collector Resource Usage | ≤2% single-core CPU, ≤50 MB RSS | Self-monitoring telemetry (NFR-HL-01/02) |
| CI/CD Compatibility | Headless, structured stderr, exit codes 0/1/2 | GitHub Actions / GitLab CI / Jenkins pipelines |
| Data Integrity | Append-only, SQLite WAL, atomic commits, `schema_version` on all records | Round-trip export→import validation (NFR-IDM-01/03) |

## 4. Scope & Boundaries
**In-Scope:** 
- CLI orchestration (`run`, `schedule`, `sdk`, `export`, `report`)
- Process-tree metric sampling (default 250ms, configurable 100–1000ms)
- SDK version management, integrity verification, and `.env` isolation
- Structured export (JSON/CSV/SQL, optional PostgreSQL/MySQL push)
- CI/CD headless integration & machine-readable logging
- Self-telemetry (overhead %, sample gaps, collector resource usage)

**Out-of-Scope:**
- Modification of `hvigor`/DevEco Studio source code or project configs
- IDE/UI or application runtime profiling
- Built-in BI/dashboard (visualization deferred to downstream consumers)
- macOS support (deferred to v1.1+)
- Benchmarking compilers/linkers outside `hvigor` context

**Hard Constraints:** 
- Python ≥3.10, `psutil` ≥6.0.0, SQLite (WAL mode)
- Immutable `RunConfig`; `RunContext` updated only by Orchestrator
- Strict root-PID validation (`hvigorw.js` cmdline match + ±2s spawn correlation)
- Windows PSS approximation documented (±5–7% error) or `null` in `--metric-mode strict`
- All exports & DB records must include `schema_version` (semver)

## 5. Assumptions & Architectural Trade-offs
- `hvigor` is invoked as `node $NODE_OPTIONS <hvigor_path>/bin/hvigorw.js $HVIGOR_OPTIONS`; tool anchors exclusively to this root PID.
- Sampling (100–1000ms) is chosen over eBPF/ETW to guarantee cross-platform simplicity, zero kernel dependencies, and ≤3% overhead (ADR-001).
- SQLite is used over external TSDBs for zero-config portability on single-host CI runners (ADR-002).
- Windows PSS is approximated via `Private + (WorkingSet - Private) / N_shared`; USS is native via `psutil` ≥6.0.0. Cross-platform parity targets ≤15% RSS delta (AC-05).
- Tool measures itself: overhead, sample gaps, DB write latency, and collector resource usage are first-class exported metrics enabling self-validation against NFRs.
