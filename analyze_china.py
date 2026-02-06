"""
Analyze Chinese companies' contributions to Linux kernel (2019-2025).

Processes scraped data to generate:
1. Summary table: Chinese contributions by version
2. Top Chinese companies ranking
3. Trend analysis
"""

import json
from pathlib import Path
from collections import defaultdict
import pandas as pd

# Known Chinese companies (case-insensitive matching)
CHINESE_COMPANIES = {
    "huawei", "alibaba", "tencent", "baidu", "bytedance", "xiaomi",
    "oppo", "vivo", "zte", "lenovo", "inspur", "hisilicon",
    "allwinnertech", "rockchip", "unisoc", "spreadtrum", "sophgo",
    "loongson", "phytium", "arm china", "mediatek", "quectel",
    "gigadevice", "starfive", "thead", "sifive china", "spacemit",
    "deepin", "kylin", "uniontech", "kylinos", "openanolis",
}

# Additional keywords that indicate Chinese affiliation
CHINESE_KEYWORDS = ["shenzhen", "beijing", "shanghai", "guangzhou", "hangzhou"]


def is_chinese_company(name: str) -> bool:
    """Check if a company name is Chinese."""
    name_lower = name.lower()

    # Exact match
    if name_lower in CHINESE_COMPANIES:
        return True

    # Partial match
    for cn_name in CHINESE_COMPANIES:
        if cn_name in name_lower:
            return True

    # Keyword match
    for keyword in CHINESE_KEYWORDS:
        if keyword in name_lower:
            return True

    return False


def analyze_version(data: dict) -> dict:
    """Extract Chinese company data from a single version."""
    version = data["version"]
    result = {
        "version": version,
        "total_patches": 0,
        "total_lines": 0,
        "chinese_patches": 0,
        "chinese_lines": 0,
        "chinese_country_patches": 0,
        "chinese_country_lines": 0,
        "companies": [],
    }

    # Get total patches/lines
    if data.get("employer_patches"):
        result["total_patches"] = data["employer_patches"]["total"]
    if data.get("employer_lines"):
        result["total_lines"] = data["employer_lines"]["total"]

    # Get Chinese country stats
    if data.get("country_patches"):
        for entry in data["country_patches"]["entries"]:
            if entry["name"].lower() in ["chinese", "china"]:
                result["chinese_country_patches"] = entry["count"]
                result["chinese_country_percentage"] = entry["percentage"]
                break

    if data.get("country_lines"):
        for entry in data["country_lines"]["entries"]:
            if entry["name"].lower() in ["chinese", "china"]:
                result["chinese_country_lines"] = entry["count"]
                result["chinese_country_lines_percentage"] = entry["percentage"]
                break

    # Extract Chinese companies
    if data.get("employer_patches"):
        for entry in data["employer_patches"]["entries"]:
            if is_chinese_company(entry["name"]):
                company_data = {
                    "name": entry["name"],
                    "rank": entry["rank"],
                    "patches": entry["count"],
                    "patches_pct": entry["percentage"],
                    "lines": 0,
                    "lines_pct": 0,
                    "top_contributors": [
                        {"name": c["name"], "patches": c["count"]}
                        for c in entry["contributors"][:5]
                    ],
                }

                # Find corresponding lines data
                if data.get("employer_lines"):
                    for line_entry in data["employer_lines"]["entries"]:
                        if line_entry["name"] == entry["name"]:
                            company_data["lines"] = line_entry["count"]
                            company_data["lines_pct"] = line_entry["percentage"]
                            break

                result["companies"].append(company_data)
                result["chinese_patches"] += entry["count"]

    # Calculate Chinese companies' total lines
    if data.get("employer_lines"):
        for entry in data["employer_lines"]["entries"]:
            if is_chinese_company(entry["name"]):
                result["chinese_lines"] += entry["count"]

    return result


def main():
    data_dir = Path("data")
    results = []

    # Load and analyze all versions
    all_data_file = data_dir / "all_versions.json"
    if all_data_file.exists():
        with open(all_data_file, encoding="utf-8") as f:
            all_versions = json.load(f)

        for version_data in all_versions:
            analysis = analyze_version(version_data)
            results.append(analysis)

    # Create summary DataFrame
    summary_rows = []
    for r in results:
        summary_rows.append({
            "Version": r["version"],
            "Total Patches": r["total_patches"],
            "CN Companies Patches": r["chinese_patches"],
            "CN Companies %": f"{r['chinese_patches']/r['total_patches']*100:.2f}%" if r["total_patches"] else "0%",
            "CN Country Patches": r.get("chinese_country_patches", 0),
            "CN Country %": f"{r.get('chinese_country_percentage', 0):.2f}%",
            "Total Lines": r["total_lines"],
            "CN Companies Lines": r["chinese_lines"],
            "CN Companies Lines %": f"{r['chinese_lines']/r['total_lines']*100:.2f}%" if r["total_lines"] else "0%",
        })

    df_summary = pd.DataFrame(summary_rows)
    print("\n=== Chinese Contributions Summary (2019-2025) ===\n")
    print(df_summary.to_string(index=False))

    # Aggregate: top Chinese companies across all versions
    all_companies = defaultdict(lambda: {"patches": 0, "lines": 0, "versions": []})

    for r in results:
        for company in r["companies"]:
            name = company["name"]
            all_companies[name]["patches"] += company["patches"]
            all_companies[name]["lines"] += company["lines"]
            all_companies[name]["versions"].append(r["version"])

    # Sort by total patches
    top_companies = sorted(
        all_companies.items(),
        key=lambda x: x[1]["patches"],
        reverse=True
    )

    print("\n\n=== Top Chinese Companies (Aggregated 5.0-6.18) ===\n")
    for i, (name, stats) in enumerate(top_companies[:20], 1):
        print(f"{i:2d}. {name:30s} | Patches: {stats['patches']:6d} | Lines: {stats['lines']:10d} | Versions: {len(stats['versions'])}")

    # Calculate totals
    total_patches_all = sum(r["total_patches"] for r in results)
    total_chinese_patches = sum(r["chinese_patches"] for r in results)
    total_lines_all = sum(r["total_lines"] for r in results)
    total_chinese_lines = sum(r["chinese_lines"] for r in results)

    print(f"\n\n=== Overall Statistics (5.0-6.18) ===")
    print(f"Total kernel patches: {total_patches_all:,}")
    print(f"Chinese companies patches: {total_chinese_patches:,} ({total_chinese_patches/total_patches_all*100:.2f}%)")
    print(f"Total kernel lines changed: {total_lines_all:,}")
    print(f"Chinese companies lines: {total_chinese_lines:,} ({total_chinese_lines/total_lines_all*100:.2f}%)")

    # Save detailed results
    output_file = data_dir / "china_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n\nDetailed analysis saved to {output_file}")

    # Save summary CSV
    csv_file = data_dir / "china_summary.csv"
    df_summary.to_csv(csv_file, index=False, encoding="utf-8-sig")
    print(f"Summary table saved to {csv_file}")


if __name__ == "__main__":
    main()
