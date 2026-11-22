"""Recipe data model and the ingredient -> recipes lookup index."""
import json
from collections import defaultdict
from dataclasses import dataclass, field

from normalizer import STAPLES, clean


@dataclass(frozen=True)
class Recipe:
    name: str
    minutes: int
    ingredients: frozenset
    steps: tuple = field(default_factory=tuple)
    needed_set: frozenset = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        # Precomputed once: ranking calls needed()/missing() thousands of times per query.
        object.__setattr__(self, "needed_set", frozenset(self.ingredients) - STAPLES)

    @property
    def cooking_time(self):
        return self.minutes

    def needed(self):
        """Ingredients the user must really have (pantry staples are assumed available)."""
        return self.needed_set

    def missing(self, have):
        return self.needed_set - have

    def coverage(self, have):
        n = self.needed_set
        return len(n & have) / len(n) if n else 0.0


class RecipeIndex:
    """list of Recipe + inverted index ingredient -> recipe ids."""

    def __init__(self, path):
        self.path = path
        self.skipped = 0
        self.recipes = []
        self.load(path)

    def load(self, path):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        seen, recipes = set(), []
        for r in raw:
            try:
                ings = frozenset(c for c in map(clean, r["ingredients"]) if c)
                rec = Recipe(str(r["name"]).strip(), int(r["minutes"]), ings, tuple(r.get("steps", [])))
            except (KeyError, TypeError, ValueError):
                self.skipped += 1
                continue
            key = (rec.name.lower(), rec.ingredients)
            if not rec.needed_set or rec.minutes <= 0 or key in seen:
                self.skipped += 1
                continue
            seen.add(key)
            recipes.append(rec)
        if not recipes:
            raise ValueError(f"No usable recipes found in {path}")
        self.recipes = recipes
        self.vocab = sorted({i for r in recipes for i in r.ingredients})
        self.inv = defaultdict(list)
        for idx, r in enumerate(recipes):
            for i in r.needed_set:
                self.inv[i].append(idx)
        return self

    def frequent(self, n=300):
        """Most common ingredients first (used for the quick-add suggestions in the UI)."""
        return [w for w, _ in sorted(((i, len(v)) for i, v in self.inv.items()), key=lambda x: (-x[1], x[0]))][:n]

    def candidates(self, have):
        """Recipes that share at least one ingredient with `have`."""
        ids = set()
        for i in have:
            ids.update(self.inv.get(i, ()))
        return [self.recipes[i] for i in sorted(ids)]
