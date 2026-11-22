"""Convert a Food.com recipe CSV into data/recipes.json (filtered, normalized subset, seed 42).

Supported files (auto-detected):
  * the dataset named in the proposal, Kaggle "irkaal/foodcom-recipes-and-reviews"  -> recipes.csv
  * the older Food.com "RAW_recipes.csv" (shuyangli94/food-com-recipes-and-user-interactions)

Usage: python scripts/prepare_data.py data/raw/recipes.csv [--n 20000] [--vocab 1500]

Steps: keep recipes with 0 < minutes <= 180 and 3-12 ingredients -> clean every ingredient line with the
project's normalizer -> keep only the most frequent ingredient names (vocabulary limit, proposal risk 2);
rarer names are mapped to a frequent name that is their last word(s) ("sharp cheddar cheese" -> "cheese")
and recipes that still contain an unmapped ingredient are dropped -> sample N recipes with seed 42."""
import argparse
import ast
import json
import re
from collections import Counter

from common import SEED, p

import pandas as pd

from normalizer import STAPLES, clean

ap = argparse.ArgumentParser(description="Prepare the Food.com recipe subset")
ap.add_argument("csv")
ap.add_argument("--n", type=int, default=20000, help="number of recipes to keep")
ap.add_argument("--vocab", type=int, default=1500, help="size of the ingredient vocabulary")
ap.add_argument("--out", default=p("data", "recipes.json"))
a = ap.parse_args()


def r_vector(s):
    """Parse R-style  c("a", "b")  strings used by the irkaal dataset."""
    if not isinstance(s, str):
        return []
    return [x.replace('\\"', '"') for x in re.findall(r'"((?:[^"\\]|\\.)*)"', s)]


def iso_minutes(s):
    """'PT1H30M' -> 90."""
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?", str(s))
    return int(m.group(1) or 0) * 60 + int(m.group(2) or 0) if m else 0


df = pd.read_csv(a.csv)
cols = set(df.columns)
if {"name", "minutes", "ingredients", "steps"} <= cols:  # RAW_recipes.csv
    rows = ((r["name"], int(r["minutes"]), ast.literal_eval(r["ingredients"]), ast.literal_eval(r["steps"]))
            for _, r in df.iterrows() if isinstance(r["name"], str))
elif {"Name", "RecipeIngredientParts", "RecipeInstructions"} <= cols and ("TotalTime" in cols or "CookTime" in cols):
    tcol = "TotalTime" if "TotalTime" in cols else "CookTime"
    rows = ((r["Name"], iso_minutes(r[tcol]), r_vector(r["RecipeIngredientParts"]), r_vector(r["RecipeInstructions"]))
            for _, r in df.iterrows() if isinstance(r["Name"], str))
else:
    raise SystemExit(f"{a.csv}: unknown format. Expected Food.com recipes.csv or RAW_recipes.csv. Columns: {sorted(cols)[:12]}")

parsed = []
for name, mins, raw_ings, steps in rows:
    if not 0 < mins <= 180 or not 3 <= len(raw_ings) <= 12:
        continue
    ings = [i for i in (clean(x) for x in raw_ings) if i]
    if len(set(ings) - STAPLES) >= 2:
        parsed.append((name.strip().title(), mins, ings, [str(s).strip() for s in steps][:8]))
print(len(parsed), "recipes after time/size filter")

freq = Counter(i for _, _, ings, _ in parsed for i in set(ings))
vocab = {w for w, _ in freq.most_common(a.vocab)}


def to_vocab(i):
    if i in vocab:
        return i
    words = i.split()
    for k in range(1, len(words)):  # longest suffix first
        if " ".join(words[k:]) in vocab:
            return " ".join(words[k:])
    return None


out = []
for name, mins, ings, steps in parsed:
    mapped = [to_vocab(i) for i in ings]
    if all(mapped):
        out.append({"name": name, "minutes": mins, "ingredients": sorted(set(mapped)), "steps": steps})
print(len(out), f"recipes fully covered by the {len(vocab)}-ingredient vocabulary")
if not out:
    raise SystemExit("No recipes left after filtering - is this the right file?")
out = pd.DataFrame(out).sample(min(a.n, len(out)), random_state=SEED).to_dict("records")
with open(a.out, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False)
print("saved", len(out), "recipes to", a.out, " (restart the app to use it)")
