"""
Scrape Linux kernel contribution statistics from remword.com/kps_result
for kernel versions 5.0 through 6.18 (2019-2025).

Collects:
- Per-company patch counts (whole)
- Per-company line counts (whole_line)
- Per-country patch counts (whole_country)
- Per-country line counts (whole_line_country)
"""

import re
import time
import json
import httpx
from bs4 import BeautifulSoup
from pathlib import Path

BASE_URL = "https://www.remword.com/kps_result"

# Linux kernel versions from 5.0 (2019-03-03) to 6.18
VERSIONS = [
    "5.0", "5.1", "5.2", "5.3", "5.4", "5.5", "5.6", "5.7", "5.8", "5.9",
    "5.10", "5.11", "5.12", "5.13", "5.14", "5.15", "5.16", "5.17", "5.18", "5.19",
    "6.0", "6.1", "6.2", "6.3", "6.4", "6.5", "6.6", "6.7", "6.8", "6.9",
    "6.10", "6.11", "6.12", "6.13", "6.14", "6.15", "6.16", "6.17", "6.18",
]

PAGE_TYPES = {
    "employer_patches": "{ver}_whole.html",
    "employer_lines": "{ver}_whole_line.html",
    "country_patches": "{ver}_whole_country.html",
    "country_lines": "{ver}_whole_line_country.html",
}

# Pattern: No.{rank}\t{Name}\s+{count}({percentage}%)
ENTRY_PATTERN = re.compile(
    r"No\.(\d+)\s+(.+?)\s{2,}(\d+)\((\d+\.?\d*)%\)"
)
# Pattern for contributors: No.{rank}\t{Name} <email>\s+{count}
CONTRIBUTOR_PATTERN = re.compile(
    r"No\.(\d+)\s+(.+?)\s{2,}(\d+)\s*$"
)


def parse_entries_from_html(html: str) -> list[dict]:
    """Parse company/country entries from KPS page using DOM structure.

    The HTML structure is:
    <ul id="containerul">
      <pre>...header text...</pre>
      <li>No.1  CompanyName   3070(23.97%)
        <ul>
          <li>No.1  Person <email>   214</li>
          ...
        </ul>
      </li>
      ...
    </ul>
    """
    soup = BeautifulSoup(html, "html.parser")
    container = soup.find("ul", id="containerul")
    if not container:
        return []

    entries = []

    # Find all <li> elements, then filter for top-level ones
    # Top-level entries have a nested <ul>, contributors don't
    all_li = container.find_all("li")

    # Group: top-level <li> are those with a nested <ul>
    for li in all_li:
        if not li.find("ul"):  # Skip non-top-level entries
            continue

        # Get only the direct text of this <li>, not nested content
        # The direct text contains: No.{rank}\t{Name}\t{count}({pct}%)
        direct_text = ""
        for child in li.children:
            if isinstance(child, str):
                direct_text += child
            elif hasattr(child, 'name') and child.name == "ul":
                break

        direct_text = direct_text.strip()
        match = ENTRY_PATTERN.search(direct_text)
        if not match:
            continue

        rank = int(match.group(1))
        name = match.group(2).strip()
        count = int(match.group(3))
        percentage = float(match.group(4))

        # Parse contributors from nested <ul>
        contributors = []
        nested_ul = li.find("ul")
        if nested_ul:
            for sub_li in nested_ul.find_all("li", recursive=False):
                sub_text = sub_li.get_text().strip()
                sub_match = ENTRY_PATTERN.search(sub_text)
                if sub_match:
                    contrib_name = sub_match.group(2).strip()
                    # Remove email part: "Name <email>" -> "Name"
                    if "<" in contrib_name:
                        contrib_name = contrib_name.split("<")[0].strip()
                    if "&lt;" in contrib_name:
                        contrib_name = contrib_name.split("&lt;")[0].strip()
                    contributors.append({
                        "rank": int(sub_match.group(1)),
                        "name": contrib_name,
                        "count": int(sub_match.group(3)),
                    })
                else:
                    # Try without percentage (some contributor lines have just count)
                    sub_match2 = CONTRIBUTOR_PATTERN.search(sub_text)
                    if sub_match2:
                        contrib_name = sub_match2.group(2).strip()
                        if "<" in contrib_name:
                            contrib_name = contrib_name.split("<")[0].strip()
                        contributors.append({
                            "rank": int(sub_match2.group(1)),
                            "name": contrib_name,
                            "count": int(sub_match2.group(3)),
                        })

        entries.append({
            "rank": rank,
            "name": name,
            "count": count,
            "percentage": percentage,
            "contributors": contributors,
        })

    return entries


def parse_page(html: str) -> dict:
    """Parse a full page returning summary stats and all entries."""
    soup = BeautifulSoup(html, "html.parser")

    # The header is in a <pre> tag inside containerul
    pre = soup.find("pre")
    header_text = pre.get_text() if pre else soup.get_text()[:500]

    total_match = re.search(
        r"(?:Total\s+(?:patch\s+sets?|changed\s+lines?).*?:\s*)([\d,]+)",
        header_text, re.IGNORECASE
    )
    total = int(total_match.group(1).replace(",", "")) if total_match else 0

    orgs_match = re.search(r"(\d+)\s+(?:companies|nations?|countries)", header_text, re.IGNORECASE)
    num_orgs = int(orgs_match.group(1)) if orgs_match else 0

    entries = parse_entries_from_html(html)

    return {
        "total": total,
        "num_orgs": num_orgs,
        "entries": entries,
    }


def scrape_version(client: httpx.Client, version: str) -> dict | None:
    """Scrape all page types for a given kernel version."""
    result = {"version": version}
    first_page = True

    for page_type, url_template in PAGE_TYPES.items():
        url = f"{BASE_URL}/{url_template.format(ver=version)}"
        try:
            resp = client.get(url)
            if resp.status_code == 404:
                if first_page:
                    return None  # Version doesn't exist
                result[page_type] = None
                continue
            resp.raise_for_status()
            data = parse_page(resp.text)
            result[page_type] = data
            print(f"  [{version}] {page_type}: {data['total']} total, {len(data['entries'])} entries")
        except httpx.HTTPStatusError as e:
            print(f"  [{version}] {page_type}: HTTP error {e.response.status_code}")
            result[page_type] = None
        except Exception as e:
            print(f"  [{version}] {page_type}: Error {e}")
            result[page_type] = None

        first_page = False
        time.sleep(0.3)

    return result


def main():
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    all_results = []

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        for version in VERSIONS:
            print(f"\nScraping Linux {version}...")
            result = scrape_version(client, version)
            if result is not None:
                all_results.append(result)
                with open(output_dir / f"v{version}.json", "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            else:
                print(f"  Skipping {version} (not available)")

    with open(output_dir / "all_versions.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Scraped {len(all_results)} versions. Data saved to {output_dir}/")


if __name__ == "__main__":
    main()
