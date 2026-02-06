#!/usr/bin/env python3
"""
Batch Analyzer for Chinese Companies in Linux Kernel

Analyzes contributions from major Chinese companies to the Linux kernel
using the linux_kernel_analyzer.py scoring system.

Usage:
    python batch_analyzer_china.py --version v6.6..v6.7
    python batch_analyzer_china.py --version v6.5..v6.6 --max-commits 100
"""

import argparse
import json
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict


# Major Chinese companies for batch analysis
CHINESE_COMPANIES = {
    "Huawei": "@huawei.com",
    "Alibaba": "@alibaba.com",
    "Tencent": "@tencent.com",
    "ByteDance": "@bytedance.com",
    "Xiaomi": "@xiaomi.com",
    "OPPO": "@oppo.com",
    "vivo": "@vivo.com",
    "ZTE": "@zte.com",
    "MediaTek": "@mediatek.com",
    "Loongson": "@loongson.cn",
    "Kylin": "@kylinos.cn",
    "AntGroup": "@antgroup.com",
    "Baidu": "@baidu.com",
}


def analyze_company(
    company_name: str,
    company_filter: str,
    version_range: str,
    max_commits: int | str,
    repo_path: str,
    output_dir: Path,
) -> dict:
    """Run analysis for a single company."""
    print(f"\n{'='*60}")
    print(f"Analyzing {company_name} ({company_filter})")
    print(f"{'='*60}")

    cmd = [
        "python",
        "linux_kernel_analyzer.py",
        "--version", version_range,
        "--company", company_filter,
        "--max-commits", str(max_commits),
        "--repo", repo_path,
        "--output-dir", str(output_dir),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Load the summary file
    version_tag = version_range.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    summary_file = output_dir / f"commit_scores_{version_tag}_summary.json"

    if summary_file.exists():
        with open(summary_file, encoding="utf-8") as f:
            summary = json.load(f)
        return {
            "company": company_name,
            "filter": company_filter,
            "success": True,
            "summary": summary,
        }
    else:
        return {
            "company": company_name,
            "filter": company_filter,
            "success": False,
            "error": result.stderr,
        }


def generate_company_report(
    results: list[dict],
    version_range: str,
    output_dir: Path,
):
    """Generate a consolidated report for all companies."""

    report = {
        "generated_at": datetime.now().isoformat(),
        "version_range": version_range,
        "companies": {},
        "aggregates": {
            "total_commits": 0,
            "total_score": 0,
            "companies_analyzed": 0,
            "successful": 0,
            "failed": 0,
        },
        "rankings": {
            "by_total_commits": [],
            "by_average_score": [],
            "by_total_score": [],
        },
        "category_breakdown": {},
        "subsystem_breakdown": {},
        "top_commits_all": [],
    }

    all_commits = []

    for result in results:
        company = result["company"]
        report["aggregates"]["companies_analyzed"] += 1

        if not result.get("success"):
            report["aggregates"]["failed"] += 1
            report["companies"][company] = {
                "status": "failed",
                "error": result.get("error", "Unknown error"),
            }
            continue

        report["aggregates"]["successful"] += 1
        summary = result["summary"]

        # Store company stats
        report["companies"][company] = {
            "total_commits": summary.get("total_commits_analyzed", 0),
            "average_score": summary.get("average_score", 0),
            "total_score": summary.get("total_score", 0),
            "dimension_averages": summary.get("dimension_averages", {}),
            "score_distribution": summary.get("score_distribution", {}),
            "by_category": summary.get("by_category", {}),
            "by_subsystem": summary.get("by_subsystem", {}),
        }

        # Update aggregates
        report["aggregates"]["total_commits"] += summary.get("total_commits_analyzed", 0)
        report["aggregates"]["total_score"] += summary.get("total_score", 0)

        # Collect top commits
        if summary.get("top_10_commits"):
            for commit_str in summary["top_10_commits"][:3]:  # Top 3 per company
                all_commits.append({
                    "company": company,
                    "summary": commit_str,
                })

        # Aggregate category breakdown
        for cat, stats in summary.get("by_category", {}).items():
            if cat not in report["category_breakdown"]:
                report["category_breakdown"][cat] = {"count": 0, "total_score": 0}
            report["category_breakdown"][cat]["count"] += stats["count"]
            report["category_breakdown"][cat]["total_score"] += stats.get("total_score", stats["count"] * stats.get("avg_score", 0))

        # Aggregate subsystem breakdown
        for sub, stats in summary.get("by_subsystem", {}).items():
            if sub not in report["subsystem_breakdown"]:
                report["subsystem_breakdown"][sub] = {"count": 0, "total_score": 0}
            report["subsystem_breakdown"][sub]["count"] += stats["count"]
            report["subsystem_breakdown"][sub]["total_score"] += stats.get("total_score", stats["count"] * stats.get("avg_score", 0))

    # Calculate averages for categories
    for cat in report["category_breakdown"]:
        count = report["category_breakdown"][cat]["count"]
        total = report["category_breakdown"][cat]["total_score"]
        report["category_breakdown"][cat]["avg_score"] = total / count if count > 0 else 0

    # Calculate averages for subsystems
    for sub in report["subsystem_breakdown"]:
        count = report["subsystem_breakdown"][sub]["count"]
        total = report["subsystem_breakdown"][sub]["total_score"]
        report["subsystem_breakdown"][sub]["avg_score"] = total / count if count > 0 else 0

    # Generate rankings
    ranking_data = []
    for company, stats in report["companies"].items():
        if stats.get("status") == "failed":
            continue
        ranking_data.append({
            "company": company,
            "total_commits": stats.get("total_commits", 0),
            "average_score": stats.get("average_score", 0),
            "total_score": stats.get("total_score", 0),
        })

    # Sort by different metrics
    report["rankings"]["by_total_commits"] = sorted(
        ranking_data, key=lambda x: x["total_commits"], reverse=True
    )
    report["rankings"]["by_average_score"] = sorted(
        ranking_data, key=lambda x: x["average_score"], reverse=True
    )
    report["rankings"]["by_total_score"] = sorted(
        ranking_data, key=lambda x: x["total_score"], reverse=True
    )

    # Top commits across all companies
    report["top_commits_all"] = all_commits[:20]

    return report


def print_report_summary(report: dict):
    """Print a summary of the report to console."""

    print("\n" + "=" * 70)
    print("CHINESE COMPANIES LINUX KERNEL CONTRIBUTION ANALYSIS")
    print("=" * 70)
    print(f"Version range: {report['version_range']}")
    print(f"Generated: {report['generated_at']}")
    print()

    print(f"Companies analyzed: {report['aggregates']['companies_analyzed']}")
    print(f"  Successful: {report['aggregates']['successful']}")
    print(f"  Failed: {report['aggregates']['failed']}")
    print()

    print(f"Total commits analyzed: {report['aggregates']['total_commits']}")
    print(f"Total score: {report['aggregates']['total_score']}")
    if report['aggregates']['total_commits'] > 0:
        print(f"Overall average score: {report['aggregates']['total_score'] / report['aggregates']['total_commits']:.2f}")
    print()

    print("-" * 70)
    print("RANKING BY TOTAL COMMITS")
    print("-" * 70)
    for i, entry in enumerate(report["rankings"]["by_total_commits"][:10], 1):
        print(f"{i:2d}. {entry['company']:20s} | Commits: {entry['total_commits']:4d} | Avg Score: {entry['average_score']:5.2f}")

    print()
    print("-" * 70)
    print("RANKING BY AVERAGE SCORE")
    print("-" * 70)
    for i, entry in enumerate(report["rankings"]["by_average_score"][:10], 1):
        print(f"{i:2d}. {entry['company']:20s} | Avg Score: {entry['average_score']:5.2f} | Commits: {entry['total_commits']:4d}")

    print()
    print("-" * 70)
    print("RANKING BY TOTAL SCORE")
    print("-" * 70)
    for i, entry in enumerate(report["rankings"]["by_total_score"][:10], 1):
        print(f"{i:2d}. {entry['company']:20s} | Total Score: {entry['total_score']:6.0f} | Commits: {entry['total_commits']:4d}")

    print()
    print("-" * 70)
    print("CATEGORY BREAKDOWN (All Companies)")
    print("-" * 70)
    # Sort by count
    categories = sorted(
        report["category_breakdown"].items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    for cat, stats in categories[:15]:
        print(f"{cat:20s} | Count: {stats['count']:4d} | Avg Score: {stats['avg_score']:5.2f}")

    print()
    print("-" * 70)
    print("SUBSYSTEM BREAKDOWN (All Companies)")
    print("-" * 70)
    subsystems = sorted(
        report["subsystem_breakdown"].items(),
        key=lambda x: x[1]["count"],
        reverse=True
    )
    for sub, stats in subsystems[:15]:
        print(f"{sub:30s} | Count: {stats['count']:4d} | Avg Score: {stats['avg_score']:5.2f}")

    print()
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Batch analyze Chinese companies' Linux kernel contributions"
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Version range (e.g., v6.6..v6.7)",
    )
    parser.add_argument(
        "--max-commits",
        default="100",
        help='Maximum commits per company (default: 100)',
    )
    parser.add_argument(
        "--repo",
        default="linux-kernel",
        help="Path to Linux kernel git repository",
    )
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Output directory for results",
    )
    parser.add_argument(
        "--companies",
        nargs="*",
        help="Specific companies to analyze (default: all major Chinese companies)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all commits (no limit)",
    )

    args = parser.parse_args()

    # Determine max commits
    max_commits = "all" if args.all else args.max_commits

    # Determine companies to analyze
    if args.companies:
        companies = {name: filter for name, filter in CHINESE_COMPANIES.items()
                     if name.lower() in [c.lower() for c in args.companies]}
    else:
        companies = CHINESE_COMPANIES

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("BATCH ANALYZER FOR CHINESE COMPANIES")
    print("=" * 70)
    print(f"Version range: {args.version}")
    print(f"Companies to analyze: {len(companies)}")
    print(f"Max commits per company: {max_commits}")
    print()

    # Run analysis for each company
    results = []
    for company_name, company_filter in companies.items():
        result = analyze_company(
            company_name=company_name,
            company_filter=company_filter,
            version_range=args.version,
            max_commits=max_commits,
            repo_path=args.repo,
            output_dir=output_dir,
        )
        results.append(result)

    # Generate consolidated report
    report = generate_company_report(results, args.version, output_dir)

    # Save report
    version_tag = args.version.replace("..", "_").replace(".", "_").replace("^", "").replace("~", "")
    report_file = output_dir / f"china_companies_{version_tag}_report.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # Print summary
    print_report_summary(report)

    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
