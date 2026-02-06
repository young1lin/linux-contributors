#!/usr/bin/env python3
"""Quick test to see what the agent returns"""

import json
import subprocess
import sys

# Test commit data
commit_data = {
    "commit_hash": "f708f6970cc9d6bac71da45c129482092e710537",
    "short_hash": "f708f6970cc9",
    "author_name": "Miaohe Lin",
    "author_email": "linmiaohe@huawei.com",
    "author_date": "2024-07-09T20:04:33+08:00",
    "committer_name": "Andrew Morton",
    "committer_email": "akpm@linux-foundation.org",
    "commit_date": "2024-07-09T15:41:11-07:00",
    "subject": "mm/hugetlb: fix kernel NULL pointer dereference when migrating hugetlb folio",
    "body": """A kernel crash was observed when migrating hugetlb folio:

BUG: kernel NULL pointer dereference, address: 0000000000000008

Fixes: f6a8dd98a2ce ("hugetlb: convert alloc_buddy_hugetlb_folio to use a folio")
Fixes: be9581ea8c05 ("mm: fix crashes from deferred split racing folio migration")
Signed-off-by: Miaohe Lin <linmiaohe@huawei.com>
Cc: Hugh Dickins <hughd@google.com>
Cc: <stable@vger.kernel.org>
Signed-off-by: Andrew Morton <akpm@linux-foundation.org>""",
    "files": ["mm/hugetlb.c"],
    "files_changed": 1,
    "insertions": 3,
    "deletions": 0,
    "hunks": 1,
    "diff_output": """diff --git a/mm/hugetlb.c b/mm/hugetlb.c
index fe44324d6383..43e1af868cfd 100644
--- a/mm/hugetlb.c
+++ b/mm/hugetlb.c
@@ -2162,6 +2162,9 @@ static struct folio *alloc_buddy_hugetlb_folio(struct hstate *h,
 		nid = numa_mem_id();
retry:
 	folio = __folio_alloc(gfp_mask, order, nid, nmask);
+	/* Ensure hugetlb folio won't have large_rmappable flag set. */
+	if (folio)
+		folio_clear_large_rmappable(folio);""",
    "code_snippet": """@@ -2162,6 +2162,9 @@ static struct folio *alloc_buddy_hugetlb_folio(struct hstate *h,
 		nid = numa_mem_id();
retry:
 	folio = __folio_alloc(gfp_mask, order, nid, nmask);
+	/* Ensure hugetlb folio won't have large_rmappable flag set. */
+	if (folio)
+		folio_clear_large_rmappable(folio);"""
}

prompt = f"""Analyze this Linux kernel commit and return ONLY a valid JSON object (no markdown, no explanation):

{json.dumps(commit_data, ensure_ascii=False, indent=2)}
"""

print("=" * 80)
print("Testing Claude agent with commit f708f6970cc9")
print("=" * 80)
print()

cmd = [
    "claude",
    "-p",
    prompt,
    "--agent",
    "kernel-commit-analyzer",
]

print("Calling claude CLI...")
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    timeout=120,
    env={**subprocess.os.environ, "NO_COLOR": "1"},
)

print("\n" + "=" * 80)
print("STDOUT:")
print("=" * 80)
print(result.stdout)

print("\n" + "=" * 80)
print("STDERR:")
print("=" * 80)
print(result.stderr)

print("\n" + "=" * 80)
print("ANALYSIS:")
print("=" * 80)

output = result.stdout.strip()

# Try to parse as JSON
try:
    # Strip markdown if present
    if "```json" in output:
        json_start = output.find("```json") + 7
        json_end = output.find("```", json_start)
        output = output[json_start:json_end].strip()
    elif "```" in output:
        json_start = output.find("```") + 3
        json_end = output.rfind("```")
        output = output[json_start:json_end].strip()

    analysis = json.loads(output)
    print("✓ Valid JSON!")
    print(f"Keys: {list(analysis.keys())}")

    if "score_breakdown" in analysis:
        print(f"score_breakdown keys: {list(analysis['score_breakdown'].keys())}")
        bd = analysis["score_breakdown"]
        has_nonzero = any(isinstance(v, (int, float)) and v > 0 for v in bd.values())
        print(f"Has non-zero values: {has_nonzero}")
    else:
        print("⚠ Missing score_breakdown!")

    print(f"\nFull response:")
    print(json.dumps(analysis, indent=2, ensure_ascii=False))

except json.JSONDecodeError as e:
    print(f"✗ JSON parse error: {e}")
    print(f"\nRaw output (first 500 chars):")
    print(output[:500])
