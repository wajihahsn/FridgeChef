"""Train the ingredient classifier (MobileNetV2 transfer learning). Images: data/images/<class_name>/*.jpg
Frozen baseline : python scripts/train_classifier.py --name classifier_frozen
Fine-tuned      : python scripts/train_classifier.py --finetune --name classifier_finetuned
Other seeds     : add --seed 43 / --seed 44 (or run scripts/train_all.py which does everything).
The 80/20 train/held-out split is fixed (seed 42) so every model is tested on the same held-out images;
--seed only changes initialisation, augmentation and batch order.
The first run downloads the pretrained ImageNet weights once (needs internet); afterwards they are cached."""
import argparse
import json
import os
import time

from common import MODELS, SEED, p, split_indices

import torch
import torchvision
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, transforms

ap = argparse.ArgumentParser()
ap.add_argument("--finetune", action="store_true", help="unfreeze the whole network (default: frozen features)")
ap.add_argument("--epochs", type=int, default=8)
ap.add_argument("--name", default="classifier")
ap.add_argument("--seed", type=int, default=SEED)
ap.add_argument("--data", default=p("data", "images"))
ap.add_argument("--batch-size", type=int, default=32)
ap.add_argument("--no-pretrained", action="store_true", help="random weights (only for offline smoke tests)")
a = ap.parse_args()

torch.manual_seed(a.seed)
norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
plain = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(), norm])
aug = transforms.Compose([transforms.RandomResizedCrop(224, scale=(0.6, 1.0)), transforms.RandomHorizontalFlip(),
                          transforms.ColorJitter(0.3, 0.3, 0.3), transforms.ToTensor(), norm])
if not os.path.isdir(a.data):
    raise SystemExit(f"Image folder not found: {a.data}\nSee README, section 'Photo recognition'.")
ds_a, ds_p = datasets.ImageFolder(a.data, aug), datasets.ImageFolder(a.data, plain)
if len(ds_p.classes) < 2:
    raise SystemExit("Need at least 2 class folders inside data/images/")
tr_idx, va_idx = split_indices(len(ds_p))
tl = DataLoader(Subset(ds_a, tr_idx), batch_size=a.batch_size, shuffle=True)
vl = DataLoader(Subset(ds_p, va_idx), batch_size=a.batch_size)
print(f"{len(ds_p.classes)} classes, {len(tr_idx)} train / {len(va_idx)} held-out images, "
      f"{'fine-tuned' if a.finetune else 'frozen features'}, seed {a.seed}")

try:
    m = torchvision.models.mobilenet_v2(weights=None if a.no_pretrained else "DEFAULT")
except Exception as e:
    raise SystemExit(f"Could not download the pretrained weights ({e}).\n"
                     "Connect to the internet once (they are cached afterwards), or use --no-pretrained for a smoke test.")
for prm in m.features.parameters():
    prm.requires_grad = a.finetune
m.classifier[1] = nn.Linear(1280, len(ds_p.classes))
opt = torch.optim.Adam([q for q in m.parameters() if q.requires_grad], lr=1e-4 if a.finetune else 1e-3)
t0 = time.time()
for ep in range(a.epochs):
    m.train()
    if not a.finetune:
        m.features.eval()  # keep BatchNorm statistics of the pretrained network
    for x, y in tl:
        opt.zero_grad()
        nn.functional.cross_entropy(m(x), y).backward()
        opt.step()
    m.eval()
    ok = 0
    with torch.no_grad():
        for x, y in vl:
            ok += (m(x).argmax(1) == y).sum().item()
    print(f"epoch {ep + 1}/{a.epochs}: held-out accuracy {ok / max(len(va_idx), 1):.3f}  ({time.time() - t0:.0f}s)")
os.makedirs(MODELS, exist_ok=True)
torch.save(m.state_dict(), os.path.join(MODELS, f"{a.name}.pt"))
for fn in ("classes.json", f"{a.name}.classes.json"):
    json.dump(ds_p.classes, open(os.path.join(MODELS, fn), "w", encoding="utf-8"))
print(f"saved models/{a.name}.pt  ({len(ds_p.classes)} classes)")
