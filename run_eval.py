"""Offline evaluation. Backup for when you don't want to burn quota live.

Writes eval_results.json next to the data files.
"""
import json, os, sys
from engine import llm, retrieval, rules as rules_mod, pipeline

DATA = os.path.join(os.path.dirname(__file__), "data")

key = os.environ.get("GEMINI_API_KEY")
if not key:
    sys.exit("Set GEMINI_API_KEY first.")
llm.configure(key)

catalogue = retrieval.load_catalogue(os.path.join(DATA, "mm_catalogue.json"))
matrix = retrieval.build_index(catalogue)
rules_cfg = rules_mod.load_rules(os.path.join(DATA, "tier_rules.yaml"))
gold = json.load(open(os.path.join(DATA, "gold_requirements.json")))["requirements"]

results = []
for g in gold:
    t = pipeline.run(g["text"], catalogue, matrix, rules_cfg)
    if "validation" not in t:
        print(f"{g['id']}: FAILED {t.get('errors')}")
        continue
    pred = t["validation"]["final_tier"]
    ok = pred == g["expected_tier"]
    print(f"{g['id']}: expected {g['expected_tier']:20s} got {pred:20s} {'ok' if ok else 'MISS'}")
    results.append({
        "id": g["id"], "expected": g["expected_tier"], "predicted": pred,
        "correct": ok, "citation_valid": t["validation"]["citation_valid"],
        "difficulty": g["difficulty"],
    })

n = len(results)
print(f"\nTier accuracy   {sum(r['correct'] for r in results)/n:.0%}")
print(f"Citations valid {sum(r['citation_valid'] for r in results)/n:.0%}")
json.dump(results, open(os.path.join(DATA, "eval_results.json"), "w"), indent=2)
