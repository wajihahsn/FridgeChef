"""Optional helper: download both datasets with the Kaggle API via `pip install kagglehub`.
Needs a free Kaggle account and an API token (https://www.kaggle.com/settings -> Create New Token; put kaggle.json
in ~/.kaggle/ or set KAGGLE_USERNAME / KAGGLE_KEY). The datasets' terms of use apply (academic coursework only).
Usage: python scripts/download_data.py recipes | images
Alternatively download the files manually in the browser - see README."""
import shutil
import sys

from common import p

what = sys.argv[1] if len(sys.argv) > 1 else ""
if what not in ("recipes", "images"):
    raise SystemExit(__doc__)
try:
    import kagglehub
except ImportError:
    raise SystemExit("Run: pip install kagglehub")
if what == "recipes":
    path = kagglehub.dataset_download("irkaal/foodcom-recipes-and-reviews")
    import os
    os.makedirs(p("data", "raw"), exist_ok=True)
    shutil.copy(os.path.join(path, "recipes.csv" if os.path.exists(os.path.join(path, "recipes.csv")) else "RAW_recipes.csv"),
                p("data", "raw", "RAW_recipes.csv"))
    print("Saved data/raw/RAW_recipes.csv. Next: python scripts/prepare_data.py data/raw/RAW_recipes.csv 20000")
else:
    path = kagglehub.dataset_download("moltean/fruits")
    print("Fruits-360 downloaded to:", path, "\nLook for its 'Training' folder, then run:\n"
          "  python scripts/prepare_images.py <that Training folder> --preset")
