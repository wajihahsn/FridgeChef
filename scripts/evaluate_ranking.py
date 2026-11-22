"""Utility ranker vs plain-overlap baseline on data/test_scenarios.json (seed 42).
Metrics: precision@5, NDCG@5, average number of missing ingredients in the top 5, average response time.

Step 1  python scripts/evaluate_ranking.py
        -> writes data/relevance_template.csv (columns: scenario_id, recipe, relevance, judge1..3).
        The three members judge each recipe: 0 = not useful, 1 = okay, 2 = great. Fill 'relevance'
        (or the judge columns; their mean is used), save as data/relevance.csv.
Step 2  python scripts/evaluate_ranking.py     -> metrics + results/ranking.png + results/ranking_missing.png

Demo shortcut:  python scripts/evaluate_ranking.py --auto-draft
        writes a DRAFT data/relevance.csv from a simple rule so the pipeline can be tried end to end.
        It is NOT human judgment: replace it with the team's judgments before reporting results."""
import csv
import json
import os
import random
import sys
import time

from common import RESULTS, SEED, p, recipes_path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from normalizer import IngredientNormalizer
from rankers import OverlapRanker, UtilityRanker
from recipes import RecipeIndex

random.seed(SEED)
ix = RecipeIndex(recipes_path())
norm = IngredientNormalizer(ix.vocab)
rankers = {"baseline": OverlapRanker(), "utility": UtilityRanker()}
scenarios = json.load(open(p("data", "test_scenarios.json"), encoding="utf-8"))

tops, haves, times = {}, {}, {n: [] for n in rankers}
for sc in scenarios:
    have = set(norm.normalize_list(sc["ingredients"]))
    haves[sc["id"]] = have
    cands = ix.candidates(have)
    tops[sc["id"]] = {}
    for n, rk in rankers.items():
        t0 = time.perf_counter()
        tops[sc["id"]][n] = [r for _, r in rk.rank(have, cands, k=5)]
        times[n].append((time.perf_counter() - t0) * 1000)

rel_path, tmpl_path = p("data", "relevance.csv"), p("data", "relevance_template.csv")


def pool():
    return {sid: sorted({r.name: r for rs in d.values() for r in rs}.values(), key=lambda r: r.name)
            for sid, d in tops.items()}


if "--auto-draft" in sys.argv:
    with open(rel_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "recipe", "relevance", "note"])
        for sid, recs in pool().items():
            have = haves[sid]
            for r in recs:
                used, miss = len(r.needed() & have), len(r.missing(have))
                g = 2 if (miss == 0 and used >= 2) or (miss <= 1 and used >= 3) else 1 if (used >= 2 and miss <= 2) else 0
                w.writerow([sid, r.name, g, "AUTO-DRAFT (not human judgment)"])
    print("DRAFT written to", rel_path, "- replace with the team's judgments before reporting results.")

if not os.path.exists(rel_path):
    with open(tmpl_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "recipe", "relevance", "judge1", "judge2", "judge3", "have", "recipe_ingredients"])
        for sid, recs in pool().items():
            for r in recs:
                w.writerow([sid, r.name, "", "", "", "", "; ".join(sorted(haves[sid])), "; ".join(sorted(r.ingredients))])
    print("Wrote", tmpl_path, "\nJudge each row (0/1/2), save as data/relevance.csv and run again.")
    sys.exit()

rel = {}
for row in csv.DictReader(open(rel_path, encoding="utf-8")):
    vals = [row.get("relevance")] if (row.get("relevance") or "").strip() else [row.get(f"judge{i}") for i in (1, 2, 3)]
    vals = [float(v) for v in vals if v not in (None, "")]
    rel[(int(row["scenario_id"]), row["recipe"])] = round(sum(vals) / len(vals)) if vals else 0

dcg = lambda g: sum((2 ** x - 1) / np.log2(i + 2) for i, x in enumerate(g))
res = {n: {"P@5": [], "NDCG@5": [], "missing": []} for n in rankers}
for sid, d in tops.items():
    ideal = sorted([v for (s, _), v in rel.items() if s == sid], reverse=True)[:5]
    for n, recs in d.items():
        g = [rel.get((sid, r.name), 0) for r in recs]
        res[n]["P@5"].append(sum(x >= 1 for x in g) / 5)
        res[n]["NDCG@5"].append(dcg(g) / dcg(ideal) if dcg(ideal) > 0 else 0)
        res[n]["missing"].append(np.mean([len(r.missing(haves[sid])) for r in recs]) if recs else 0)

print(f"{len(scenarios)} scenarios, {len(ix.recipes)} recipes, seed {SEED}")
for n in res:
    print(f"{n:9s} P@5={np.mean(res[n]['P@5']):.3f}  NDCG@5={np.mean(res[n]['NDCG@5']):.3f}  "
          f"avg missing={np.mean(res[n]['missing']):.2f}  avg time={np.mean(times[n]):.2f} ms")

x = np.arange(2)
fig, ax = plt.subplots(figsize=(6, 4))
for k, n in enumerate(res):
    vals = [np.mean(res[n]["P@5"]), np.mean(res[n]["NDCG@5"])]
    b = ax.bar(x + k * 0.35, vals, 0.35, label=n)
    ax.bar_label(b, fmt="%.2f")
ax.set_xticks(x + 0.175, ["Precision@5", "NDCG@5"]); ax.set_ylim(0, 1.1); ax.legend(); ax.set_title("Ranking: utility vs baseline")
fig.savefig(os.path.join(RESULTS, "ranking.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
fig, ax = plt.subplots(figsize=(6, 4))
b = ax.bar(list(res), [np.mean(res[n]["missing"]) for n in res], color=["#999", "#1c9a5b"])
ax.bar_label(b, fmt="%.2f"); ax.set_title("Average missing ingredients in top 5 (lower is better)")
fig.savefig(os.path.join(RESULTS, "ranking_missing.png"), dpi=150, bbox_inches="tight"); plt.close(fig)
print("saved results/ranking.png and results/ranking_missing.png")
