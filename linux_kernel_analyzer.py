#!/usr/bin/env python3
"""
Linux Kernel Commit Analyzer (AI-Powered)

Analyzes Linux kernel commits using Claude AI agent and produces a scored JSON report.

This analyzer:
1. Retrieves commits from git log with specified filters
2. Gathers diff stats for each commit
3. Uses Claude AI agent to classify and score each commit
4. Outputs detailed JSON reports with parallel processing (3 workers)

Usage:
    # Single company
    uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "@huawei.com" --max-commits 50

    # All companies
    uv run linux_kernel_analyzer.py --version v6.5..v6.6 --company "all" --max-commits 100

    # All Chinese companies (one command, outputs JSONL)
    uv run linux_kernel_analyzer.py --chinese-companies --version v6.5..v6.6 --max-commits 200
"""

import argparse
import json
import re
import subprocess
import sys
import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal
import threading


# ==================== LOGGING SETUP ====================

def setup_logging(output_dir: str, version_range: str, mode: str = "analyze") -> logging.Logger:
    """Setup logging to both file and console."""
    version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    log_dir = Path(output_dir) / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    log_file = log_dir / f"{mode}_{version_tag}_{timestamp}.log"

    # Create logger
    logger = logging.getLogger(f"kernel_analyzer_{timestamp}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()  # Clear any existing handlers

    # File handler - detailed logging
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    fh.setFormatter(fh_formatter)
    logger.addHandler(fh)

    # Console handler - info level only
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch_formatter = logging.Formatter('%(levelname)s: %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    # Log session start
    logger.info("=" * 70)
    logger.info(f"Linux Kernel Commit Analyzer - {mode.upper()} MODE")
    logger.info("=" * 70)
    logger.info(f"Version range: {version_range}")
    logger.info(f"Log file: {log_file}")
    logger.info("")

    return logger


# ==================== SUBSYSTEM TIER CLASSIFICATION ====================

SUBSYSTEM_TIERS = {
    1: ["mm/", "kernel/sched/", "kernel/locking/", "net/core/", "init/", "lib/"],
    2: ["kernel/bpf/", "kernel/trace/", "kernel/", "net/", "fs/", "block/",
        "security/", "crypto/", "ipc/", "virt/kvm/"],
    3: ["drivers/gpu/drm/", "drivers/net/", "drivers/scsi/", "drivers/nvme/",
        "drivers/ata/", "drivers/usb/", "drivers/pci/", "drivers/input/",
        "sound/", "arch/"],
    4: ["drivers/", "tools/", "samples/", "scripts/"],
    5: ["Documentation/devicetree/", "MAINTAINERS", "CREDITS", ".mailmap"],
    6: ["Documentation/"],
}

# Map tier number (1-6) to A2_subsystem_criticality points
TIER_TO_A2_POINTS = {1: 10, 2: 8, 3: 6, 4: 4, 5: 2, 6: 1}


def get_subsystem_tier(files: list[str]) -> int:
    """Determine subsystem tier (1-6) based on files touched. Lower tier = more critical."""
    best_tier = 6  # default to least critical
    for f in files:
        f_lower = f.lower()
        # Check VFS core files specifically (tier 1)
        vfs_core = ["fs/namei.c", "fs/read_write.c", "fs/super.c", "fs/inode.c"]
        if f in vfs_core:
            return 1
        # Check DT source files (tier 5)
        if "/boot/dts/" in f and f.endswith((".dts", ".dtsi")):
            best_tier = min(best_tier, 5)
            continue
        for tier, prefixes in SUBSYSTEM_TIERS.items():
            for prefix in prefixes:
                if f.startswith(prefix) or f_lower.startswith(prefix.lower()):
                    best_tier = min(best_tier, tier)
                    break
    return best_tier


# ==================== CHINESE COMPANIES LIST ====================

CHINESE_COMPANIES = {
    "huawei.com": "Huawei",
    "alibaba.com": "Alibaba", "alibaba-inc.com": "Alibaba", "alipay.com": "Alibaba",
    "tencent.com": "Tencent",
    "baidu.com": "Baidu",
    "bytedance.com": "ByteDance",
    "xiaomi.com": "Xiaomi",
    "oppo.com": "OPPO",
    "vivo.com": "vivo", "zte.com.cn": "ZTE", "zte.com": "ZTE",
    "lenovo.com": "Lenovo",
    "inspur.com": "Inspur",
    "hisilicon.com": "HiSilicon",
    "cambricon.com": "Cambricon",
    "iluvatar.com": "Iluvatar",
    "biren.tech": "Biren",
    "loongson.cn": "Loongson",
    "phytium.com.cn": "Phytium",
    "mediatek.com": "MediaTek",
    "mstar.com": "MStar",
    "quectel.com": "Quectel",
    "gigadevice.com": "GigaDevice",
    "starfivetech.com": "StarFive",
    "thead.cn": "T-Head",
    "spacemit.com": "Spacemit",
    "kylinos.cn": "Kylin",
    "uniontech.com": "UnionTech",
    "deepin.org": "Deepin",
    "openanolis.com": "OpenAnolis",
    "antgroup.com": "AntGroup",
    "jd.com": "JD",
    "meizu.com": "Meizu",
    "realme.com": "Realme",
    "redhat.com.cn": "RedHat China",
    "suse.com": "SUSE",
    "canonical.com": "Canonical",
    "collabora.com": "Collabora",
    "linaro.org": "Linaro",
    "codeaurora.org": "CodeAurora",
    "baylibre.com": "BayLibre",
    "bootlin.com": "Bootlin",
    "amd.com": "AMD", "intel.com": "Intel", "nvidia.com": "NVIDIA",
    "qualcomm.com": "Qualcomm", "arm.com": "ARM", "google.com": "Google",
    "microsoft.com": "Microsoft", "amazon.com": "Amazon", "meta.com": "Meta",
    "apple.com": "Apple", "oracle.com": "Oracle", "ibm.com": "IBM",
    "fujitsu.com": "Fujitsu", "nec.com": "NEC", "renesas.com": "Renesas",
    "toshiba.com": "Toshiba", "synopsys.com": "Synopsys", "broadcom.com": "Broadcom",
    "cavium.com": "Cavium", "marvell.com": "Marvell", "qlogic.com": "QLogic",
    "emc.com": "EMC", "netronome.com": "Netronome", "pensando.io": "Pensando",
    "vmware.com": "VMware", "xilinx.com": "Xilinx", "altera.com": "Altera",
    "lattice.com": "Lattice", "microchip.com": "Microchip", "nxp.com": "NXP",
    "infineon.com": "Infineon", "st.com": "STMicroelectronics",
    "ti.com": "Texas Instruments", "adi.com": "Analog Devices",
    "maxim.com": "Maxim", "linear.com": "Linear", "cirrus.com": "Cirrus",
    "realtek.com": "Realtek", "via.com": "VIA", "rockchip.com": "Rockchip",
    "allwinnertech.com": "Allwinner", "unisoc.com": "Unisoc", "sophgo.com": "Sophgo",
}

# Chinese company domains for filtering
CHINESE_COMPANY_DOMAINS = {
    "huawei.com", "alibaba.com", "alibaba-inc.com", "alipay.com",
    "tencent.com", "baidu.com", "bytedance.com", "xiaomi.com",
    "oppo.com", "vivo.com", "zte.com.cn", "zte.com", "lenovo.com",
    "inspur.com", "hisilicon.com", "cambricon.com", "iluvatar.com",
    "biren.tech", "loongson.cn", "phytium.com.cn", "mediatek.com",
    "mstar.com", "quectel.com", "gigadevice.com", "starfivetech.com",
    "thead.cn", "spacemit.com", "kylinos.cn", "uniontech.com",
    "deepin.org", "openanolis.com", "antgroup.com", "jd.com",
    "meizu.com", "realme.com", "redhat.com.cn",
}


def extract_company(email: str) -> str:
    """Extract company name from email address."""
    domain = email.split("@")[-1].lower().strip()

    for company_domain, company_name in CHINESE_COMPANIES.items():
        if domain == company_domain or domain.endswith("." + company_domain):
            return company_name

    parts = domain.split(".")
    if len(parts) >= 2:
        return parts[-2].capitalize()
    return "Unknown"


def is_chinese_company(email: str) -> bool:
    """Check if email domain belongs to a Chinese company."""
    domain = email.split("@")[-1].lower().strip()
    return any(domain == d or domain.endswith("." + d) for d in CHINESE_COMPANY_DOMAINS)


# ==================== DATA CLASSES ====================

@dataclass
class CommitData:
    """Raw commit data from git."""
    hash: str
    author: str
    author_date: str
    committer: str
    commit_date: str
    subject: str
    body: str
    files: list[str]
    files_changed: int
    insertions: int
    deletions: int
    hunks: int
    diff_output: str


@dataclass
class ScoredCommit:
    """Fully scored commit with AI analysis."""
    commit_hash: str
    short_hash: str
    author_name: str
    author_email: str
    author_company: str
    author_date: str
    committer_name: str
    committer_email: str
    committer_company: str
    commit_date: str
    subject: str
    primary_category: str
    secondary_categories: list[str]
    cve_ids: list[str]
    fixes_tag: str
    cc_stable: bool
    subsystem_prefix: str
    subsystems_touched: list[str]
    subsystem_tier: int
    files_changed: int
    insertions: int
    deletions: int
    hunks: int
    review_chain: dict
    score_total: int
    score_technical: int
    score_impact: int
    score_quality: int
    score_community: int
    score_breakdown: dict
    score_justification: str
    code_snippet: str
    flags: list[str]
    link: str


# ==================== PROGRESS TRACKING ====================

class ProgressCounter:
    def __init__(self, total: int):
        self.total = total
        self.current = 0
        self.lock = threading.Lock()

    def increment(self):
        with self.lock:
            self.current += 1
            return self.current

    def get(self):
        with self.lock:
            return self.current


# ==================== AI AGENT ANALYSIS ====================

def analyze_with_agent(
    commit_data: CommitData,
    repo_path: str,
    logger: logging.Logger | None = None,
    timeout: int = 300,
    max_retries: int = 3,
) -> tuple[dict, str | None]:
    """
    Call Claude CLI with kernel-commit-analyzer agent to analyze a commit.

    Args:
        commit_data: The commit data to analyze
        repo_path: Path to the git repository
        logger: Optional logger instance
        timeout: Timeout in seconds for the agent call (default: 300)
        max_retries: Max retries for 429 rate limit errors (default: 3)

    Returns:
        (analysis_dict, error_type) - error_type is None on success,
        or one of "TIMEOUT", "429_RATE_LIMIT", "JSON_ERROR", "OTHER"
    """
    short_hash = commit_data.hash[:12]
    if logger:
        logger.debug(f"{'='*60}")
        logger.debug(f"Analyzing commit: {short_hash}")
        logger.debug(f"Subject: {commit_data.subject[:80]}...")
        logger.debug(f"Files changed: {commit_data.files_changed}, +{commit_data.insertions}/-{commit_data.deletions}")
    code_snippet = get_code_snippet(repo_path, commit_data.hash, commit_data.files)

    agent_input = {
        "commit_hash": commit_data.hash,
        "short_hash": commit_data.hash[:12],
        "author_name": commit_data.author.split("<")[0].strip(),
        "author_email": commit_data.author.split("<")[-1].split(">")[0].strip() if "<" in commit_data.author else "",
        "author_date": commit_data.author_date,
        "committer_name": commit_data.committer.split("<")[0].strip(),
        "committer_email": commit_data.committer.split("<")[-1].split(">")[0].strip() if "<" in commit_data.committer else "",
        "commit_date": commit_data.commit_date,
        "subject": commit_data.subject,
        "body": commit_data.body,
        "files": commit_data.files,
        "files_changed": commit_data.files_changed,
        "insertions": commit_data.insertions,
        "deletions": commit_data.deletions,
        "hunks": commit_data.hunks,
        "diff_output": commit_data.diff_output[:10000],
        "code_snippet": code_snippet,
    }

    prompt = f"""Analyze this Linux kernel commit and return ONLY a valid JSON object (no markdown, no explanation):

{json.dumps(agent_input, ensure_ascii=False, indent=2)}
"""

    cmd = [
        "claude",
        "-p",
        prompt,
        "--agent",
        "kernel-commit-analyzer",
    ]

    for attempt in range(max_retries):
        try:
            if logger:
                logger.debug(f"Calling Claude CLI agent... (attempt {attempt + 1}/{max_retries})")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**subprocess.os.environ, "NO_COLOR": "1"},
            )

            output = result.stdout.strip()
            stderr = result.stderr.strip()

            if logger and stderr:
                logger.debug(f"stderr: {stderr[:200]}")

            # Check for 429 rate limit error in stderr or output
            if "429" in stderr or "rate limit" in stderr.lower() or "429" in output.lower():
                if attempt < max_retries - 1:
                    # Exponential backoff: 30s, 60s, 120s
                    wait_time = 30 * (2 ** attempt)
                    if logger:
                        logger.warning(f"[429_RATE_LIMIT] {short_hash} - Hit rate limit, waiting {wait_time}s before retry...")
                    print(f"  [429 RATE LIMIT] {short_hash} - Waiting {wait_time}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    if logger:
                        logger.warning(f"[429_RATE_LIMIT] {short_hash} - Hit rate limit, max retries exceeded")
                    print(f"  [429 RATE LIMIT] Max retries exceeded for {short_hash}")
                    return get_fallback_analysis(commit_data, "429_RATE_LIMIT"), "429_RATE_LIMIT"

            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                output = output[json_start:json_end].strip()
            elif "```" in output:
                json_start = output.find("```") + 3
                json_end = output.rfind("```")
                output = output[json_start:json_end].strip()

            if logger:
                logger.debug(f"Parsing agent response...")
            analysis = json.loads(output)

            if logger:
                category = analysis.get("primary_category", "UNKNOWN")
                score_breakdown = analysis.get("score_breakdown", {})
                logger.debug(f"Agent response OK - category: {category}, score_breakdown keys: {list(score_breakdown.keys())}")
                logger.debug(f"Agent response top-level keys: {list(analysis.keys())}")
                # Log first 500 chars of response for debugging
                logger.debug(f"Raw agent output (first 500 chars): {output[:500]}")

            return analysis, None

        except subprocess.TimeoutExpired:
            if logger:
                logger.error(f"[TIMEOUT] {short_hash} - Agent analysis timed out after {timeout}s")
            print(f"  [TIMEOUT] Agent analysis timed out for {short_hash} ({timeout}s)")
            return get_fallback_analysis(commit_data, "TIMEOUT"), "TIMEOUT"
        except json.JSONDecodeError as e:
            if logger:
                logger.error(f"[JSON_ERROR] {short_hash} - Failed to parse JSON: {e}")
            print(f"  [ERROR] Failed to parse JSON from agent: {e}")
            return get_fallback_analysis(commit_data, "JSON_ERROR"), "JSON_ERROR"
        except Exception as e:
            if logger:
                logger.error(f"[ERROR] {short_hash} - Agent analysis failed: {type(e).__name__}: {e}")
            print(f"  [ERROR] Agent analysis failed: {e}")
            return get_fallback_analysis(commit_data, "OTHER"), "OTHER"

    # Should not reach here, but just in case
    return get_fallback_analysis(commit_data, "OTHER"), "OTHER"


# ==================== FAILED COMMITS TRACKING ====================

class FailedCommit:
    """Record of a commit that failed during analysis."""
    def __init__(self, commit_hash: str, error_type: str, error_msg: str, subject: str = ""):
        self.commit_hash = commit_hash
        self.error_type = error_type  # "TIMEOUT", "429_RATE_LIMIT", "JSON_ERROR", "OTHER"
        self.error_msg = error_msg
        self.subject = subject
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "commit_hash": self.commit_hash,
            "error_type": self.error_type,
            "error_msg": self.error_msg,
            "subject": self.subject,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "FailedCommit":
        return cls(d["commit_hash"], d["error_type"], d["error_msg"], d.get("subject", ""))


def save_failed_commits(failed: list[FailedCommit], output_dir: str, version_range: str):
    """Save failed commits to a JSON file for later repair."""
    version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    failed_file = Path(output_dir) / f"failed_commits_{version_tag}.json"
    with open(failed_file, "w", encoding="utf-8") as f:
        json.dump([fc.to_dict() for fc in failed], f, ensure_ascii=False, indent=2)
    return failed_file


def load_failed_commits(output_dir: str, version_range: str) -> list[FailedCommit]:
    """Load failed commits from a JSON file for repair."""
    version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    failed_file = Path(output_dir) / f"failed_commits_{version_tag}.json"
    if not failed_file.exists():
        return []
    with open(failed_file, "r", encoding="utf-8") as f:
        return [FailedCommit.from_dict(d) for d in json.load(f)]


def is_valid_analysis(analysis: dict) -> bool:
    """Check if the agent analysis contains valid nested scoring data."""
    bd = analysis.get("score_breakdown", {})

    # Must have 4 required dimensions
    required_dims = ["technical", "impact", "quality", "community"]
    if not all(dim in bd for dim in required_dims):
        return False

    # Each dimension must be a dict with subtotal
    for dim in required_dims:
        if not isinstance(bd[dim], dict):
            return False
        if "subtotal" not in bd[dim]:
            return False

    # At least one dimension must have non-zero score
    return any(bd[dim].get("subtotal", 0) > 0 for dim in required_dims)


def get_fallback_analysis(commit_data: CommitData, error_type: str = "UNKNOWN") -> dict:
    """
    Return a minimal analysis when agent fails.
    Scores are set to 0 to clearly indicate failed commits.
    """
    subsystem_prefix, subsystems_touched = get_subsystems_from_files(commit_data.files)
    subsystem_tier = get_subsystem_tier(commit_data.files)

    return {
        "primary_category": "FAILED",
        "secondary_categories": [],
        "cve_ids": extract_cve_ids(commit_data.subject + " " + commit_data.body),
        "fixes_tag": extract_fixes_tag(commit_data.body),
        "cc_stable": "cc: stable" in commit_data.body.lower() or "stable@" in commit_data.body.lower(),
        "subsystem_prefix": subsystem_prefix,
        "subsystems_touched": subsystems_touched,
        "subsystem_tier": subsystem_tier,
        "score_breakdown": {
            "technical": {
                "code_volume": 0,
                "subsystem_criticality": 0,
                "cross_subsystem": 0,
                "subtotal": 0,
                "details": ""
            },
            "impact": {
                "category_base": 0,
                "stable_lts": 0,
                "user_impact": 0,
                "novelty": 0,
                "subtotal": 0,
                "details": ""
            },
            "quality": {
                "review_chain": 0,
                "message_quality": 0,
                "testing": 0,
                "atomicity": 0,
                "subtotal": 0,
                "details": ""
            },
            "community": {
                "cross_org": 0,
                "maintainer": 0,
                "response": 0,
                "subtotal": 0,
                "details": ""
            }
        },
        "reasoning": f"Agent analysis failed: {error_type}",
        "flags": ["AGENT_ERROR", f"AGENT_ERROR_{error_type}"],
    }


# ==================== COMMIT PARSING ====================

def parse_review_chain(body: str) -> dict:
    """Parse review tags from commit body."""
    chain = {
        "signed_off_by": [],
        "reviewed_by": [],
        "tested_by": [],
        "acked_by": [],
        "reported_by": [],
    }

    patterns = {
        "signed-off-by": "signed_off_by",
        "reviewed-by": "reviewed_by",
        "tested-by": "tested_by",
        "acked-by": "acked_by",
        "reported-by": "reported_by",
    }

    for line in body.split("\n"):
        line = line.strip()
        for tag, key in patterns.items():
            if line.lower().startswith(tag + ":"):
                content = line.split(":", 1)[1].strip()
                if "<" in content and ">" in content:
                    email = content.split("<")[1].split(">")[0].strip()
                    company = extract_company(email)
                    chain[key].append(f"{content} ({company})")
                else:
                    chain[key].append(content)

    return chain


def parse_commits(git_output: str) -> list[dict]:
    """Parse git log output into structured commit data."""
    commits = []
    current_commit = {}
    in_body = False

    for line in git_output.split("\n"):
        if line == "COMMIT_START":
            current_commit = {}
            in_body = False
            continue
        elif line == "COMMIT_END":
            if current_commit.get("hash"):
                commits.append(current_commit)
            current_commit = {}
            in_body = False
            continue

        if line == "Body:":
            in_body = True
            current_commit["body"] = ""
            continue

        if in_body:
            current_commit["body"] = current_commit.get("body", "") + "\n" + line
        elif ":" in line:
            key, value = line.split(":", 1)
            key = key.strip().lower().replace(" ", "_")
            value = value.strip()
            current_commit[key] = value

    return commits


def get_subsystems_from_files(files: list[str]) -> tuple[str, list[str]]:
    """Extract subsystem prefix and list from file paths."""
    subsystems = set()
    for f in files:
        if "/" in f:
            subsystem = f.split("/")[0] + "/"
            subsystems.add(subsystem)

    subsystems_list = sorted(list(subsystems))
    prefix = subsystems_list[0] if subsystems_list else "unknown"

    return prefix, subsystems_list


# ==================== GIT OPERATIONS ====================

def get_diff_stats(repo_path: str, commit_hash: str) -> tuple[int, int, int, list[str], str]:
    """Get diff statistics and output for a commit."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "diff", "--numstat", f"{commit_hash}^..{commit_hash}"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        insertions = 0
        deletions = 0
        files = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                try:
                    ins = int(parts[0]) if parts[0] != "-" else 0
                    dele = int(parts[1]) if parts[1] != "-" else 0
                    insertions += ins
                    deletions += dele
                    files.append(parts[2])
                except ValueError:
                    pass

        result = subprocess.run(
            ["git", "-C", repo_path, "diff", f"{commit_hash}^..{commit_hash}"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        diff_output = result.stdout
        hunks = diff_output.count("@@")

        return insertions, deletions, hunks, files, diff_output

    except subprocess.TimeoutExpired:
        return 0, 0, 0, [], ""
    except Exception:
        return 0, 0, 0, [], ""


def get_code_snippet(repo_path: str, commit_hash: str, files: list[str]) -> str:
    """Get the most relevant diff hunk from a commit."""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "diff", f"{commit_hash}^..{commit_hash}"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        diff_lines = result.stdout.split("\n")

        max_hunk_size = 0
        best_hunk = []
        in_hunk = False
        current_hunk = []

        for line in diff_lines[:500]:
            if line.startswith("@@"):
                if current_hunk and len(current_hunk) > max_hunk_size:
                    max_hunk_size = len(current_hunk)
                    best_hunk = current_hunk
                current_hunk = [line]
                in_hunk = True
            elif in_hunk:
                current_hunk.append(line)
                if len(current_hunk) >= 20:
                    break

        if not best_hunk and current_hunk:
            best_hunk = current_hunk

        return "\n".join(best_hunk[:20])

    except Exception:
        return ""


def extract_cve_ids(text: str) -> list[str]:
    """Extract CVE IDs from commit text."""
    pattern = r"(CVE-\d{4}-\d{4,7})"
    return list(set(re.findall(pattern, text.upper())))


def extract_fixes_tag(body: str) -> str:
    """Extract Fixes: tag from commit body."""
    for line in body.split("\n"):
        if line.strip().lower().startswith("fixes:"):
            return line.strip()
    return ""


def generate_lore_link(commit_hash: str, subject: str) -> str:
    """Generate lore.kernel.org link for a commit."""
    return f"https://lore.kernel.org/linux-kernel/{commit_hash}"


# ==================== MAIN ANALYSIS ====================

def process_single_commit(
    repo_path: str,
    commit: dict,
    idx: int,
    total: int,
    progress: ProgressCounter,
    logger: logging.Logger | None = None,
    timeout: int = 300,
    max_retries: int = 3,
) -> tuple[ScoredCommit, str | None]:
    """
    Process a single commit with AI agent analysis.

    Returns:
        (ScoredCommit, error_type) - error_type is None on success
    """
    commit_hash = commit.get("hash", "")
    short_hash = commit_hash[:12]
    current = progress.increment()

    if logger:
        logger.info(f"[{current}/{total}] Analyzing {short_hash}: {commit.get('subject', '')[:60]}...")

    print(f"[{current}/{total}] Analyzing {short_hash}: {commit.get('subject', '')[:60]}...")

    insertions, deletions, hunks, files, diff_output = get_diff_stats(repo_path, commit_hash)

    commit_data = CommitData(
        hash=commit_hash,
        author=commit.get("author", ""),
        author_date=commit.get("authordate", ""),
        committer=commit.get("committer", ""),
        commit_date=commit.get("commitdate", ""),
        subject=commit.get("subject", ""),
        body=commit.get("body", ""),
        files=files,
        files_changed=len(files),
        insertions=insertions,
        deletions=deletions,
        hunks=hunks,
        diff_output=diff_output,
    )

    print(f"  -> Calling AI agent for {short_hash}...")
    analysis, error_type = analyze_with_agent(commit_data, repo_path, logger, timeout, max_retries)

    # Validate agent response - if empty/incomplete, use fallback
    if not error_type and not is_valid_analysis(analysis):
        if logger:
            logger.warning(f"{short_hash} - Agent returned incomplete analysis, using fallback")
        print(f"  -> Agent returned incomplete analysis, using fallback")
        analysis = get_fallback_analysis(commit_data, "INCOMPLETE_RESPONSE")
        error_type = "INCOMPLETE_RESPONSE"

    if error_type:
        if logger:
            logger.warning(f"{short_hash} - Using fallback due to: {error_type}")
        print(f"  -> Using fallback analysis due to: {error_type}")

    author_email = commit_data.author.split("<")[-1].split(">")[0].strip() if "<" in commit_data.author else ""
    committer_email = commit_data.committer.split("<")[-1].split(">")[0].strip() if "<" in commit_data.committer else ""

    # Extract component scores from nested score_breakdown structure
    bd = analysis.get("score_breakdown", {})
    tech = bd.get("technical", {})
    impact = bd.get("impact", {})
    quality = bd.get("quality", {})
    community = bd.get("community", {})

    components = {
        "code_volume": tech.get("code_volume", 0),
        "subsystem_criticality": tech.get("subsystem_criticality", 0),
        "cross_subsystem": tech.get("cross_subsystem", 0),
        "category_base": impact.get("category_base", 0),
        "stable_lts": impact.get("stable_lts", 0),
        "user_impact": impact.get("user_impact", 0),
        "novelty": impact.get("novelty", 0),
        "review_chain": quality.get("review_chain", 0),
        "message_quality": quality.get("message_quality", 0),
        "testing": quality.get("testing", 0),
        "atomicity": quality.get("atomicity", 0),
        "cross_org": community.get("cross_org", 0),
        "maintainer": community.get("maintainer", 0),
        "response": community.get("response", 0),
    }

    # --- Global score range clamp ---
    SCORE_RANGES = {
        "code_volume": (0, 20), "subsystem_criticality": (0, 10),
        "cross_subsystem": (0, 10), "category_base": (0, 15),
        "stable_lts": (0, 5), "user_impact": (0, 5),
        "novelty": (0, 5), "review_chain": (0, 8),
        "message_quality": (0, 6), "testing": (0, 4),
        "atomicity": (0, 2), "cross_org": (0, 4),
        "maintainer": (0, 3), "response": (0, 3),
    }
    for key, (lo, hi) in SCORE_RANGES.items():
        components[key] = max(lo, min(hi, components.get(key, 0)))

    # --- Category-specific caps ---
    primary_cat = analysis.get("primary_category", "")

    # TRIV-* cap: max 5 points total
    if primary_cat.startswith("TRIV-"):
        triv_caps = {
            "code_volume": 1, "subsystem_criticality": 1, "cross_subsystem": 0,
            "category_base": 0, "stable_lts": 0, "user_impact": 0, "novelty": 0,
            "review_chain": 1, "message_quality": 1, "testing": 0, "atomicity": 1,
            "cross_org": 0, "maintainer": 0, "response": 0,
        }
        for key, cap in triv_caps.items():
            components[key] = min(components.get(key, 0), cap)

    # MAINT-WARN / MAINT-NAMING cap: max 23 points total
    if primary_cat in ("MAINT-WARN", "MAINT-NAMING"):
        maint_low_caps = {
            "code_volume": 3, "subsystem_criticality": 4, "cross_subsystem": 0,
            "category_base": 3, "stable_lts": 0, "user_impact": 1, "novelty": 0,
            "review_chain": 3, "message_quality": 3, "testing": 0, "atomicity": 2,
            "cross_org": 2, "maintainer": 2, "response": 0,
        }
        for key, cap in maint_low_caps.items():
            components[key] = min(components.get(key, 0), cap)

    # Calculate dimension scores from clamped components
    score_technical = components["code_volume"] + components["subsystem_criticality"] + components["cross_subsystem"]
    score_impact = components["category_base"] + components["stable_lts"] + components["user_impact"] + components["novelty"]
    score_quality = components["review_chain"] + components["message_quality"] + components["testing"] + components["atomicity"]
    score_community = components["cross_org"] + components["maintainer"] + components["response"]

    # Rebuild nested score_breakdown for output
    score_breakdown_nested = {
        "technical": {
            "code_volume": components["code_volume"],
            "subsystem_criticality": components["subsystem_criticality"],
            "cross_subsystem": components["cross_subsystem"],
            "subtotal": score_technical,
            "details": tech.get("details", "")
        },
        "impact": {
            "category_base": components["category_base"],
            "stable_lts": components["stable_lts"],
            "user_impact": components["user_impact"],
            "novelty": components["novelty"],
            "subtotal": score_impact,
            "details": impact.get("details", "")
        },
        "quality": {
            "review_chain": components["review_chain"],
            "message_quality": components["message_quality"],
            "testing": components["testing"],
            "atomicity": components["atomicity"],
            "subtotal": score_quality,
            "details": quality.get("details", "")
        },
        "community": {
            "cross_org": components["cross_org"],
            "maintainer": components["maintainer"],
            "response": components["response"],
            "subtotal": score_community,
            "details": community.get("details", "")
        }
    }

    score_total = score_technical + score_impact + score_quality + score_community

    code_snippet = get_code_snippet(repo_path, commit_hash, files)

    flags = analysis.get("flags", [])
    if error_type:
        flags.append(f"AGENT_ERROR_{error_type}")

    primary_cat = analysis.get("primary_category", "UNKNOWN")

    if logger:
        status = "FAILED" if error_type else "OK"
        logger.info(f"{short_hash} | {status} | score_total={score_total} | category={primary_cat} | error={error_type or 'None'}")

    return ScoredCommit(
        commit_hash=commit_hash,
        short_hash=short_hash,
        author_name=commit_data.author.split("<")[0].strip(),
        author_email=author_email,
        author_company=extract_company(author_email),
        author_date=commit_data.author_date,
        committer_name=commit_data.committer.split("<")[0].strip(),
        committer_email=committer_email,
        committer_company=extract_company(committer_email),
        commit_date=commit_data.commit_date,
        subject=commit_data.subject,
        primary_category=analysis.get("primary_category", "UNKNOWN"),
        secondary_categories=analysis.get("secondary_categories", []),
        cve_ids=analysis.get("cve_ids", []),
        fixes_tag=analysis.get("fixes_tag", ""),
        cc_stable=analysis.get("cc_stable", False),
        subsystem_prefix=analysis.get("subsystem_prefix", "unknown"),
        subsystems_touched=analysis.get("subsystems_touched", []),
        subsystem_tier=analysis.get("subsystem_tier", 4),
        files_changed=len(files),
        insertions=insertions,
        deletions=deletions,
        hunks=hunks,
        review_chain=parse_review_chain(commit_data.body),
        score_total=score_total,
        score_technical=score_technical,
        score_impact=score_impact,
        score_quality=score_quality,
        score_community=score_community,
        score_breakdown=score_breakdown_nested,
        score_justification=analysis.get("reasoning", analysis.get("score_justification", "")),
        code_snippet=code_snippet,
        flags=flags,
        link=generate_lore_link(commit_hash, commit_data.subject),
    ), error_type


def analyze_commits(
    repo_path: str,
    version_range: str,
    company_filter: str,
    max_commits: int | str,
    max_workers: int = 3,
    output_dir: str = "data",
    track_failures: bool = True,
    logger: logging.Logger | None = None,
    timeout: int = 300,
    max_retries: int = 3,
) -> list[dict]:
    """Analyze commits using AI agent with parallel processing."""

    if not logger:
        logger = setup_logging(output_dir, version_range, "analyze")

    logger.info(f"Company filter: {company_filter}")
    logger.info(f"Max commits: {max_commits}")
    logger.info(f"Max workers: {max_workers}")
    logger.info(f"Timeout: {timeout}s, Max retries: {max_retries}")

    cmd = [
        "git", "-C", repo_path, "log", "--no-merges",
        "--format=COMMIT_START%nHash: %H%nAuthor: %an <%ae>%nAuthorDate: %aI%nCommitter: %cn <%ce>%nCommitDate: %cI%nSubject: %s%nBody:%n%b%nCOMMIT_END",
        version_range,
    ]

    if company_filter != "all":
        cmd.append(f"--author={company_filter}")

    if max_commits != "all" and isinstance(max_commits, int):
        cmd.append(f"-n{max_commits}")

    logger.info(f"Running git log command...")
    print(f"Running git log command...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    commits = parse_commits(result.stdout)

    if not commits:
        logger.warning("No commits found matching the criteria.")
        print("No commits found matching the criteria.")
        return []

    logger.info(f"Found {len(commits)} commits to analyze")
    print(f"Found {len(commits)} commits. Analyzing with {max_workers} parallel workers...")
    print("Press Ctrl+C to stop and save partial results...")

    scored_commits = []
    failed_commits = []
    progress = ProgressCounter(len(commits))

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_commit, repo_path, commit, i, len(commits), progress, logger, timeout, max_retries): commit
                for i, commit in enumerate(commits)
            }

            for future in as_completed(futures):
                try:
                    scored_commit, error_type = future.result()
                    scored_commits.append(scored_commit)
                    if error_type and track_failures:
                        failed_commits.append(FailedCommit(
                            commit_hash=scored_commit.commit_hash,
                            error_type=error_type,
                            error_msg=f"Agent analysis failed with {error_type}",
                            subject=scored_commit.subject[:100],
                        ))
                except Exception as e:
                    commit = futures[future]
                    commit_hash = commit.get('hash', '')
                    print(f"  [ERROR] Failed to analyze commit {commit_hash[:12]}: {e}")
                    if track_failures:
                        failed_commits.append(FailedCommit(
                            commit_hash=commit_hash,
                            error_type="OTHER",
                            error_msg=str(e),
                            subject=commit.get('subject', '')[:100],
                        ))

    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Analysis stopped by user. Saving partial results...")
        logger.warning("Analysis interrupted by user")
        # Cancel remaining futures
        for future in futures:
            future.cancel()

    scored_commits.sort(key=lambda x: x.commit_date)

    # Log summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("ANALYSIS SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total commits processed: {len(scored_commits)}")
    logger.info(f"Successful: {len([c for c in scored_commits if c.score_total > 0])}")
    logger.info(f"Failed (score=0): {len([c for c in scored_commits if c.score_total == 0])}")

    # Save failed commits for potential repair
    if track_failures and failed_commits:
        failed_file = save_failed_commits(failed_commits, output_dir, version_range)
        print(f"\n[INFO] Saved {len(failed_commits)} failed commits to: {failed_file}")
        print(f"[INFO] Run with --repair to re-analyze failed commits:")

        # Group by error type for summary
        by_error = {}
        for fc in failed_commits:
            by_error[fc.error_type] = by_error.get(fc.error_type, 0) + 1
        for err_type, count in sorted(by_error.items(), key=lambda x: -x[1]):
            print(f"       {err_type}: {count}")

        logger.info(f"Failed commits saved to: {failed_file}")
        for err_type, count in sorted(by_error.items(), key=lambda x: -x[1]):
            logger.info(f"  {err_type}: {count}")

    return scored_commits


# ==================== REPAIR FAILED COMMITS ====================

def repair_failed_commits(
    repo_path: str,
    version_range: str,
    output_dir: str = "data",
    max_workers: int = 1,
    logger: logging.Logger | None = None,
    timeout: int = 300,
    max_retries: int = 3,
) -> list[dict]:
    """
    Re-analyze commits that previously failed.

    Returns:
        list of re-analyzed commits as dicts
    """
    if not logger:
        logger = setup_logging(output_dir, version_range, "repair")

    logger.info(f"Loading failed commits from: {output_dir}")
    failed_commits = load_failed_commits(output_dir, version_range)

    if not failed_commits:
        logger.warning(f"No failed commits found for version range: {version_range}")
        print(f"No failed commits found for version range: {version_range}")
        return []

    logger.info(f"Found {len(failed_commits)} failed commits to repair")
    print(f"Found {len(failed_commits)} failed commits to repair...")
    print(f"Version range: {version_range}")

    # Group by error type
    by_error = {}
    for fc in failed_commits:
        by_error[fc.error_type] = by_error.get(fc.error_type, 0) + 1

    logger.info("Error breakdown:")
    for err_type, count in sorted(by_error.items(), key=lambda x: -x[1]):
        logger.info(f"  {err_type}: {count}")

    print("\nError breakdown:")
    for err_type, count in sorted(by_error.items(), key=lambda x: -x[1]):
        print(f"  {err_type}: {count}")

    # Get full commit data from git
    repaired_commits = []
    new_failed_commits = []
    progress = ProgressCounter(len(failed_commits))

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for fc in failed_commits:
                # Fetch the commit from git
                cmd = [
                    "git", "-C", repo_path, "log", "-1",
                    "--format=COMMIT_START%nHash: %H%nAuthor: %an <%ae>%nAuthorDate: %aI%nCommitter: %cn <%ce>%nCommitDate: %cI%nSubject: %s%nBody:%n%b%nCOMMIT_END",
                    fc.commit_hash,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                commits = parse_commits(result.stdout)

                if not commits:
                    logger.warning(f"Could not find commit {fc.commit_hash[:12]} in repo")
                    print(f"  [WARNING] Could not find commit {fc.commit_hash[:12]} in repo")
                    continue

                commit = commits[0]
                future = executor.submit(
                    process_single_commit,
                    repo_path,
                    commit,
                    len(repaired_commits),
                    len(failed_commits),
                    progress,
                    logger,
                    timeout,
                    max_retries,
                )
                futures[future] = (fc, commit)

            for future in as_completed(futures):
                try:
                    scored_commit, error_type = future.result()
                    repaired_commits.append(scored_commit)

                    if error_type:
                        # Still failed, keep in the failed list
                        fc, _ = futures[future]
                        logger.warning(f"Commit {scored_commit.commit_hash[:12]} still failed after repair: {error_type}")
                        new_failed_commits.append(FailedCommit(
                            commit_hash=scored_commit.commit_hash,
                            error_type=error_type,
                            error_msg=f"Retry failed with {error_type}",
                            subject=scored_commit.subject[:100],
                        ))

                except Exception as e:
                    fc, commit = futures[future]
                    logger.error(f"Failed to repair commit {fc.commit_hash[:12]}: {e}")
                    print(f"  [ERROR] Failed to repair commit {fc.commit_hash[:12]}: {e}")
                    new_failed_commits.append(FailedCommit(
                        commit_hash=fc.commit_hash,
                        error_type="OTHER",
                        error_msg=str(e),
                        subject=fc.subject,
                    ))

    except KeyboardInterrupt:
        logger.warning("Repair interrupted by user")
        print("\n\n[INTERRUPTED] Repair stopped by user. Saving partial results...")
        for future in futures:
            future.cancel()

    # Log repair summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("REPAIR SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total attempted: {len(failed_commits)}")
    logger.info(f"Successfully repaired: {len(repaired_commits) - len(new_failed_commits)}")
    logger.info(f"Still failed: {len(new_failed_commits)}")

    # Update failed commits file (remove repaired ones)
    if new_failed_commits:
        save_failed_commits(new_failed_commits, output_dir, version_range)
        print(f"\n[INFO] {len(new_failed_commits)} commits still failed after repair")
        logger.info(f"Remaining failed commits saved to: data/failed_commits_{version_range.replace('..', '_').replace('.', '_')}.json")
    else:
        # All repaired, delete the failed file
        version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
        failed_file = Path(output_dir) / f"failed_commits_{version_tag}.json"
        if failed_file.exists():
            failed_file.unlink()
        print(f"\n[SUCCESS] All {len(failed_commits)} commits successfully repaired!")

    return [scored_commit_to_dict(c) for c in repaired_commits]


# ==================== ALL CHINESE COMPANIES ANALYSIS ====================

def build_chinese_company_filter() -> str:
    """Build git log author filter for all Chinese companies."""
    domains = [f"@{d}" for d in CHINESE_COMPANY_DOMAINS]
    # git log uses regex, join with |
    return "\\|".join(domains)


def analyze_all_chinese_companies(
    repo_path: str,
    version_range: str,
    max_commits: int | str,
    max_workers: int = 3,
    output_dir: str = "data",
    logger: logging.Logger | None = None,
    timeout: int = 300,
    max_retries: int = 3,
) -> dict:
    """
    Analyze all Chinese companies and output JSONL files.

    Returns:
        dict with summary statistics
    """
    if not logger:
        logger = setup_logging(output_dir, version_range, "chinese_companies")

    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Build filter for all Chinese companies
    chinese_filter = build_chinese_company_filter()

    logger.info("Analyzing all Chinese companies")
    print(f"Analyzing all Chinese companies in {version_range}...")
    print(f"Filter: {chinese_filter[:100]}...")
    print("Press Ctrl+C to stop and save partial results...")

    try:
        # Analyze commits
        commits = analyze_commits(
            repo_path=repo_path,
            version_range=version_range,
            company_filter=chinese_filter,
            max_commits=max_commits,
            max_workers=max_workers,
            output_dir=output_dir,
            track_failures=True,
            logger=logger,
            timeout=timeout,
            max_retries=max_retries,
        )

        if not commits:
            logger.warning("No commits found for Chinese companies")
            print("No commits found for Chinese companies.")
            return {"total_commits": 0, "companies": {}}

    except KeyboardInterrupt:
        logger.warning("Chinese companies analysis interrupted by user")
        print("\n\n[INTERRUPTED] Chinese companies analysis stopped by user.")
        print("Attempting to save partial results...")
        # Will still try to save partial results below
        commits = []  # Will be empty, so partial results will be saved if any
        return {"total_commits": 0, "companies": {}, "interrupted": True}

    # Convert to dicts
    commits_dict = [scored_commit_to_dict(c) for c in commits]

    logger.info(f"Converting {len(commits_dict)} commits to dict format")

    # Output JSONL file (one JSON per line)
    version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    jsonl_file = output_path / f"chinese_companies_{version_tag}.jsonl"

    with open(jsonl_file, "w", encoding="utf-8") as f:
        for commit in commits_dict:
            f.write(json.dumps(commit, ensure_ascii=False) + "\n")

    logger.info(f"Saved JSONL to: {jsonl_file}")
    print(f"\nSaved JSONL to: {jsonl_file}")

    # Group by company for summary
    by_company = {}
    for c in commits_dict:
        company = c["author_company"]
        if company not in by_company:
            by_company[company] = {
                "commits": [],
                "total_score": 0,
                "categories": {},
            }
        by_company[company]["commits"].append(c)
        by_company[company]["total_score"] += c["score_total"]

        cat = c["primary_category"]
        by_company[company]["categories"][cat] = by_company[company]["categories"].get(cat, 0) + 1

    # Calculate per-company stats
    company_stats = {}
    for company, data in by_company.items():
        company_stats[company] = {
            "commit_count": len(data["commits"]),
            "total_score": data["total_score"],
            "avg_score": round(data["total_score"] / len(data["commits"]), 2),
            "categories": data["categories"],
        }

    # Save summary
    summary = {
        "version_range": version_range,
        "total_commits": len(commits_dict),
        "companies": company_stats,
        "top_companies_by_commits": sorted(
            [(c, s["commit_count"]) for c, s in company_stats.items()],
            key=lambda x: x[1],
            reverse=True
        ),
        "top_companies_by_score": sorted(
            [(c, s["total_score"]) for c, s in company_stats.items()],
            key=lambda x: x[1],
            reverse=True
        ),
    }

    summary_file = output_path / f"chinese_companies_{version_tag}_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Saved summary to: {summary_file}")

    # Print summary
    print("\n" + "=" * 60)
    print("CHINESE COMPANIES ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Version range: {version_range}")
    print(f"Total commits: {len(commits_dict)}")
    print(f"Companies: {len(company_stats)}")
    print(f"\nTop 10 by commit count:")
    for company, count in summary["top_companies_by_commits"][:10]:
        print(f"  {company}: {count} commits")

    return summary


# ==================== SUMMARY GENERATION ====================

def generate_summary(commits: list[dict], version_range: str, company_filter: str) -> dict:
    """Generate summary statistics from analyzed commits."""
    if not commits:
        return {
            "version_range": version_range,
            "company_filter": company_filter,
            "total_commits_analyzed": 0,
        }

    total_score = sum(c["score_total"] for c in commits)
    avg_score = total_score / len(commits)

    score_dist = {
        "90_100_exceptional": sum(1 for c in commits if c["score_total"] >= 90),
        "70_89_high": sum(1 for c in commits if 70 <= c["score_total"] < 90),
        "50_69_medium": sum(1 for c in commits if 50 <= c["score_total"] < 70),
        "30_49_low": sum(1 for c in commits if 30 <= c["score_total"] < 50),
        "10_29_minimal": sum(1 for c in commits if 10 <= c["score_total"] < 30),
        "0_9_trivial": sum(1 for c in commits if c["score_total"] < 10),
    }

    dim_avgs = {
        "technical": sum(c["score_technical"] for c in commits) / len(commits),
        "impact": sum(c["score_impact"] for c in commits) / len(commits),
        "quality": sum(c["score_quality"] for c in commits) / len(commits),
        "community": sum(c["score_community"] for c in commits) / len(commits),
    }

    by_category = {}
    for c in commits:
        cat = c["primary_category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total_score": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["total_score"] += c["score_total"]

    for cat in by_category:
        by_category[cat]["avg_score"] = by_category[cat]["total_score"] / by_category[cat]["count"]

    by_subsystem = {}
    for c in commits:
        sub = c["subsystem_prefix"]
        if sub not in by_subsystem:
            by_subsystem[sub] = {"count": 0, "total_score": 0}
        by_subsystem[sub]["count"] += 1
        by_subsystem[sub]["total_score"] += c["score_total"]

    for sub in by_subsystem:
        by_subsystem[sub]["avg_score"] = by_subsystem[sub]["total_score"] / by_subsystem[sub]["count"]

    sorted_commits = sorted(commits, key=lambda x: x["score_total"], reverse=True)
    top_10 = [f"{c['short_hash']}: {c['subject'][:50]}... (score: {c['score_total']})" for c in sorted_commits[:10]]
    bottom_10 = [f"{c['short_hash']}: {c['subject'][:50]}... (score: {c['score_total']})" for c in sorted_commits[-10:]]

    flags_summary = {}
    for c in commits:
        for flag in c["flags"]:
            flags_summary[flag] = flags_summary.get(flag, 0) + 1

    return {
        "version_range": version_range,
        "company_filter": company_filter,
        "total_commits_analyzed": len(commits),
        "total_score": total_score,
        "average_score": round(avg_score, 2),
        "score_distribution": score_dist,
        "dimension_averages": {k: round(v, 2) for k, v in dim_avgs.items()},
        "by_category": by_category,
        "by_subsystem": by_subsystem,
        "top_10_commits": top_10,
        "bottom_10_commits": bottom_10,
        "flags_summary": flags_summary,
    }


def scored_commit_to_dict(sc: ScoredCommit) -> dict:
    """Convert ScoredCommit to dict for JSON serialization."""
    return {
        "commit_hash": sc.commit_hash,
        "short_hash": sc.short_hash,
        "author_name": sc.author_name,
        "author_email": sc.author_email,
        "author_company": sc.author_company,
        "author_date": sc.author_date,
        "committer_name": sc.committer_name,
        "committer_email": sc.committer_email,
        "committer_company": sc.committer_company,
        "commit_date": sc.commit_date,
        "subject": sc.subject,
        "primary_category": sc.primary_category,
        "secondary_categories": sc.secondary_categories,
        "cve_ids": sc.cve_ids,
        "fixes_tag": sc.fixes_tag,
        "cc_stable": sc.cc_stable,
        "subsystem_prefix": sc.subsystem_prefix,
        "subsystems_touched": sc.subsystems_touched,
        "subsystem_tier": sc.subsystem_tier,
        "files_changed": sc.files_changed,
        "insertions": sc.insertions,
        "deletions": sc.deletions,
        "hunks": sc.hunks,
        "review_chain": sc.review_chain,
        "score_total": sc.score_total,
        "score_technical": sc.score_technical,
        "score_impact": sc.score_impact,
        "score_quality": sc.score_quality,
        "score_community": sc.score_community,
        "score_breakdown": sc.score_breakdown,
        "score_justification": sc.score_justification,
        "code_snippet": sc.code_snippet,
        "flags": sc.flags,
        "link": sc.link,
    }


# ==================== MAIN ====================

def main():
    parser = argparse.ArgumentParser(
        description="Analyze Linux kernel commits using AI agent and produce scored JSON report"
    )
    parser.add_argument("--version", required=False, help="Version range (e.g., v6.5..v6.6)")
    parser.add_argument("--company", default="all", help='Company email filter (e.g., "@huawei.com") or "all"')
    parser.add_argument("--max-commits", default="all", help='Maximum commits to analyze (e.g., 50) or "all"')
    parser.add_argument("--repo", default="linux-kernel", help="Path to Linux kernel git repository")
    parser.add_argument("--output-dir", default="data", help="Output directory for results")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout in seconds for each agent call (default: 300)")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries for 429 rate limit errors (default: 3)")

    # Repair mode: re-analyze failed commits
    parser.add_argument("--repair", action="store_true",
                        help="Repair mode: re-analyze commits that previously failed (requires --version)")

    # Special mode for all Chinese companies
    parser.add_argument("--chinese-companies", action="store_true",
                        help="Analyze all Chinese companies and output JSONL file")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    # Handle repair mode
    if args.repair:
        if not args.version:
            print("Error: --version is required when using --repair")
            print("Example: --repair --version v6.5..v6.6")
            return

        print("\n" + "=" * 60)
        print("REPAIR MODE: Re-analyzing failed commits")
        print("=" * 60)

        repaired = repair_failed_commits(
            repo_path=args.repo,
            version_range=args.version,
            output_dir=args.output_dir,
            max_workers=args.workers,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )

        if not repaired:
            print("\nNo commits to repair.")
            return

        # Save repaired commits
        version_tag = args.version.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
        repair_file = output_dir / f"repaired_commits_{version_tag}.json"
        with open(repair_file, "w", encoding="utf-8") as f:
            json.dump(repaired, f, ensure_ascii=False, indent=2)

        print(f"\nSaved repaired commits to: {repair_file}")

        # Merge with existing results if available
        all_file = output_dir / f"commit_scores_{version_tag}_all.json"
        if all_file.exists():
            with open(all_file, "r", encoding="utf-8") as f:
                existing_commits = json.load(f)

            # Create a map of existing commits by hash
            existing_map = {c["commit_hash"]: c for c in existing_commits}

            # Update with repaired commits
            for rc in repaired:
                existing_map[rc["commit_hash"]] = rc

            # Save updated all file
            merged = list(existing_map.values())
            merged.sort(key=lambda x: x["commit_date"])
            with open(all_file, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            print(f"Merged repaired commits into: {all_file}")

        return

    # Check for chinese-companies mode
    if args.chinese_companies:
        if not args.version:
            print("Error: --version is required when using --chinese-companies")
            return

        max_commits = args.max_commits
        if max_commits != "all":
            try:
                max_commits = int(max_commits)
            except ValueError:
                print("Error: --max-commits must be an integer or 'all'")
                return

        analyze_all_chinese_companies(
            repo_path=args.repo,
            version_range=args.version,
            max_commits=max_commits,
            max_workers=args.workers,
            output_dir=args.output_dir,
            timeout=args.timeout,
            max_retries=args.max_retries,
        )
        return

    # Normal mode
    if not args.version:
        print("Error: --version is required (or use --chinese-companies or --repair)")
        parser.print_help()
        return

    max_commits = args.max_commits
    if max_commits != "all":
        try:
            max_commits = int(max_commits)
        except ValueError:
            print("Error: --max-commits must be an integer or 'all'")
            return

    commits = analyze_commits(
        repo_path=args.repo,
        version_range=args.version,
        company_filter=args.company,
        max_commits=max_commits,
        max_workers=args.workers,
        output_dir=args.output_dir,
        track_failures=True,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )

    if not commits:
        print("No commits found matching the criteria.")
        return

    commits_dict = [scored_commit_to_dict(c) for c in commits]

    batch_size = 50
    if len(commits_dict) > batch_size:
        for i in range(0, len(commits_dict), batch_size):
            batch = commits_dict[i : i + batch_size]
            version_tag = args.version.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
            batch_file = output_dir / f"commit_scores_{version_tag}_batch_{i // batch_size + 1}.json"
            with open(batch_file, "w", encoding="utf-8") as f:
                json.dump(batch, f, ensure_ascii=False, indent=2)
            print(f"Saved batch {i // batch_size + 1} to {batch_file}")

    summary = generate_summary(commits_dict, args.version, args.company)

    version_tag = args.version.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    all_file = output_dir / f"commit_scores_{version_tag}_all.json"
    with open(all_file, "w", encoding="utf-8") as f:
        json.dump(commits_dict, f, ensure_ascii=False, indent=2)

    summary_file = output_dir / f"commit_scores_{version_tag}_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Version range: {args.version}")
    print(f"Company filter: {args.company}")
    print(f"Total commits: {len(commits)}")
    print(f"Average score: {summary['average_score']:.2f}")
    print(f"\nScore distribution:")
    for range_name, count in summary["score_distribution"].items():
        print(f"  {range_name}: {count}")
    print(f"\nDimension averages:")
    for dim, avg in summary["dimension_averages"].items():
        print(f"  {dim}: {avg:.2f}")
    print(f"\nFiles saved:")
    print(f"  {all_file}")
    print(f"  {summary_file}")


if __name__ == "__main__":
    main()
