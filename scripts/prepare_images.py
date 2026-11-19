"""Copy a class subset of Fruits-360 into data/images/<class>/ (seed 42, default max 100 images per class).

Usage:
  python scripts/prepare_images.py <Fruits-360 Training folder> --preset            # ~19 common classes
  python scripts/prepare_images.py <Training folder> tomato onion "bell pepper=Pepper" "potato=Potato Red,Potato White"
  python scripts/prepare_images.py <Training folder> --list                         # show the dataset folder names
Options: --max 100   (images per class, so your own photos still matter)
label=Prefix[,Prefix2] is used when the dataset folder name differs from the recipe ingredient name
(folders starting with a prefix are used)."""
import os
import random
import shutil
import sys

from common import SEED, p

PRESET = ["tomato", "potato=Potato Red,Potato White", "sweet potato=Potato Sweet", "onion=Onion", "carrot", "cucumber",
          "lemon=Lemon", "lime=Limes,Lime", "orange=Orange", "banana=Banana", "apple=Apple", "avocado=Avocado",
          "eggplant", "bell pepper=Pepper", "corn=Corn", "ginger=Ginger Root", "zucchini", "mango=Mango",
          "pear=Pear", "cabbage"]

args = sys.argv[1:]
if not args:
    raise SystemExit(__doc__)
src = args.pop(0)
mx = 100
if "--max" in args:
    i = args.index("--max")
    mx = int(args[i + 1])
    del args[i:i + 2]
if not os.path.isdir(src):
    raise SystemExit(f"Folder not found: {src}")
if "--list" in args:
    print("\n".join(sorted(os.listdir(src))))
    raise SystemExit
if "--preset" in args:
    args = [a for a in args if a != "--preset"] + PRESET
if not args:
    raise SystemExit(__doc__)

random.seed(SEED)
total = 0
for a in args:
    label, prefixes = a.split("=", 1) if "=" in a else (a, a)
    prefixes = [x.strip().lower() for x in prefixes.split(",")]
    dirs = sorted(d for d in os.listdir(src) if any(d.lower().startswith(x) for x in prefixes)
                  and os.path.isdir(os.path.join(src, d)))
    files = [os.path.join(src, d, f) for d in dirs for f in sorted(os.listdir(os.path.join(src, d)))
             if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    random.shuffle(files)
    dst = p("data", "images", label)
    os.makedirs(dst, exist_ok=True)
    for i, f in enumerate(files[:mx]):
        shutil.copy(f, os.path.join(dst, f"ds_{i}{os.path.splitext(f)[1].lower()}"))
    total += len(files[:mx])
    print(f"{label:14s} {len(files[:mx]):4d} images   (from {len(dirs)} dataset folders)")
print("total", total, "images in data/images/")
