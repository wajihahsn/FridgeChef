# FridgeChef: AI What's-in-My-Fridge Assistant
AL-2002 Artificial Intelligence Lab, Fall 2026 · FAST-NUCES Karachi · Wajiha Hassan (24K-2509), Unzila Azam (24K-2511), Narmeen Zehra (24K-2565)

Type what is in your fridge (or photograph one ingredient) and get recipes ranked by a **utility function**
(ingredient coverage, missing count, cooking time), the missing items, and **substitutions with a reason**.
Flask backend + plain HTML/CSS/JS frontend. **Runs fully offline** after setup.

## Quick start (works immediately, no downloads)
Needs Python 3.10 - 3.13 (https://www.python.org/downloads/; on Windows tick "Add Python to PATH").
```bash
cd fridgechef
python -m venv .venv
.venv\Scripts\activate            # Windows PowerShell   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python backend/app.py             # opens http://127.0.0.1:5000
```
- Windows, if activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
- Always use the address the terminal prints; never double-click `index.html`.
- Another port: `python backend/app.py --port 5001`; no auto-open: `--no-browser`.
- Tests: `pytest` (45 tests; the vision tests are skipped if PyTorch is not installed).
- VS Code: open the folder, install the suggested extensions, pick the `.venv` interpreter, press F5 ("FridgeChef (Flask)").

The app ships with 133 hand-written sample recipes so it works out of the box. Use the full Food.com data below for the real project.

## Using the app
1. Type ingredients (comma-separated is fine: `2 cloves garlic, tomatoes, eggs`). Plurals, amounts and typos are normalized (`cheez` -> `cheese`). Orange chips = not in any recipe.
2. Optional: upload a photo (needs the trained model below), tap the right guess to add it.
3. Set max cooking time / max missing ingredients, choose *Utility*, *Baseline* or *Compare both side by side*, press **Find recipes**.
4. Each card shows coverage, time, what you have/miss, substitutions (tagged `rule` or `Word2Vec`), "Why this score?" and the steps.

## Full dataset (once, needs internet + free Kaggle account)
Proposal source: Kaggle *Food.com Recipes and Reviews* (`irkaal/foodcom-recipes-and-reviews`). Read the dataset's terms first.
1. Download `recipes.csv` from the Kaggle page into `data/raw/` (or `pip install kagglehub` and `python scripts/download_data.py recipes`; needs a Kaggle API token).
2. `python scripts/prepare_data.py data/raw/recipes.csv --n 20000 --vocab 1500`
   (the older `RAW_recipes.csv` format is also accepted). This writes `data/recipes.json`.
3. Restart the app: it now uses it automatically and trains/caches Word2Vec in `models/` (first start takes a little longer).
Word2Vec substitutions are intentionally strict: on the 133-recipe sample they rarely fire; they become useful with thousands of recipes.

## Photo recognition (MobileNetV2 transfer learning)
Not included (it needs your images and training); until trained the app shows a friendly message and typing still works.
1. `pip install -r requirements-vision.txt`
2. Download Fruits-360 from Kaggle (`moltean/fruits`) or its GitHub page. Then:
   `python scripts/prepare_images.py <path>/Training --preset` (about 20 classes, 100 images each; `--list` shows folder names).
   Classes that print 0 are missing from your dataset version: add your own photos (30+ per class, varied backgrounds) to `data/images/<class>/`. Folder name = ingredient name.
3. Train frozen baseline + fine-tuned for seeds 42, 43, 44: `python scripts/train_all.py --epochs 8` (first run downloads the pretrained weights once).
   Single run: `python scripts/train_classifier.py --finetune --name classifier_finetuned`.
4. `python scripts/evaluate_classifier.py` -> accuracy mean +- std, per-class report, confusion matrices, charts.
5. Use the best model: copy it to `models/classifier.pt` (`copy` on Windows, `cp` on Mac/Linux) and restart. `models/classes.json` is written by training.

## Evaluation for the report (charts go to `results/`)
| Comparison (proposal section 7) | Command |
|---|---|
| Utility vs overlap baseline: P@5, NDCG@5, missing count, response time | `python scripts/evaluate_ranking.py` -> judge `data/relevance_template.csv` (0/1/2, all three members), save as `data/relevance.csv`, run again |
| Sensitivity of the utility weights | `python scripts/evaluate_sensitivity.py` |
| Rule table vs Word2Vec (30 cases): auto metrics + 1-5 human ratings | `python scripts/evaluate_substitution.py` -> rate `data/substitution_template.csv`, save as `data/substitution_ratings.csv`, run again |
| Fine-tuned vs frozen classifier, confusion matrix | `python scripts/evaluate_classifier.py` |

`python scripts/evaluate_ranking.py --auto-draft` creates a **draft** relevance file by a simple rule just to try the pipeline. It is not human judgment: do not report numbers from it. Seed 42 is used everywhere.

## Project layout
```
backend/   app.py normalizer.py recipes.py rankers.py substitution.py classifier.py
frontend/  index.html style.css app.js
scripts/   prepare_data prepare_images download_data train_classifier train_all evaluate_* build_sample_data
data/      sample_recipes.json  test_scenarios.json (20)  substitution_cases.json (30)
models/    classifier.pt + classes.json (after training), Word2Vec cache
tests/     test_core.py test_api.py test_vision.py        docs/  proposal PDF
```
Classes follow the proposal: IngredientNormalizer, Recipe, RecipeIndex, Ranker/OverlapRanker/UtilityRanker, Substituter/RuleSubstituter/EmbeddingSubstituter, IngredientClassifier, and the Flask app (`create_app`) as FridgeChefApp.

## API
`GET /api/status` · `GET /api/ingredients` · `POST /api/normalize` · `POST /api/recommend` (`ingredients, max_time, max_missing, method=utility|baseline|compare, k`) · `POST /api/detect` (multipart `image`)

