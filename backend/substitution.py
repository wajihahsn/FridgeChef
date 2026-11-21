"""Substitution suggestions (proposal technique 3): curated rule table vs Word2Vec embeddings.

Both substituters implement suggest(missing, have) and only ever propose ingredients the user HAS,
each with a short human-readable reason."""
import hashlib
import os
import random

from normalizer import STAPLES

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")

# missing ingredient -> [(replacement, reason), ...] in order of preference.
RULES = {
    "butter": [("margarine", "same fat content and texture"), ("oil", "liquid fat works for sauteing and baking"),
               ("ghee", "clarified butter, same flavour")],
    "milk": [("yogurt", "thin it with a little water for the same creaminess"), ("cream", "richer, dilute with water"),
             ("coconut milk", "dairy-free creamy liquid")],
    "cream": [("milk", "lighter; add a little butter for richness"), ("yogurt", "tangy, creamy texture"),
              ("coconut milk", "rich dairy-free alternative")],
    "yogurt": [("cream", "similar creamy texture"), ("milk", "thinner but mild and creamy"),
               ("sour cream", "same tang and thickness")],
    "sour cream": [("yogurt", "same tang and thickness"), ("cream", "creamy, add a squeeze of lemon")],
    "egg": [("banana", "binds baked goods; adds sweetness"), ("yogurt", "adds moisture and binding"),
            ("flour", "thickens and binds in patties")],
    "lemon": [("lime", "same citrus acidity"), ("vinegar", "provides the sourness"), ("orange", "milder citrus note")],
    "lime": [("lemon", "same citrus acidity"), ("vinegar", "provides the sourness")],
    "rice": [("pasta", "similar starchy base"), ("quinoa", "similar grain texture"), ("couscous", "quick-cooking grain")],
    "pasta": [("rice", "similar starchy base"), ("noodles", "same shape and role"), ("couscous", "quick-cooking grain")],
    "noodles": [("pasta", "same shape and role"), ("rice", "starchy base")],
    "chicken": [("turkey", "very similar lean white meat"), ("tofu", "plant protein that absorbs flavour"),
                ("mushroom", "meaty texture"), ("chickpea", "plant protein"), ("lentil", "hearty plant protein")],
    "beef": [("lamb", "similar rich red meat"), ("mushroom", "meaty, savoury texture"), ("lentil", "hearty plant protein")],
    "pork": [("chicken", "similar mild meat"), ("beef", "similar richness")],
    "turkey": [("chicken", "very similar lean white meat")],
    "bacon": [("ham", "similar smoky cured pork"), ("sausage", "salty, smoky pork")],
    "ham": [("bacon", "similar smoky cured pork"), ("sausage", "salty pork")],
    "shrimp": [("fish", "seafood alternative"), ("chicken", "quick-cooking protein")],
    "fish": [("shrimp", "seafood alternative"), ("tuna", "same sea flavour")],
    "tuna": [("fish", "same sea flavour"), ("chickpea", "flaky plant-based option")],
    "cheese": [("cream", "adds richness"), ("yogurt", "adds tang and creaminess"), ("mozzarella", "melts the same way"),
               ("parmesan", "salty, sharp cheese flavour")],
    "mozzarella": [("cheese", "melts the same way"), ("cream", "adds richness")],
    "parmesan": [("cheese", "salty, sharp cheese flavour")],
    "onion": [("shallot", "milder onion flavour"), ("green onion", "mild onion flavour"), ("garlic", "savoury aromatic base")],
    "shallot": [("onion", "stronger but same family"), ("green onion", "mild onion flavour")],
    "green onion": [("onion", "stronger; use less"), ("shallot", "mild onion flavour")],
    "garlic": [("onion", "savoury aromatic base"), ("ginger", "pungent aromatic"), ("shallot", "mild savoury aroma")],
    "ginger": [("garlic", "pungent aromatic"), ("cumin", "warm spice note")],
    "bread": [("tortilla", "flat wrap instead of slices"), ("rice", "starchy base")],
    "tortilla": [("bread", "flat bread wrap"), ("pita", "flat bread wrap")],
    "pita": [("tortilla", "flat bread wrap"), ("bread", "flat bread wrap")],
    "potato": [("sweet potato", "same starchy texture"), ("rice", "starchy filler"), ("pasta", "starchy filler")],
    "sweet potato": [("potato", "same starchy texture"), ("carrot", "sweet, soft root vegetable")],
    "tomato": [("bell pepper", "juicy, slightly sweet vegetable"), ("tomato sauce", "concentrated tomato flavour")],
    "tomato sauce": [("tomato", "cook it down into a sauce"), ("tomato paste", "dilute with water")],
    "tomato paste": [("tomato sauce", "reduce it for a thicker sauce"), ("tomato", "cook it down")],
    "spinach": [("kale", "similar leafy green"), ("cabbage", "leafy, mild flavour"), ("lettuce", "leafy green")],
    "kale": [("spinach", "similar leafy green"), ("cabbage", "sturdy leafy green")],
    "lettuce": [("spinach", "fresh leafy green"), ("cabbage", "crunchy leaves")],
    "cabbage": [("lettuce", "crunchy leaves"), ("kale", "sturdy leafy green")],
    "broccoli": [("cauliflower", "same family, same cooking time"), ("green bean", "green crunchy vegetable")],
    "cauliflower": [("broccoli", "same family, same cooking time")],
    "zucchini": [("cucumber", "similar mild, watery vegetable"), ("eggplant", "similar soft texture when cooked")],
    "eggplant": [("zucchini", "similar soft texture when cooked"), ("mushroom", "meaty, absorbs flavour")],
    "cucumber": [("zucchini", "similar mild, watery vegetable"), ("celery", "fresh crunch")],
    "bell pepper": [("tomato", "juicy and sweet"), ("carrot", "sweet and crunchy")],
    "carrot": [("sweet potato", "sweet root vegetable"), ("bell pepper", "sweet and crunchy")],
    "celery": [("cucumber", "fresh crunch"), ("carrot", "adds crunch and sweetness")],
    "mushroom": [("eggplant", "meaty, absorbs flavour"), ("zucchini", "soft texture when cooked")],
    "chickpea": [("kidney bean", "similar protein-rich bean"), ("lentil", "protein-rich legume"), ("bean", "similar texture")],
    "kidney bean": [("chickpea", "similar protein-rich bean"), ("black bean", "similar bean texture"), ("lentil", "protein-rich legume")],
    "black bean": [("kidney bean", "similar bean texture"), ("chickpea", "protein-rich bean")],
    "lentil": [("chickpea", "protein-rich legume"), ("kidney bean", "protein-rich legume"), ("rice", "starchy filler")],
    "tofu": [("chicken", "protein with similar texture"), ("egg", "soft protein"), ("chickpea", "plant protein")],
    "flour": [("breadcrumb", "binds and thickens"), ("oat", "ground oats can replace flour")],
    "breadcrumb": [("flour", "dry coating or binder"), ("oat", "crunchy dry coating")],
    "oat": [("flour", "dry base for batters"), ("rice", "mild grain")],
    "honey": [("maple syrup", "liquid natural sweetener"), ("sugar", "sweetens; add a splash of water")],
    "maple syrup": [("honey", "liquid natural sweetener"), ("sugar", "sweetens; add a splash of water")],
    "brown sugar": [("sugar", "plain sugar; add a drop of honey"), ("honey", "sweet and moist")],
    "vinegar": [("lemon", "provides acidity"), ("lime", "provides acidity")],
    "soy sauce": [("salt", "adds saltiness; add a splash of water"), ("worcestershire sauce", "salty umami")],
    "coconut milk": [("cream", "rich creamy liquid"), ("milk", "lighter creamy liquid")],
    "cilantro": [("parsley", "fresh green herb"), ("basil", "fresh green herb")],
    "parsley": [("cilantro", "fresh green herb"), ("basil", "fresh green herb")],
    "basil": [("parsley", "fresh green herb"), ("oregano", "Italian-style herb")],
    "oregano": [("basil", "Italian-style herb"), ("thyme", "similar savoury herb")],
    "thyme": [("oregano", "similar savoury herb"), ("rosemary", "woody savoury herb")],
    "rosemary": [("thyme", "woody savoury herb"), ("oregano", "savoury herb")],
    "cumin": [("coriander", "warm earthy spice"), ("chili powder", "warm spice blend")],
    "chili": [("chili powder", "same heat"), ("paprika", "milder heat and colour"), ("bell pepper", "same shape, no heat")],
    "chili powder": [("paprika", "milder heat and colour"), ("chili", "fresh heat")],
    "paprika": [("chili powder", "similar colour and heat"), ("bell pepper", "mild pepper flavour")],
    "peanut butter": [("tahini", "nutty spread"), ("butter", "rich fat")],
    "apple": [("pear", "similar crisp sweet fruit"), ("banana", "sweet soft fruit")],
    "banana": [("apple", "sweet, soft when cooked"), ("honey", "adds sweetness")],
    "orange": [("lemon", "citrus note"), ("apple", "sweet fruit")],
    "corn": [("pea", "sweet small vegetable"), ("carrot", "sweet vegetable")],
    "pea": [("corn", "sweet small vegetable"), ("green bean", "green vegetable")],
    "green bean": [("pea", "green vegetable"), ("broccoli", "green vegetable")],
    "avocado": [("cream", "creamy, rich texture"), ("yogurt", "creamy, rich texture")],
}


class Substituter:
    """Abstract: suggest(missing, have) -> list of dicts {for, use, source, reason}."""

    def suggest(self, missing, have):
        raise NotImplementedError


class RuleSubstituter(Substituter):
    """Curated rule table filtered by what the user has."""
    source = "rule"

    def suggest(self, missing, have, limit=2):
        return [{"for": missing, "use": s, "source": self.source, "reason": why}
                for s, why in RULES.get(missing, []) if s in have][:limit]


class EmbeddingSubstituter(Substituter):
    """Word2Vec trained on recipe ingredient lists; nearest neighbours filtered by what the user has.
    The trained model is cached in models/ so later runs start instantly and offline."""
    source = "embedding"
    MIN_SIMILARITY = 0.30
    NEIGHBOURS = 8  # a replacement must be among the ingredient's closest neighbours overall

    def __init__(self, recipes, cache=True, model_dir=MODEL_DIR):
        self.m = None
        try:
            from gensim.models import Word2Vec
        except ImportError:
            return
        base = [sorted(r.ingredients) for r in recipes]
        sig = hashlib.md5(("v2|" + "|".join(" ".join(s) for s in base)).encode()).hexdigest()[:12]
        path = os.path.join(model_dir, f"ingredient_w2v_{sig}.model")
        if cache and os.path.exists(path):
            try:
                self.m = Word2Vec.load(path)
                return
            except Exception:
                pass
        try:
            # An ingredient list is a set, so word order carries no meaning: shuffle it (seeded) and, for
            # small datasets, repeat each recipe a few times so a small window still sees varied contexts.
            rnd = random.Random(42)
            copies = 5 if len(base) < 5000 else 1
            sentences = []
            for s in base:
                for _ in range(copies):
                    t = s[:]
                    rnd.shuffle(t)
                    sentences.append(t)
            self.m = Word2Vec(sentences, vector_size=32 if copies > 1 else 50, window=5, min_count=2, sg=1,
                              negative=10, seed=42, workers=1, epochs=10)
            if cache:
                os.makedirs(model_dir, exist_ok=True)
                for old in os.listdir(model_dir):  # drop stale caches of other datasets
                    if old.startswith("ingredient_w2v_"):
                        os.remove(os.path.join(model_dir, old))
                self.m.save(path)
        except Exception:
            self.m = None

    @property
    def available(self):
        return self.m is not None

    def suggest(self, missing, have, limit=2):
        if not self.m or missing not in self.m.wv:
            return []
        out = []
        for w, sim in self.m.wv.most_similar(missing, topn=self.NEIGHBOURS):
            if w in have and w not in STAPLES and sim >= self.MIN_SIMILARITY:
                out.append({"for": missing, "use": w, "source": self.source,
                            "reason": f"used in similar recipes (similarity {sim:.2f})"})
        return out[:limit]


class CombinedSubstituter(Substituter):
    """Runs both methods so the UI (and the evaluation) can compare them."""

    def __init__(self, recipes, **kw):
        self.rules, self.emb = RuleSubstituter(), EmbeddingSubstituter(recipes, **kw)

    def suggest(self, missing, have, method="both", limit=2):
        out = []
        if method in ("both", "rule"):
            out += self.rules.suggest(missing, have, limit)
        if method in ("both", "embedding"):
            seen = {o["use"] for o in out}
            out += [o for o in self.emb.suggest(missing, have, limit) if o["use"] not in seen]
        return out
