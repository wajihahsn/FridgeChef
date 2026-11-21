# FridgeChef: step-by-step guide

**Where to type commands:** in a terminal opened INSIDE the `fridgechef` folder (VS Code: File > Open Folder > `fridgechef`, then Terminal > New Terminal). Every command below is typed there, with the virtual environment active (you see `(.venv)` at the start of the line).

## PART 1: Run the app (everyone, 5 minutes)
1. Install Python 3.10-3.13 from python.org (Windows: tick "Add Python to PATH").
2. Create the environment (once):
   `python -m venv .venv`
3. Activate it (every new terminal):
   Windows: `.venv\Scripts\activate`   Mac/Linux: `source .venv/bin/activate`
   (Windows error about scripts? run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.)
4. Install packages (once): `pip install -r requirements.txt`
5. Start: `python backend/app.py`. The browser opens at http://127.0.0.1:5000. Keep the terminal open; Ctrl+C stops it.
6. Check everything: `pytest` (should say 45 passed).

## PART 2: Datasets (Member 1 = recipes, Member 2 = images)
You need a free Kaggle account (kaggle.com). Read each dataset's terms on its page first.

### A. Recipes (Wajiha)
1. Download from https://www.kaggle.com/datasets/irkaal/foodcom-recipes-and-reviews the file `recipes.csv` (use the Download button, unzip).
2. Create the folder `data/raw/` and put the file there: `fridgechef/data/raw/recipes.csv`
3. Run: `python scripts/prepare_data.py data/raw/recipes.csv --n 20000 --vocab 1500`
4. This creates `data/recipes.json`. Restart the app (Ctrl+C, then `python backend/app.py`): it now uses it automatically.

### B. Ingredient images (Unzila)
1. Install PyTorch packages (large): `pip install -r requirements-vision.txt`
2. Download Fruits-360 from https://www.kaggle.com/datasets/moltean/fruits and unzip it ANYWHERE outside the project (e.g. `C:\datasets\fruits`). You do NOT put it inside the project.
3. Find its `Training` folder (e.g. `C:\datasets\fruits\fruits-360_100x100\fruits-360\Training`). To see the folder names: `python scripts/prepare_images.py "<path to Training>" --list`
4. Copy ~20 classes into the project: `python scripts/prepare_images.py "<path to Training>" --preset`
   This creates `data/images/<class>/` folders (e.g. `data/images/tomato/`). A class that prints 0 is missing from your version.
5. Add your own photos (at least 30 per class, different backgrounds/lighting) as .jpg/.png into the matching folder, e.g. `data/images/onion/my1.jpg`. The folder name must be the ingredient name.
6. Train (30 min - hours on CPU): `python scripts/train_all.py --epochs 8`
   (quick test first: `python scripts/train_all.py --epochs 1`). The first run downloads pretrained weights, so internet is needed once.
7. Evaluate: `python scripts/evaluate_classifier.py` (charts appear in `results/`).
8. Pick the best model and copy it to `models/classifier.pt`:
   Windows: `copy models\classifier_finetuned_s42.pt models\classifier.pt`   Mac/Linux: `cp models/classifier_finetuned_s42.pt models/classifier.pt`
   Restart the app: the header badge says "photo recognition ready".

## PART 3: Evaluation that the three of you must do by hand
All files go in the `data/` folder. Results charts are written to `results/`.

### 1. Ranking judgments (all three members)
1. `python scripts/evaluate_ranking.py` creates `data/relevance_template.csv`.
2. Open it in Excel. Each row is a recipe for a scenario (the `have` column shows the ingredients). Each member fills their own column `judge1`, `judge2`, `judge3` with 0 (not useful), 1 (okay) or 2 (great). Judge independently.
3. Save/export as CSV with the name `data/relevance.csv` (same folder, same columns).
4. Run `python scripts/evaluate_ranking.py` again. It prints Precision@5, NDCG@5, average missing ingredients and response time, and saves `results/ranking.png` and `results/ranking_missing.png`.
   (Do NOT use `--auto-draft` for the report: it is not human judgment.)

### 2. Substitution ratings (all three members)
1. `python scripts/evaluate_substitution.py` creates `data/substitution_template.csv` (and prints automatic metrics).
2. Open it in Excel. Each member rates every suggestion 1 (nonsense) to 5 (perfect) in `rater1`, `rater2`, `rater3`.
3. Save as `data/substitution_ratings.csv`.
4. Run `python scripts/evaluate_substitution.py` again: it prints mean plausibility per method (rule vs Word2Vec) and saves `results/substitution.png`.
Note: after you switch to the full recipe data, delete `data/substitution_ratings.csv` / re-run step 1 first, because suggestions change.

### 3. Weight sensitivity test (automatic)
`python scripts/evaluate_sensitivity.py` -> `results/sensitivity.png`.

## PART 4: What is left, per person
| Who | To do |
|---|---|
| Wajiha | Part 2A (recipes); ranking evaluation; sensitivity test |
| Unzila | Part 2B (images, own photos, training, classifier evaluation) |
| Narmeen | Re-run substitution evaluation after the full data is loaded; test the app end to end; GitHub upload |
| All three | Judge `relevance.csv` and rate `substitution_ratings.csv`; write the report (use the 4+ charts in `results/`: ranking, substitution, confusion matrix, classifier accuracy, sensitivity); cite Food.com and Fruits-360 in the report |

## PART 5: Submit
`git init`, `git add .`, `git commit -m "FridgeChef"`, create the repository on GitHub, `git remote add origin <url>`, `git push -u origin main`. Big data/model files are excluded by `.gitignore`.

## Troubleshooting
- "Cannot reach the server": the terminal running `python backend/app.py` was closed.
- Port in use: `python backend/app.py --port 5001`.
- "No module named ...": the environment is not active, or step 4 of Part 1 was skipped.
- Photo button says not trained: finish Part 2B step 8.
