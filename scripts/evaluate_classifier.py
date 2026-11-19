"""Evaluate classifiers on the fixed held-out split: top-1 accuracy, per-class precision/recall, confusion matrix,
frozen-vs-fine-tuned comparison (mean and spread over seeds) and average prediction time.
Usage: python scripts/evaluate_classifier.py                 (auto-detects models/classifier_*_s*.pt)
       python scripts/evaluate_classifier.py models/a.pt models/b.pt   [--data other/image/folder]"""
import glob
import os
import re
import sys
import time
from collections import defaultdict

from common import MODELS, RESULTS, p, split_indices

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
import torchvision
from sklearn.metrics import ConfusionMatrixDisplay, classification_report, confusion_matrix
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

argv = sys.argv[1:]
data_dir = p("data", "images")
if "--data" in argv:
    i = argv.index("--data")
    data_dir = argv[i + 1]
    del argv[i:i + 2]
paths = argv or sorted(glob.glob(os.path.join(MODELS, "classifier_*_s[0-9]*.pt"))) \
    or sorted(glob.glob(os.path.join(MODELS, "classifier_*.pt")))
if not paths:
    raise SystemExit("No models found in models/. Train first (see README).")
tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
                         transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
ds = datasets.ImageFolder(data_dir, tf)
_, va_idx = split_indices(len(ds))
loader = DataLoader(Subset(ds, va_idx), batch_size=32)
print(f"{len(va_idx)} held-out images, {len(ds.classes)} classes")

accs, groups = {}, defaultdict(list)
for path in paths:
    m = torchvision.models.mobilenet_v2()
    m.classifier[1] = torch.nn.Linear(1280, len(ds.classes))
    m.load_state_dict(torch.load(path, map_location="cpu"))
    m.eval()
    y, yh = [], []
    t0 = time.perf_counter()
    with torch.no_grad():
        for x, t in loader:
            yh += m(x).argmax(1).tolist()
            y += t.tolist()
    ms = (time.perf_counter() - t0) / max(len(y), 1) * 1000
    name = os.path.splitext(os.path.basename(path))[0]
    accs[name] = float(np.mean(np.array(y) == np.array(yh)))
    groups[re.sub(r"_s\d+$", "", name)].append(accs[name])
    rep = classification_report(y, yh, labels=range(len(ds.classes)), target_names=ds.classes, zero_division=0)
    print(f"\n{name}: accuracy {accs[name]:.3f}  ({ms:.1f} ms/image)\n{rep}")
    open(os.path.join(RESULTS, f"classifier_report_{name}.txt"), "w").write(rep)
    fig, ax = plt.subplots(figsize=(8, 8))
    ConfusionMatrixDisplay(confusion_matrix(y, yh, labels=range(len(ds.classes))), display_labels=ds.classes).plot(
        ax=ax, xticks_rotation=60, colorbar=False)
    fig.savefig(os.path.join(RESULTS, f"confusion_{name}.png"), dpi=150, bbox_inches="tight"); plt.close(fig)

print("\nSummary (mean +- std over seeds):")
for g, v in groups.items():
    print(f"  {g:24s} {np.mean(v):.3f} +- {np.std(v):.3f}  (n={len(v)})")
fig, ax = plt.subplots(figsize=(6, 4))
names = list(groups)
b = ax.bar(names, [np.mean(groups[g]) for g in names], yerr=[np.std(groups[g]) for g in names], capsize=6, color="#1c9a5b")
ax.bar_label(b, fmt="%.3f", padding=4); ax.set_ylim(0, 1.1); ax.set_title("Classifier held-out accuracy (mean +- std)")
plt.setp(ax.get_xticklabels(), rotation=15)
fig.savefig(os.path.join(RESULTS, "classifier_accuracy.png"), dpi=150, bbox_inches="tight")
print("saved charts in results/")
