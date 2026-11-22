"""Recipe rankers: the utility-based core method and the plain-overlap baseline."""
from recipes import RecipeIndex


class Ranker:
    """Abstract ranker. Subclasses implement score(); rank() applies the user's constraints."""

    def score(self, r, have):
        raise NotImplementedError

    def rank(self, have, source, max_time=None, max_missing=None, k=5):
        """Return the top-k [(score, recipe)] that satisfy the constraints.

        `source` is a RecipeIndex (candidates are looked up) or any iterable of Recipe."""
        cands = source.candidates(have) if isinstance(source, RecipeIndex) else source
        out = []
        for r in cands:
            if max_time and r.minutes > max_time:
                continue
            if max_missing is not None and len(r.missing(have)) > max_missing:
                continue
            out.append((self.score(r, have), r))
        out.sort(key=lambda x: (-x[0], x[1].minutes, x[1].name))
        return out[:k]


class OverlapRanker(Ranker):
    """Baseline: number of matching ingredients only."""

    def score(self, r, have):
        return len(r.needed() & have)


class UtilityRanker(Ranker):
    """Core method: utility = coverage - W_MISSING * missing - W_TIME * minutes.

    Weights are fixed in advance (see scripts/evaluate_sensitivity.py for the sensitivity test)."""
    W_MISSING, W_TIME = 0.15, 0.002
    W_USED = 0.0  # optional extra term (share of the USER's items the recipe uses); 0 = exactly as proposed

    def __init__(self, w_missing=None, w_time=None, w_used=None):
        if w_missing is not None:
            self.W_MISSING = w_missing
        if w_time is not None:
            self.W_TIME = w_time
        if w_used is not None:
            self.W_USED = w_used

    def breakdown(self, r, have):
        cov, miss = r.coverage(have), len(r.missing(have))
        return {"coverage": round(cov, 3), "missing_penalty": round(self.W_MISSING * miss, 3),
                "time_penalty": round(self.W_TIME * r.minutes, 3)}

    def score(self, r, have):
        s = r.coverage(have) - self.W_MISSING * len(r.missing(have)) - self.W_TIME * r.minutes
        if self.W_USED:
            s += self.W_USED * len(r.needed() & have) / max(len(have), 1)
        return s
