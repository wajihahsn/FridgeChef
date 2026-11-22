"""Sensitivity test of the utility weights (proposal section 4): how much does the top-5 change when the
fixed weights W_MISSING and W_TIME are varied? Needs no human labels.
Usage: python scripts/evaluate_sensitivity.py   -> results/sensitivity.png + printed table"""
import json
import os

from common import RESULTS, p, recipes_path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from normalizer import IngredientNormalizer
from rankers import UtilityRanker
from recipes import RecipeIndex

ix = RecipeIndex(recipes_path())
norm = IngredientNormalizer(ix.vocab)
scen = [set(norm.normalize_list(s["ingredients"])) for s in json.load(open(p("data", "test_scenarios.json"), encoding="utf-8"))]
base = UtilityRanker()
ref = [[r.name for _, r in base.rank(h, ix, k=5)] for h in scen]
WM, WT = [0.05, 0.10, 0.15, 0.20, 0.30], [0.0, 0.001, 0.002, 0.005, 0.01]


def overlap(a, b):
    return len(set(a) & set(b)) / 5 if a or b else 1.0


grid_overlap = np.zeros((len(WM), len(WT)))
grid_missing = np.zeros_like(grid_overlap)
for i, wm in enumerate(WM):
    for j, wt in enumerate(WT):
        rk = UtilityRanker(wm, wt)
        tops = [[r for _, r in rk.rank(h, ix, k=5)] for h in scen]
        grid_overlap[i, j] = np.mean([overlap([r.name for r in t], f) for t, f in zip(tops, ref)])
        grid_missing[i, j] = np.mean([np.mean([len(r.missing(h)) for r in t]) if t else 0 for t, h in zip(tops, scen)])

print(f"Top-5 overlap with the default weights (W_MISSING={base.W_MISSING}, W_TIME={base.W_TIME}); rows W_MISSING, cols W_TIME")
print("          " + "  ".join(f"{w:6}" for w in WT))
for i, wm in enumerate(WM):
    print(f"{wm:8.2f}  " + "  ".join(f"{v:6.2f}" for v in grid_overlap[i]))
print(f"\nmean overlap over the grid: {grid_overlap.mean():.2f}  (min {grid_overlap.min():.2f})")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
for ax, g, title in ((axes[0], grid_overlap, "Top-5 stability vs default weights"), (axes[1], grid_missing, "Avg missing ingredients in top 5")):
    im = ax.imshow(g, cmap="Greens" if g is grid_overlap else "Oranges")
    ax.set_xticks(range(len(WT)), WT); ax.set_yticks(range(len(WM)), WM)
    ax.set_xlabel("W_TIME"); ax.set_ylabel("W_MISSING"); ax.set_title(title)
    for (i, j), v in np.ndenumerate(g):
        ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046)
fig.savefig(os.path.join(RESULTS, "sensitivity.png"), dpi=150, bbox_inches="tight")
print("saved results/sensitivity.png")
