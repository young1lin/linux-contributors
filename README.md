# Linux Kernel Commit Analyzer

AI-powered Linux kernel commit analysis tool using Claude Code agents.

## Overview

This project analyzes Linux kernel git commits and produces scored JSON reports. It uses Claude AI agents to intelligently classify commits and score them across 4 dimensions:

- **Technical** (0-40): Code volume, subsystem criticality, cross-subsystem impact
- **Impact** (0-30): Category significance, stable backports, user impact, novelty
- **Quality** (0-20): Review chain, commit message quality, testing, atomicity
- **Community** (0-10): Cross-org collaboration, maintainer endorsement, community response

## Quick Start

```bash
# Install dependencies
uv sync

# Initialize/update Linux kernel repo (optional if you have your own)
git submodule update --init --recursive
```

## One-Command Analysis

### Analyze All Chinese Companies (Recommended)

```bash
# Analyze all Chinese companies in a version range, output JSONL
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --max-commits 200
```

### Comprehensive Analysis (All Versions)

```bash
# Analyze all Chinese companies across all major versions (v5.0 to v6.18)
uv run linux_kernel_analyzer.py --chinese-companies --version v5.0..v6.18 --max-commits all
```

This produces:
- `data/chinese_companies_v6_5__v6_6.jsonl` - One JSON per line for all commits
- `data/chinese_companies_v6_5__v6_6_summary.json` - Summary by company

### Single Company Analysis

```bash
# Huawei only
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "@huawei.com" --max-commits 50

# All companies
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "all" --max-commits 100
```

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--chinese-companies` | Analyze all Chinese companies (outputs JSONL) | flag |
| `--version` | Version range (required) | `v6.5..v6.6` |
| `--company` | Email domain filter | `@huawei.com` or `all` |
| `--max-commits` | Max commits to analyze | `50` or `all` |
| `--repo` | Kernel repo path | `linux-kernel` (default) |
| `--output-dir` | Output directory | `data` (default) |
| `--workers` | Parallel workers | `3` (default) |

## Output Files

### Chinese Companies Mode
```
data/
├── chinese_companies_v6_5__v6_6.jsonl          # All commits, one JSON per line
└── chinese_companies_v6_5__v6_6_summary.json   # Summary by company
```

### Normal Mode
```
data/
├── commit_scores_v6_5__v6_6_all.json           # All commits
├── commit_scores_v6_5__v6_6_summary.json       # Summary statistics
└── commit_scores_v6_5__v6_6_batch_*.json       # Batches (if >50 commits)
```

## AI Agent Classification

The `kernel-commit-analyzer` Claude Code skill classifies commits into:

| Type | Categories |
|------|------------|
| **Security** | `SEC-CVE`, `SEC-VULN`, `SEC-HARDEN` |
| **Bug** | `BUG-CRASH`, `BUG-RACE`, `BUG-LEAK`, `BUG-CORRUPT`, `BUG-HANG`, `BUG-REGRESSION`, `BUG-OTHER` |
| **Feature** | `FEAT-DRIVER`, `FEAT-HW`, `FEAT-API`, `FEAT-OPT`, `FEAT-OTHER` |
| **Maintenance** | `MAINT-REFACTOR`, `MAINT-CLEANUP`, `MAINT-MODERNIZE` |
| **Trivial** | `TRIV-TYPO`, `TRIV-WHITESPACE`, `TRIV-TRIVIAL` |
| **Other** | `DOC`, `BUILD`, `DT`, `BACK-STABLE`, `BACK-FIXES` |

## Chinese Companies Detected

Huawei, Alibaba, Tencent, Baidu, ByteDance, Xiaomi, OPPO, vivo, ZTE, Lenovo, Inspur, HiSilicon, Cambricon, Iluvatar, Biren, Loongson, Phytium, MediaTek, MStar, Quectel, GigaDevice, StarFive, T-Head, Spacemit, Kylin, UnionTech, Deepin, OpenAnolis, AntGroup, JD, Meizu, Realme.

## Requirements

- **UV** - Python package manager
- **Claude Code CLI** - For AI agent analysis
- **Git** - For accessing kernel repository

## Project Structure

```
linux-contributors/
├── .claude/
│   └── skills/
│       └── kernel-commit-analyzer.md    # Claude AI agent skill
├── linux-kernel/                        # Git submodule (optional)
├── linux_kernel_analyzer.py             # Main analyzer
├── data/                                # Output directory
├── pyproject.toml                       # UV configuration
└── README.md                            # This file
```

## Legacy Statistics

This project also includes historical statistics (2019-2025) from KPS data:

- **Total patches**: 553,641
- **Chinese companies**: 40,060 (7.24%)
- **Top contributor**: Huawei (22,054 patches)

See `analyze_china.py` and `scraper.py` for the KPS-based analysis.



## Complete Usage

### 1. Analyze (分析)

分析中国公司在指定版本范围内的所有commit：

```bash
# 分析单个版本范围
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --max-commits all --workers 3

# 分析所有版本（分批执行，避免超时）
uv run linux_kernel_analyzer.py --chinese-companies --version v5.0..v5.3 --max-commits all --workers 2
uv run linux_kernel_analyzer.py --chinese-companies --version v5.3..v5.10 --max-commits all --workers 2
uv run linux_kernel_analyzer.py --chinese-companies --version v5.10..v6.0 --max-commits all --workers 2
uv run linux_kernel_analyzer.py --chinese-companies --version v6.0..v6.10 --max-commits all --workers 2
uv run linux_kernel_analyzer.py --chinese-companies --version v6.10..v6.18 --max-commits all --workers 2
```

**输出文件：**
- `data/chinese_companies_<version>.jsonl` - 所有commit的JSON记录（每行一个）
- `data/chinese_companies_<version>_summary.json` - 按公司汇总
- `data/logs/chinese_companies_<version>_<timestamp>.log` - 详细日志
- `data/failed_commits_<version>.json` - 失败的commit列表（如有）

**关键参数：**
- `--workers N` - 并行worker数，建议2-3，太高可能导致API限流
- `--max-commits N` - 限制commit数量，调试时可设为较小值如`10`

### 2. Repair (修复失败的commit)

当AI agent调用失败时，会生成 `data/failed_commits_<version>.json` 文件。使用 `--repair` 重新分析：

```bash
# 修复指定版本的失败commit
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --repair

# 修复时可指定较少的workers避免再次失败
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --repair --workers 1
```

**工作原理：**
1. 读取 `data/failed_commits_<version>.json` 获取失败的commit hash列表
2. 重新调用AI agent分析这些commit
3. 成功的结果会**更新**到原有的 `.jsonl` 文件中
4. 仍然失败的commit会再次写入 `failed_commits` 文件

**查看失败原因：**
```bash
# 查看失败commit数量和类型
cat data/failed_commits_v6_5_v6_6.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {len(d)}'); print({c.get(\"error\",\"unknown\") for c in d})"

# 查看日志中的错误详情
grep -i "error\|failed" data/logs/chinese_companies_v6_5_v6_6_*.log
```

**常见失败原因：**
- `JSON_ERROR` - AI agent返回了非JSON格式（如包含markdown）
- `TIMEOUT` - API调用超时
- `INCOMPLETE_RESPONSE` - 返回的JSON缺少必要字段

### 3. 过滤失败记录

在后续分析时，可以过滤掉失败的记录：

```python
import json

with open('data/chinese_companies_v6_5_v6_6.jsonl', 'r') as f:
    commits = [json.loads(line) for line in f if line.strip()]

# 只保留成功的记录（score_total > 0）
successful = [c for c in commits if c['score_total'] > 0]
print(f"成功: {len(successful)}/{len(commits)}")
```

## License

MIT License
