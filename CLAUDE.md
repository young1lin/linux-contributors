# Linux Kernel Commit Analyzer - AI-Powered Analysis

This project uses Claude Code agents to analyze Linux kernel commits and produce scored JSON reports.

## Prerequisites

1. **UV** - Python package manager:
   ```bash
   # Windows (PowerShell)
   irm https://astral.sh/uv/install.ps1 | iex
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Claude Code CLI** - For AI agent analysis:
   ```bash
   npm install -g @anthropic-ai/claude-code
   ```

3. **Linux Kernel Repository** (optional):
   ```bash
   git submodule update --init --recursive
   # Or use your own: --repo /path/to/linux
   ```

## Quick Start

```bash
# Install dependencies
uv sync
```

## One-Command Analysis

### Analyze All Chinese Companies

```bash
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --max-commits 200
```

Output:
- `data/chinese_companies_v6_5__v6_6.jsonl` - All commits, one JSON per line
- `data/chinese_companies_v6_5__v6_6_summary.json` - Summary by company

### Single Company

```bash
# Huawei only
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "@huawei.com" --max-commits 50

# All companies
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "all" --max-commits 100
```

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--chinese-companies` | Analyze all Chinese companies | flag |
| `--version` | Version range (required) | `v6.5..v6.6` |
| `--company` | Email domain filter | `@huawei.com` or `all` |
| `--max-commits` | Max commits | `50` or `all` |
| `--repo` | Kernel repo path | `linux-kernel` |
| `--output-dir` | Output directory | `data` |
| `--workers` | Parallel workers | `3` |

## AI Agent

The tool uses the `.claude/agents/kernel-commit-analyzer.md` agent to analyze commits with Claude AI.

### Classification

- **Security**: SEC-CVE, SEC-VULN, SEC-HARDEN, SEC-ACCESS, SEC-CRYPTO
- **Bug**: BUG-CRASH, BUG-CORRUPT, BUG-MEMLEAK, BUG-DEADLOCK, BUG-RACE, BUG-REGRESSION, BUG-LOGIC, BUG-RESOURCE, BUG-COMPAT, BUG-PERF-REG
- **Feature**: FEAT-DRIVER, FEAT-SUBSYS, FEAT-HW, FEAT-API, FEAT-FUNC, FEAT-PERF, FEAT-POWER, FEAT-SCALE, FEAT-TEST, FEAT-TRACE
- **Maintenance**: MAINT-REFACTOR, MAINT-SIMPLIFY, MAINT-CLEANUP, MAINT-API-MIG, MAINT-DEPR, MAINT-NAMING, MAINT-WARN, MAINT-DUP
- **Trivial**: TRIV-TYPO, TRIV-WHITESPACE, TRIV-COMMENT, TRIV-INCLUDE, TRIV-COPYRIGHT
- **Documentation**: DOC-KERNEL, DOC-API, DOC-KCONFIG, DOC-MAINTAINERS, DOC-CHANGELOG
- **Build**: BUILD-KCONFIG, BUILD-MAKEFILE, BUILD-FIX, BUILD-CI, BUILD-TOOLCHAIN
- **Device Tree**: DT-BINDING, DT-SOURCE, DT-FIX
- **Backport**: BACK-STABLE, BACK-REVERT, BACK-MERGE

### Scoring

| Dimension | Range | Components |
|-----------|-------|------------|
| Technical | 0-40 | Code volume (0-20), Subsystem criticality (0-10), Cross-subsystem (0-10) |
| Impact | 0-30 | Category base (0-15), Stable/LTS (0-5), User impact (0-5), Novelty (0-5) |
| Quality | 0-20 | Review chain (0-8), Message quality (0-6), Testing (0-4), Atomicity (0-2) |
| Community | 0-10 | Cross-org (0-4), Maintainer (0-3), Response (0-3) |

### Subsystem Tier

`subsystem_tier` is an integer 1-6 (1=most critical). Mapped to A2 points: Tier 1→10, 2→8, 3→6, 4→4, 5→2, 6→1.

## Project Structure

```
linux-contributors/
├── .claude/
│   └── agents/
│       └── kernel-commit-analyzer.md    # Claude AI agent prompt
├── linux-kernel/                        # Git submodule
├── linux_kernel_analyzer.py             # Main analyzer (AI-powered)
├── data/                                # Output directory
├── pyproject.toml                       # UV configuration
├── CLAUDE.md                            # This file
└── README.md                            # User documentation
```

## Troubleshooting

### Agent Timeout
If AI agent times out, the tool falls back to basic regex analysis with `flags: ["AGENT_ERROR"]`.

### Claude CLI Not Found
```bash
claude --version
```

### Kernel Repository Not Found
```bash
git submodule update --init --recursive
```

## Legacy Files

- `analyze_china.py` - KPS-based historical analysis (2019-2025)
- `scraper.py` - Web scraper for KPS data
