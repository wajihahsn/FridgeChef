"""Train frozen baseline + fine-tuned classifier for the 3 seeds of the evaluation plan (42, 43, 44).
Usage: python scripts/train_all.py [--epochs 8]
Creates models/classifier_frozen_s42.pt ... classifier_finetuned_s44.pt, then run
python scripts/evaluate_classifier.py   (it finds them automatically)."""
import subprocess
import sys

from common import p

extra = sys.argv[1:]
for seed in (42, 43, 44):
    for kind, flag in (("frozen", []), ("finetuned", ["--finetune"])):
        cmd = [sys.executable, p("scripts", "train_classifier.py"), "--name", f"classifier_{kind}_s{seed}",
               "--seed", str(seed)] + flag + extra
        print(">>", " ".join(cmd), flush=True)
        if subprocess.call(cmd) != 0:
            sys.exit("Training failed - see the message above.")
print("\nDone. Next: python scripts/evaluate_classifier.py")
