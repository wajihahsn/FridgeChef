"""FridgeChef Flask application (FridgeChefApp): connects normalizer, index, rankers,
substituters and the image classifier, and serves the web interface.

Run:  python backend/app.py        (options: --port 5001  --no-browser)"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory  # noqa: E402

from classifier import IngredientClassifier  # noqa: E402
from normalizer import STAPLES, IngredientNormalizer  # noqa: E402
from rankers import OverlapRanker, UtilityRanker  # noqa: E402
from recipes import RecipeIndex  # noqa: E402
from substitution import CombinedSubstituter  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_INGREDIENTS = 60


def default_data_path():
    full = os.path.join(ROOT, "data", "recipes.json")
    return full if os.path.exists(full) else os.path.join(ROOT, "data", "sample_recipes.json")


def _int_or_none(value, name, lo, hi):
    """Parse an optional integer filter; '' / None mean 'no limit'."""
    if value in (None, ""):
        return None
    try:
        v = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{name}' must be a whole number.")
    if not lo <= v <= hi:
        raise ValueError(f"'{name}' must be between {lo} and {hi}.")
    return v


def create_app(data_path=None, model_dir=None, use_embeddings_cache=True):
    app = Flask(__name__, static_folder=os.path.join(ROOT, "frontend"), static_url_path="")
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024  # photo upload limit
    index = RecipeIndex(data_path or default_data_path())
    norm = IngredientNormalizer(index.vocab)
    subs = CombinedSubstituter(index.recipes, cache=use_embeddings_cache)
    clf = IngredientClassifier(model_dir) if model_dir else IngredientClassifier()
    rankers = {"utility": UtilityRanker(), "baseline": OverlapRanker()}
    app.fc = {"index": index, "norm": norm, "subs": subs, "clf": clf, "rankers": rankers}

    def error(msg, code=400):
        return jsonify({"error": msg}), code

    @app.errorhandler(413)
    def too_big(_):
        return error("That photo is too large (limit 8 MB).", 413)

    @app.errorhandler(404)
    def not_found(_):
        return error("Not found.", 404)

    @app.errorhandler(500)
    def server_error(_):
        return error("Unexpected server error. Check the terminal for details.", 500)

    @app.get("/")
    def home():
        return send_from_directory(app.static_folder, "index.html")

    @app.get("/api/ingredients")
    def ingredients():
        return jsonify(index.vocab)

    @app.get("/api/status")
    def status():
        return jsonify({"recipes": len(index.recipes), "ingredients": len(index.vocab),
                        "image_model": clf.mode(), "image_hint": clf.reason(),
                        "word2vec": subs.emb.available, "popular": index.frequent(24),
                        "staples": sorted(STAPLES)})

    @app.post("/api/normalize")
    def normalize():
        d = request.get_json(silent=True) or {}
        lines = d.get("ingredients", [])
        if not isinstance(lines, list):
            return error("'ingredients' must be a list.")
        out = []
        for line in lines[:MAX_INGREDIENTS]:
            name, known = norm.match(str(line))
            if name:
                out.append({"input": str(line), "name": name, "known": known})
        return jsonify({"items": out})

    @app.post("/api/recommend")
    def recommend():
        t0 = time.perf_counter()
        d = request.get_json(silent=True)
        if not isinstance(d, dict):
            return error("Send a JSON body such as {\"ingredients\": [\"egg\", \"tomato\"]}.")
        lines = d.get("ingredients", [])
        if not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            return error("'ingredients' must be a list of text values.")
        try:
            max_time = _int_or_none(d.get("max_time"), "max_time", 1, 100000)
            max_missing = _int_or_none(d.get("max_missing"), "max_missing", 0, 50)
            k = _int_or_none(d.get("k", 5), "k", 1, 20) or 5
        except ValueError as e:
            return error(str(e))
        method = d.get("method", "utility")
        if method not in ("utility", "baseline", "compare"):
            return error("'method' must be utility, baseline or compare.")

        matched = [norm.match(l) for l in lines[:MAX_INGREDIENTS]]
        have = {n for n, _ in matched if n}
        unknown = sorted({n for n, known in matched if n and not known})
        base = {"have": sorted(have), "unknown": unknown, "results": [], "method": method}
        if not have:
            return jsonify(base)

        cands = index.candidates(have)

        def run(name):
            ranker = rankers[name]
            ranked = ranker.rank(have, cands, max_time, max_missing, k=k)
            items = []
            for score, r in ranked:
                miss = sorted(r.missing(have))
                item = {"name": r.name, "minutes": r.minutes, "score": round(score, 3),
                        "coverage": round(r.coverage(have), 3), "have": sorted(r.needed() & have),
                        "missing": miss, "steps": list(r.steps),
                        "staples": sorted(r.ingredients & STAPLES),
                        "substitutions": [s for m in miss for s in subs.suggest(m, have)]}
                if name == "utility":
                    item["breakdown"] = ranker.breakdown(r, have)
                items.append(item)
            return items

        if method == "compare":
            base["results"], base["baseline_results"] = run("utility"), run("baseline")
        else:
            base["results"] = run(method)
        base["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        return jsonify(base)

    @app.post("/api/detect")
    def detect():
        f = request.files.get("image")
        if not f:
            return error("No image uploaded.")
        why = clf.reason()
        if why:
            return error(why, 503)
        try:
            return jsonify(clf.predict(f.read()))
        except ValueError as e:
            return error(str(e))
        except Exception as e:  # corrupt model file, out of memory, ...
            return error("Photo recognition failed: " + str(e)[:140], 500)

    return app


if __name__ == "__main__":
    import threading
    import webbrowser

    ap = argparse.ArgumentParser(description="Run FridgeChef")
    ap.add_argument("--port", type=int, default=int(os.environ.get("PORT", 5000)))
    ap.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    a = ap.parse_args()
    app = create_app()
    url = f"http://127.0.0.1:{a.port}"
    print(f"FridgeChef running at {url}  (keep this window open, Ctrl+C to stop)")
    print(f"  recipes: {len(app.fc['index'].recipes)}   photo model: {app.fc['clf'].mode() or 'not trained'}")
    if not a.no_browser:
        threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    app.run(host="127.0.0.1", port=a.port, debug=False, threaded=True)
