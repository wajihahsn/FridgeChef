"""Rule table vs Word2Vec substitutions on the 30 cases in data/substitution_cases.json.

Automatic (no humans needed): coverage (share of cases with any suggestion) and hit rate against the
acceptable-substitute list written for each case.  NOTE: the acceptable lists were written by hand from
cooking knowledge, like the rule table, so they favour the rule table; the human ratings are the main metric.

Human plausibility ratings (proposal section 7):
  Step 1  python scripts/evaluate_substitution.py  -> writes data/substitution_template.csv
  Step 2  each of the three members rates every suggestion 1-5 in the columns rater1..rater3 (or one 'rating'
          column), saves as data/substitution_ratings.csv
  Step 3  python scripts/evaluate_substitution.py  -> mean rating per method + results/substitution*.png"""
import csv
import json
import os

from common import RESULTS, p, recipes_path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from normalizer import IngredientNormalizer
from recipes import RecipeIndex
from substitution import CombinedSubstituter

ix = RecipeIndex(recipes_path())
norm = IngredientNormalizer(ix.vocab)
sub = CombinedSubstituter(ix.recipes)
cases = json.load(open(p("data", "substitution_cases.json"), encoding="utf-8"))

rows, stats = [], {m: {"answered": 0, "hit": 0, "n": 0} for m in ("rule", "embedding")}
for c in cases:
    have = set(norm.normalize_list(c["have"]))
    for m in stats:
        got = sub.suggest(c["missing"], have, method=m)
        stats[m]["n"] += 1
        stats[m]["answered"] += bool(got)
        stats[m]["hit"] += any(s["use"] in c["acceptable"] for s in got)
        rows += [[c["id"], c["missing"], ", ".join(sorted(have)), s["source"], s["use"], s["reason"]] for s in got]

print(f"{len(cases)} cases (Word2Vec trained on {len(ix.recipes)} recipes)")
for m, s in stats.items():
    print(f"{m:10s} coverage={s['answered']}/{s['n']}  hit-rate vs acceptable list={s['hit']}/{s['n']}")

fig, ax = plt.subplots(figsize=(6, 4))
x = np.arange(2)
for k, m in enumerate(stats):
    vals = [stats[m]["answered"] / stats[m]["n"], stats[m]["hit"] / stats[m]["n"]]
    b = ax.bar(x + k * 0.35, vals, 0.35, label=m); ax.bar_label(b, fmt="%.2f")
ax.set_xticks(x + 0.175, ["Coverage", "Hit rate"]); ax.set_ylim(0, 1.1); ax.legend()
ax.set_title("Substitution: rule table vs Word2Vec (automatic)")
fig.savefig(os.path.join(RESULTS, "substitution_auto.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

rate_path = p("data", "substitution_ratings.csv")
if os.path.exists(rate_path):
    tot = {}
    for r in csv.DictReader(open(rate_path, encoding="utf-8")):
        vals = [r.get("rating")] if (r.get("rating") or "").strip() else [r.get(f"rater{i}") for i in (1, 2, 3)]
        tot.setdefault(r["source"], []).extend(float(v) for v in vals if v not in (None, ""))
    means = {k: float(np.mean(v)) for k, v in tot.items() if v}
    print("human mean plausibility (1-5):", {k: round(v, 2) for k, v in means.items()})
    fig, ax = plt.subplots(figsize=(5, 4))
    b = ax.bar(list(means), list(means.values()), color=["#1c9a5b", "#4a6fd0"][:len(means)])
    ax.bar_label(b, fmt="%.2f"); ax.set_ylim(0, 5); ax.set_title("Mean substitution plausibility (1-5)")
    fig.savefig(os.path.join(RESULTS, "substitution.png"), dpi=150, bbox_inches="tight")
    print("saved results/substitution.png")
else:
    with open(p("data", "substitution_template.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "missing", "have", "source", "suggestion", "reason", "rating", "rater1", "rater2", "rater3"])
        w.writerows([[r[0], r[1], r[2], r[3], r[4], r[5], "", "", "", ""] for r in rows])
    print(len(rows), "suggestions written to data/substitution_template.csv. Rate 1-5, save as data/substitution_ratings.csv, rerun.")
