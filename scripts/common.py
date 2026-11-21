"""Shared helpers for the scripts (paths work from any current directory)."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
DATA, MODELS, RESULTS = (os.path.join(ROOT, d) for d in ("data", "models", "results"))
SEED = 42
for _d in (DATA, MODELS, RESULTS):
    os.makedirs(_d, exist_ok=True)


def p(*parts):
    return os.path.join(ROOT, *parts)


def recipes_path():
    full = p("data", "recipes.json")
    return full if os.path.exists(full) else p("data", "sample_recipes.json")


def split_indices(n, val_frac=0.2, seed=SEED):
    """Fixed train/held-out split shared by training and evaluation (same seed -> same images)."""
    import torch
    n_val = int(val_frac * n)
    perm = torch.randperm(n, generator=torch.Generator().manual_seed(seed)).tolist()
    return perm[n_val:], perm[:n_val]
