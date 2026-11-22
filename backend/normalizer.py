"""Ingredient text normalization (proposal technique 1).

Turns messy lines such as "2 cloves minced garlic" or "Ripe Tomatoes" into one canonical
ingredient name ("garlic", "tomato") using
  1. rules (strip quantities, units, descriptors, brackets, text after a comma),
  2. a small rule-based lemmatizer (plural -> singular),
  3. a synonym table (aubergine -> eggplant),
  4. fuzzy matching against the known vocabulary (RapidFuzz, with a difflib fallback).
"""
import difflib
import re

try:  # RapidFuzz is the library named in the proposal; difflib keeps the app alive without it.
    from rapidfuzz import fuzz, process
except ImportError:  # pragma: no cover
    fuzz = process = None

# Assumed to be in every kitchen (proposal 3.3): never counted as "missing".
STAPLES = frozenset({"salt", "water", "oil", "pepper", "sugar", "olive oil", "vegetable oil", "cooking oil"})

UNITS = (r"cups?|tbsp|tsp|tbs|tablespoons?|teaspoons?|g|kg|mg|ml|l|oz|lbs?|pounds?|ounces?|grams?|"
         r"cloves?|slices?|pieces?|cans?|pinch|dash|handfuls?|sprigs?|stalks?|bunch(?:es)?|packages?|"
         r"pkg|jars?|bottles?|sticks?|heads?|knobs?|fl")

# Descriptor / preparation words that do not change which ingredient it is.
DESC = frozenset({
    "fresh", "freshly", "minced", "chopped", "diced", "sliced", "grated", "shredded", "crushed", "ground",
    "large", "small", "medium", "big", "ripe", "boneless", "skinless", "cooked", "raw", "whole", "finely",
    "thinly", "roughly", "coarsely", "optional", "dried", "frozen", "canned", "peeled", "seeded", "trimmed",
    "halved", "quartered", "melted", "softened", "unsalted", "salted", "lean", "extra", "virgin", "plain",
    "hot", "cold", "warm", "boiled", "fried", "toasted", "packed", "heaping", "level", "good", "quality",
})
STOPWORDS = frozenset({"of", "and", "or", "a", "an", "the", "to", "taste", "for", "about", "some", "few",
                       "more", "plus", "with", "into", "cut", "pieces", "if", "needed", "your", "favorite"})

# Words that look plural but are not, or whose plural is irregular.
KEEP = frozenset({"hummus", "asparagus", "couscous", "molasses", "swiss", "brussels", "citrus", "watercress",
                  "lemongrass", "grits"})
IRREGULAR = {"leaves": "leaf", "loaves": "loaf", "halves": "half", "knives": "knife", "tomatoes": "tomato",
             "potatoes": "potato", "mangoes": "mango", "anchovies": "anchovy", "cookies": "cookie",
             "brussels": "brussels", "chilies": "chili", "chillies": "chili", "olives": "olive",
             "cloves": "clove", "eggs": "egg"}

# Alternative names -> canonical name used in the recipe vocabulary.
SYNONYMS = {
    "scallion": "green onion", "spring onion": "green onion", "aubergine": "eggplant", "brinjal": "eggplant",
    "capsicum": "bell pepper", "sweet pepper": "bell pepper", "coriander": "cilantro", "coriander leaf": "cilantro",
    "courgette": "zucchini", "garbanzo bean": "chickpea", "garbanzo": "chickpea", "black pepper": "pepper",
    "ground pepper": "pepper", "peppercorn": "pepper", "cooking oil": "oil", "vegetable oil": "oil",
    "extra virgin olive oil": "olive oil", "icing sugar": "powdered sugar", "caster sugar": "sugar",
    "white sugar": "sugar", "granulated sugar": "sugar", "plain flour": "flour", "all purpose flour": "flour",
    "wheat flour": "flour", "curd": "yogurt", "yoghurt": "yogurt", "prawn": "shrimp", "mince": "beef", "potatoe": "potato", "tomatoe": "tomato",
    "chile": "chili", "chilli": "chili", "chilli pepper": "chili", "green chili": "chili", "green chilli": "chili",
    "cheddar": "cheese", "cheddar cheese": "cheese", "mozzarella cheese": "mozzarella", "heavy cream": "cream",
    "whipping cream": "cream", "double cream": "cream", "whole milk": "milk", "skim milk": "milk",
    "spaghetti": "pasta", "penne": "pasta", "macaroni": "pasta", "noodle": "noodles", "white rice": "rice",
    "basmati rice": "rice", "brown rice": "rice", "bread crumb": "breadcrumb", "baking soda": "baking soda",
    "bicarbonate of soda": "baking soda", "garlic clove": "garlic", "bean": "kidney bean", "dry bean": "kidney bean", "ginger root": "ginger",
}


def singular(w):
    """Tiny rule-based lemmatizer for ingredient nouns (plural -> singular)."""
    if w in KEEP or len(w) < 4:
        return w
    if w in IRREGULAR:
        return IRREGULAR[w]
    if w.endswith(("ss", "us", "is")):
        return w
    if w.endswith("ies"):
        return w[:-3] + "y"
    if w.endswith(("oes", "ches", "shes", "xes")):
        return w[:-2]
    return w[:-1] if w.endswith("s") else w


def clean(text):
    """Rule-based cleaning + lemmatization + synonym lookup. Returns '' for unusable text."""
    t = re.sub(r"\(.*?\)", " ", str(text).lower())
    t = t.split(",")[0]
    t = re.sub(r"[-/]", " ", t)
    t = re.sub(r"[^a-z ]", " ", t)
    raw = t.split()
    words = [w for w in raw if w not in DESC and w not in STOPWORDS and not re.fullmatch(UNITS, w)]
    if not words:  # e.g. the spice "cloves": everything looked like a unit -> keep the bare word
        words = [w for w in raw if w not in STOPWORDS and w not in DESC][:1]
    name = " ".join(singular(w) for w in words)
    return SYNONYMS.get(name, name)


class IngredientNormalizer:
    """Maps user text to the recipe vocabulary. attributes: vocabulary, stopwords."""

    def __init__(self, vocab, stopwords=STOPWORDS, cutoff=86):
        self.vocab = set(vocab)
        self.vocab_list = sorted(self.vocab)
        self.stopwords = stopwords
        self.cutoff = cutoff

    def _fuzzy(self, c):
        """Best vocabulary match for a (probably misspelled) name, or None.
        Accept a close match (ratio >= cutoff), or a looser one (>= 70) when the first letter
        agrees and the word is long enough for a typo to be the likely explanation."""
        if len(c) < 4 or not self.vocab_list:
            return None
        if process is not None:
            top = process.extract(c, self.vocab_list, scorer=fuzz.ratio, limit=3, score_cutoff=70)
            ranked = [(w, s) for w, s, _ in top]
        else:
            ranked = [(w, difflib.SequenceMatcher(None, c, w).ratio() * 100)
                      for w in difflib.get_close_matches(c, self.vocab_list, n=3, cutoff=0.7)]
        for w, s in ranked:
            if s >= self.cutoff or (len(c) >= 5 and w[0] == c[0] and abs(len(w) - len(c)) <= 1):
                return w
        return None

    def match(self, text):
        """Return (canonical_name, known) where known tells whether it exists in the vocabulary."""
        c = clean(text)
        if not c:
            return "", False
        if c in self.vocab:
            return c, True
        f = self._fuzzy(c)
        if f:
            return f, True
        words = c.split()
        if len(words) > 1:  # "cherry tomato" -> "tomato", "chicken breast" -> "chicken"
            for tail in (words[-1], words[0]):
                if tail in self.vocab:
                    return tail, True
        return c, False

    def normalize(self, text):
        return self.match(text)[0]

    def normalize_list(self, lines):
        return [x for x in dict.fromkeys(self.normalize(l) for l in lines) if x]
