"""Bootstrap draft GT files from agent_research output."""
import json
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output" / "agent-research"
GT_DIR = Path(__file__).resolve().parent.parent / "ground-truth"
DRAFT_DIR = GT_DIR / "drafts"
DRAFT_DIR.mkdir(parents=True, exist_ok=True)

by_domain = {}
for json_file in sorted(OUTPUT_DIR.rglob("*.json")):
    if json_file.parent.name == "batch":
        continue
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    domain = data.get("domain", "")
    category = data.get("category", "")
    if not domain or not category:
        continue
    if domain not in by_domain:
        by_domain[domain] = {
            "company": data.get("company", domain),
            "domain": domain,
            "tier": 2,
            "verified_date": datetime.now().strftime("%Y-%m-%d"),
            "categories": {},
        }
    extracted = data.get("extracted")
    if extracted:
        by_domain[domain]["categories"][category] = {
            **extracted,
            "_confidence": "draft-agent",
            "_sources": data.get("sources", []),
        }

for domain, gt_data in sorted(by_domain.items()):
    safe_name = domain.replace(".", "_").replace("/", "_")
    out_path = DRAFT_DIR / f"{safe_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(gt_data, f, indent=2, ensure_ascii=False)
    cat_count = len(gt_data["categories"])
    print(f"  {domain}: {cat_count} categories -> {out_path}")

for domain, gt_data in sorted(by_domain.items()):
    missing = 3 - len(gt_data["categories"])
    if missing > 0:
        print(f"  WARNING: {domain} missing {missing} categories")
