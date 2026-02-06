# Linux Kernel Commit Analyzer

基于 Claude Code Agent 的 AI 驱动 Linux 内核提交分析工具。

## 概述

本项目分析 Linux 内核 git 提交并生成带评分的 JSON 报告。

**技术架构：**
- **Agent Prompt 设计**: Claude Opus 4.5
- **核心脚本开发**: GLM-4.7
- **评分执行**: GLM-4.7
- **擦屁股（Bug 修复）**: Claude Opus 4.5

使用 Claude AI 智能分类提交并在 4 个维度上评分：

- **技术复杂度** (0-40): 代码量、子系统关键性、跨子系统影响
- **影响重要性** (0-30): 类别显著性、稳定版本回传、用户影响、创新性
- **工程质量** (0-20): 评审链、提交消息质量、测试、原子性
- **社区参与** (0-10): 跨组织协作、维护者背书、社区响应

## 快速开始

```bash
# 安装依赖
uv sync

# 初始化/更新 Linux 内核仓库（可选，如果有自己的仓库可跳过）
git submodule update --init --recursive
```

## 一键分析

### 分析所有中国公司（推荐）

```bash
# 分析指定版本范围内的所有中国公司，输出 JSONL
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --max-commits 200
```

### 全面分析（所有版本）

```bash
# 分析所有主要版本（v5.0 到 v6.18）的中国公司
uv run linux_kernel_analyzer.py --chinese-companies --version v5.0..v6.18 --max-commits all
```

生成文件：
- `data/chinese_companies_v6_5__v6_6.jsonl` - 所有提交，每行一个 JSON
- `data/chinese_companies_v6_5__v6_6_summary.json` - 按公司汇总

### 单一公司分析

```bash
# 仅华为
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "@huawei.com" --max-commits 50

# 所有公司
uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "all" --max-commits 100
```

## 参数说明

| 参数 | 描述 | 示例 |
|----------|-------------|---------|
| `--chinese-companies` | 分析所有中国公司（输出 JSONL） | 标志 |
| `--version` | 版本范围（必需） | `v6.5..v6.6` |
| `--company` | 邮箱域名过滤 | `@huawei.com` 或 `all` |
| `--max-commits` | 最大分析提交数 | `50` 或 `all` |
| `--repo` | 内核仓库路径 | `linux-kernel`（默认） |
| `--output-dir` | 输出目录 | `data`（默认） |
| `--workers` | 并行工作进程数 | `3`（默认） |

## 输出文件

### 中国公司模式
```
data/
├── chinese_companies_v6_5__v6_6.jsonl          # 所有提交，每行一个 JSON
└── chinese_companies_v6_5__v6_6_summary.json   # 按公司汇总
```

### 普通模式
```
data/
├── commit_scores_v6_5__v6_6_all.json           # 所有提交
├── commit_scores_v6_5__v6_6_summary.json       # 汇总统计
└── commit_scores_v6_5__v6_6_batch_*.json       # 批次文件（>50 提交时）
```

## AI Agent 分类

`kernel-commit-analyzer` Claude Code agent 将提交分类为：

| 类型 | 类别 |
|------|------------|
| **安全** | `SEC-CVE`, `SEC-VULN`, `SEC-HARDEN`, `SEC-ACCESS`, `SEC-CRYPTO` |
| **缺陷** | `BUG-CRASH`, `BUG-CORRUPT`, `BUG-MEMLEAK`, `BUG-DEADLOCK`, `BUG-RACE`, `BUG-REGRESSION`, `BUG-LOGIC`, `BUG-RESOURCE`, `BUG-COMPAT`, `BUG-PERF-REG` |
| **功能** | `FEAT-DRIVER`, `FEAT-SUBSYS`, `FEAT-HW`, `FEAT-API`, `FEAT-FUNC`, `FEAT-PERF`, `FEAT-POWER`, `FEAT-SCALE`, `FEAT-TEST`, `FEAT-TRACE` |
| **维护** | `MAINT-REFACTOR`, `MAINT-SIMPLIFY`, `MAINT-CLEANUP`, `MAINT-API-MIG`, `MAINT-DEPR`, `MAINT-NAMING`, `MAINT-WARN`, `MAINT-DUP` |
| **琐碎** | `TRIV-TYPO`, `TRIV-WHITESPACE`, `TRIV-COMMENT`, `TRIV-INCLUDE`, `TRIV-COPYRIGHT` |
| **文档** | `DOC-KERNEL`, `DOC-API`, `DOC-KCONFIG`, `DOC-MAINTAINERS`, `DOC-CHANGELOG` |
| **构建** | `BUILD-KCONFIG`, `BUILD-MAKEFILE`, `BUILD-FIX`, `BUILD-CI`, `BUILD-TOOLCHAIN` |
| **设备树** | `DT-BINDING`, `DT-SOURCE`, `DT-FIX` |
| **回传** | `BACK-STABLE`, `BACK-REVERT`, `BACK-MERGE` |

## 检测到的中国公司

华为、阿里巴巴、腾讯、百度、字节跳动、小米、OPPO、vivo、中兴、联想、浪潮、海思、寒武纪、天数智芯、壁仞、龙芯、飞腾、联发科、晨星、移远、兆易创新、赛昉、平头哥、算能、麒麟、统信、深度、龙蜥、蚂蚁集团、京东、魅族、真我。

## 环境要求

- **UV** - Python 包管理器
- **Claude Code CLI** - 用于 AI agent 分析
- **Git** - 访问内核仓库

## 项目结构

```
linux-contributors/
├── .claude/
│   └── agents/
│       └── kernel-commit-analyzer.md    # Claude AI agent 提示词
├── linux-kernel/                        # Git 子模块（可选）
├── linux_kernel_analyzer.py             # 主分析器
├── data/                                # 输出目录
├── pyproject.toml                       # UV 配置
└── README.md                            # 本文件
```

## 历史统计

本项目还包含来自 KPS 数据的历史统计（2019-2025）：

- **总补丁数**: 553,641
- **中国公司**: 40,060 (7.24%)
- **最大贡献者**: 华为 (22,054 个补丁)

参见 `analyze_china.py` 和 `scraper.py` 了解基于 KPS 的分析。

---

## 完整使用说明

### 1. 分析 (Analyze)

分析中国公司在指定版本范围内的所有 commit：

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
- `data/chinese_companies_<version>.jsonl` - 所有 commit 的 JSON 记录（每行一个）
- `data/chinese_companies_<version>_summary.json` - 按公司汇总
- `data/logs/chinese_companies_<version>_<timestamp>.log` - 详细日志
- `data/failed_commits_<version>.json` - 失败的 commit 列表（如有）

**关键参数：**
- `--workers N` - 并行 worker 数，建议 2-3，太高可能导致 API 限流
- `--max-commits N` - 限制 commit 数量，调试时可设为较小值如 `10`

### 2. 修复 (Repair)

当 AI agent 调用失败时，会生成 `data/failed_commits_<version>.json` 文件。使用 `--repair` 重新分析：

```bash
# 修复指定版本的失败 commit
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --repair

# 修复时可指定较少的 workers 避免再次失败
uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --repair --workers 1
```

**工作原理：**
1. 读取 `data/failed_commits_<version>.json` 获取失败的 commit hash 列表
2. 重新调用 AI agent 分析这些 commit
3. 成功的结果会**更新**到原有的 `.jsonl` 文件中
4. 仍然失败的 commit 会再次写入 `failed_commits` 文件

**查看失败原因：**
```bash
# 查看失败 commit 数量和类型
cat data/failed_commits_v6_5_v6_6.json | python -c "import json,sys; d=json.load(sys.stdin); print(f'Total: {len(d)}'); print({c.get(\"error\",\"unknown\") for c in d})"

# 查看日志中的错误详情
grep -i "error\|failed" data/logs/chinese_companies_v6_5_v6_6_*.log
```

**常见失败原因：**
- `JSON_ERROR` - AI agent 返回了非 JSON 格式（如包含 markdown）
- `TIMEOUT` - API 调用超时
- `INCOMPLETE_RESPONSE` - 返回的 JSON 缺少必要字段

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

---

## AI Agent 评分系统

评分系统总分 **0-100 分**，由 4 个独立维度组成：

```
总分 = 技术复杂度 (0-40) + 影响重要性 (0-30) + 工程质量 (0-20) + 社区参与 (0-10)
```

### 1. 技术复杂度 (Technical Complexity, 0-40分)

| 组件 | 分值 | 说明 |
|------|------|------|
| **代码量** (code_volume) | 0-20 | 根据 `files_changed`、`hunks`、`insertions`、`deletions` 评估 |
| **子系统关键性** (subsystem_criticality) | 0-10 | 根据文件路径确定子系统层级 (tier 1-6)，映射到分数 |
| **跨子系统** (cross_subsystem) | 0-10 | 根据涉及的独立子系统数量 |

**代码量评分表：**

| files_changed | hunks | 代码行数 | 分数 | 描述 |
|--------------|-------|----------|------|------|
| 1 | 1 | 1-5 | 1 | 最小 |
| 1-2 | 1-3 | 6-30 | 3 | 微小 |
| 2-4 | 3-8 | 30-100 | 6 | 小 |
| 3-8 | 5-15 | 50-300 | 9 | 中 |
| 5-15 | 10-30 | 150-600 | 12 | 大 |
| 10-30 | 20-60 | 400-1500 | 15 | 很大 |
| 20-50 | 40-100 | 1000-5000 | 18 | 重大 |
| 50+ | 100+ | 5000+ | 20 | 巨大 |

**子系统层级 (Tier) → 关键性分数：**

| Tier | 子系统路径 | 分数 |
|------|-----------|------|
| 1 (核心) | `mm/`, `kernel/sched/`, `kernel/locking/`, `fs/` (VFS), `net/core/`, `init/`, `lib/` | 10 |
| 2 (关键) | `kernel/bpf/`, `kernel/trace/`, `net/` 协议, `fs/*`, `block/`, `security/`, `crypto/` | 8 |
| 3 (重要) | `drivers/gpu/drm/`, `drivers/net/`, `drivers/scsi/`, `sound/`, `arch/` | 6 |
| 4 (标准) | 其他 `drivers/*`, `tools/`, `samples/` | 4 |
| 5 (边缘) | `Documentation/devicetree/`, `.dts`, `MAINTAINERS` | 2 |
| 6 (琐碎) | `Documentation/`, 纯注释, 空格 | 1 |

**跨子系统分数：** 1个(0分) → 2个(3分) → 3个(5分) → 4个(7分) → 5+(10分)

---

### 2. 影响重要性 (Impact & Importance, 0-30分)

| 组件 | 分值 | 说明 |
|------|------|------|
| **类别基础分** (category_base) | 0-15 | 根据提交类别确定 |
| **稳定/LTS** (stable_lts) | 0-5 | 是否有 `Cc: stable` 标记 |
| **用户影响** (user_impact) | 0-5 | 影响用户范围 |
| **创新性** (novelty) | 0-5 | 新功能/平台的创新程度 |

**类别基础分 (category_base)：**

| 分数 | 类别 |
|------|------|
| 15 | SEC-CVE |
| 13 | SEC-VULN, BUG-CRASH, BUG-CORRUPT |
| 12 | FEAT-SUBSYS, FEAT-DRIVER |
| 11 | SEC-HARDEN, BUG-DEADLOCK, BUG-RACE |
| 10 | FEAT-API, FEAT-FUNC, FEAT-PERF, FEAT-SCALE |
| 9 | BUG-REGRESSION, BUG-LOGIC, BUG-RESOURCE |
| 8 | FEAT-HW, FEAT-POWER |
| 7 | MAINT-REFACTOR, MAINT-SIMPLIFY |
| 6 | BUILD-FIX, DT-FIX |
| 5 | MAINT-CLEANUP, BUILD-KCONFIG |
| 4 | DOC-API, DT-BINDING |
| 3 | MAINT-WARN, BACK-REVERT |
| 2 | TRIV-COMMENT, BACK-STABLE |
| 0 | TRIV-TYPO, TRIV-WHITESPACE |

---

### 3. 工程质量 (Engineering Quality, 0-20分)

| 组件 | 分值 | 说明 |
|------|------|------|
| **评审链** (review_chain) | 0-8 | Reviewed-by/Acked-by/Tested-by 标签数量和多样性 |
| **消息质量** (message_quality) | 0-6 | 提交消息格式完整性 |
| **测试** (testing) | 0-4 | 是否有测试证据 |
| **原子性** (atomicity) | 0-2 | 单一逻辑变更 |

**评审链分数：** 4+跨公司评审者(8分) → 3个(6分) → 2个(4分) → 1个(3分) → 只有Signed-off-by(1分) → 只有自己(0分)

**消息质量** (每项 +1 分，最多 6 分)：
- 标题行 ≤75 字符，使用祈使语气，有子系统前缀
- 正文解释**为什么**（不只是什么）
- 正文引用具体症状、错误信息或用户报告
- 包含 `Fixes:` 标签
- 包含 `Link:` 指向 bug 报告或讨论
- 包含 `Reported-by:`

**测试分数：** 非作者 `Tested-by:`(2分) + 添加测试用例(2分) = 4分

---

### 4. 社区参与 (Community Engagement, 0-10分)

| 组件 | 分值 | 说明 |
|------|------|------|
| **跨组织** (cross_org) | 0-4 | 作者和提交者是否来自不同公司 |
| **维护者级别** (maintainer) | 0-3 | 提交者是否为 kernel.org 维护者 |
| **外部响应** (response) | 0-3 | 是否响应外部 bug 报告 |

**跨组织分数：** 不同公司+3+组织(4分) → 不同公司+2组织(3分) → 不同公司(2分) → 同公司但标准树(1分) → 自提交(0分)

**维护者分数：** `@kernel.org`(3分) → 不同组织(2分) → 不同人(1分) → 自提交(0分)

**外部响应分数：** 外部报告+测试(3分) → 外部报告(2分) → 修复已知bug(1分) → 主动变更(0分)

---

### 反游戏机制 (Anti-Gaming Measures)

**琐碎提交上限 (TRIV-*)**：当主类别是任何 TRIV-* 类型时，所有组件分数单独封顶，**最高总分 5 分**

**低投入维护上限 (MAINT-WARN, MAINT-NAMING)**：**最高总分 23 分**

---

### 评分基准示例

| 类型 | 预计分数 |
|------|---------|
| 拼写错误修正 (TRIV-TYPO) | ~3-5 |
| 警告修复 (MAINT-WARN) | ~15-18 |
| 简单 Bug 修复 (BUG-CRASH) | ~41-45 |
| 重要新功能 (FEAT-API) | ~68-72 |
| 关键 CVE 修复 (SEC-CVE) | ~81-84 |

**核心思想**：多维度评分防止投机 —— 一个提交 1000 个拼写错误修正的人会有很高的代码量分数，但技术复杂度和影响力分数接近于零。

---

## License

MIT License
