import json
import os

import pytest

from conftest import ROOT
from normalizer import STAPLES, IngredientNormalizer, clean
from rankers import OverlapRanker, UtilityRanker
from recipes import Recipe, RecipeIndex
from substitution import CombinedSubstituter, EmbeddingSubstituter, RuleSubstituter

SAMPLE = os.path.join(ROOT, "data", "sample_recipes.json")


# ---------- normalizer ----------
@pytest.mark.parametrize("raw,expected", [
    ("2 cloves minced garlic", "garlic"), ("Tomatoes", "tomato"), ("3 large eggs, beaten", "egg"),
    ("1/2 cup chopped fresh cilantro", "cilantro"), ("cloves", "clove"), ("Scallions", "green onion"),
    ("2 tbsp. olive oil", "olive oil"), ("Potatoes", "potato"), ("bay leaves", "bay leaf"),
    ("hummus", "hummus"), ("asparagus", "asparagus"), ("", ""), ("   ", ""), ("123", ""),
])
def test_clean(raw, expected):
    assert clean(raw) == expected


def test_fuzzy_and_fallbacks():
    n = IngredientNormalizer({"tomato", "egg", "cheese", "chicken", "pear", "pea"})
    assert n.normalize("tomatto") == "tomato"
    assert n.normalize("cheez") == "cheese"
    assert n.match("cherry tomato") == ("tomato", True)
    assert n.match("dragonfruit") == ("dragonfruit", False)
    assert n.match("pea") == ("pea", True)            # exact beats fuzzy
    assert n.match("peach")[1] is False               # not wrongly mapped to pea/pear


def test_normalize_list_dedupes():
    n = IngredientNormalizer({"tomato", "egg"})
    assert n.normalize_list(["Tomatoes", "tomato", "", "EGGS"]) == ["tomato", "egg"]


# ---------- recipes ----------
def test_recipe_methods():
    r = Recipe("A", 10, frozenset({"egg", "tomato", "salt"}))
    assert r.needed() == {"egg", "tomato"}               # staples ignored
    assert r.missing({"egg"}) == {"tomato"}
    assert r.coverage({"egg"}) == 0.5
    assert Recipe("S", 5, frozenset({"salt", "water"})).coverage(set()) == 0.0


def test_index_loads_and_skips_bad_rows(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps([
        {"name": "ok", "minutes": 10, "ingredients": ["2 eggs", "tomatoes"]},
        {"name": "dup", "minutes": 10, "ingredients": ["egg", "tomato"]},
        {"name": "ok", "minutes": 10, "ingredients": ["egg", "tomato"]},   # duplicate of the first
        {"name": "bad"}, {"name": "zero", "minutes": 0, "ingredients": ["egg"]},
        {"name": "onlysalt", "minutes": 5, "ingredients": ["salt"]},
    ]), encoding="utf-8")
    ix = RecipeIndex(str(f))
    assert [r.name for r in ix.recipes] == ["ok", "dup"] and ix.skipped == 4
    assert ix.vocab == ["egg", "tomato"]
    assert len(ix.candidates({"egg"})) == 2 and ix.candidates({"zzz"}) == []


def test_index_rejects_empty(tmp_path):
    f = tmp_path / "e.json"
    f.write_text("[]")
    with pytest.raises(ValueError):
        RecipeIndex(str(f))


# ---------- rankers ----------
def test_utility_prefers_fully_covered_recipe():
    a = Recipe("A", 10, frozenset({"egg", "tomato"}))
    b = Recipe("B", 10, frozenset({"egg", "tomato", "cheese", "rice"}))
    have = {"egg", "tomato"}
    assert UtilityRanker().rank(have, [a, b])[0][1].name == "A"
    assert OverlapRanker().score(a, have) == OverlapRanker().score(b, have) == 2  # baseline cannot tell them apart


def test_time_penalty_and_filters():
    fast, slow = Recipe("fast", 10, frozenset({"egg"})), Recipe("slow", 90, frozenset({"egg"}))
    assert [r.name for _, r in UtilityRanker().rank({"egg"}, [slow, fast])] == ["fast", "slow"]
    assert UtilityRanker().rank({"egg"}, [slow], max_time=30) == []
    r = Recipe("two", 10, frozenset({"egg", "rice", "tomato"}))
    assert UtilityRanker().rank({"egg"}, [r], max_missing=1) == []
    assert len(UtilityRanker().rank({"egg"}, [r], max_missing=2)) == 1


def test_ranker_accepts_index_and_is_deterministic():
    ix = RecipeIndex(SAMPLE)
    a = UtilityRanker().rank({"egg", "tomato"}, ix, k=5)
    b = UtilityRanker().rank({"egg", "tomato"}, ix.candidates({"egg", "tomato"}), k=5)
    assert [r.name for _, r in a] == [r.name for _, r in b] and len(a) == 5


def test_weights_are_configurable():
    r = Recipe("r", 100, frozenset({"egg", "rice"}))
    assert UtilityRanker(w_missing=0, w_time=0).score(r, {"egg"}) == 0.5
    assert UtilityRanker().breakdown(r, {"egg"})["time_penalty"] == 0.2


# ---------- substitution ----------
def test_rule_substituter_only_suggests_what_user_has():
    s = RuleSubstituter().suggest("butter", {"oil", "rice"})
    assert [x["use"] for x in s] == ["oil"] and s[0]["reason"]
    assert RuleSubstituter().suggest("butter", {"rice"}) == []
    assert RuleSubstituter().suggest("unobtainium", {"rice"}) == []


def test_embedding_substituter_filters_and_caches(tmp_path):
    ix = RecipeIndex(SAMPLE)
    e = EmbeddingSubstituter(ix.recipes, model_dir=str(tmp_path))
    assert e.available and any(f.startswith("ingredient_w2v_") for f in os.listdir(tmp_path))
    have = {"milk", "yogurt", "tomato", "egg"}
    out = e.suggest("cream", have)
    assert all(o["use"] in have and o["for"] == "cream" and "similarity" in o["reason"] for o in out)
    assert e.suggest("not-an-ingredient", have) == []
    e2 = EmbeddingSubstituter(ix.recipes, model_dir=str(tmp_path))   # loads from cache, identical output
    assert e2.suggest("cream", have) == out


def test_combined_methods(tmp_path):
    ix = RecipeIndex(SAMPLE)
    c = CombinedSubstituter(ix.recipes, model_dir=str(tmp_path))
    have = {"yogurt", "milk", "oil"}
    assert all(s["source"] == "rule" for s in c.suggest("cream", have, method="rule"))
    assert all(s["source"] == "embedding" for s in c.suggest("cream", have, method="embedding"))
    both = c.suggest("cream", have)
    assert len({s["use"] for s in both}) == len(both)


# ---------- data files ----------
def test_data_files_consistent():
    ix = RecipeIndex(SAMPLE)
    n = IngredientNormalizer(ix.vocab)
    scen = json.load(open(os.path.join(ROOT, "data", "test_scenarios.json"), encoding="utf-8"))
    assert len(scen) == 20
    for sc in scen:
        assert all(n.match(i)[1] for i in sc["ingredients"]), sc
    cases = json.load(open(os.path.join(ROOT, "data", "substitution_cases.json"), encoding="utf-8"))
    assert len(cases) == 30 and all(c["acceptable"] for c in cases)
    assert len(ix.recipes) >= 100 and ix.skipped == 0
    assert not (STAPLES & {i for r in ix.recipes for i in r.needed()})
