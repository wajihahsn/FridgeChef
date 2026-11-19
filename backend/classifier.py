"""Photo >> ingredient using the trained MobileNetV2 (models/classifier.pt + models/classes.json).

Train it with scripts/train_classifier.py. After training the app runs fully offline."""
import importlib.util
import io
import json
import os
import threading

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


class IngredientClassifier:
    """attributes: model, class names; methods: predict(image bytes). Training lives in scripts/."""

    def __init__(self, model_dir=MODEL_DIR):
        self.model_dir = model_dir
        self._ready = False
        self._lock = threading.Lock()

    def reason(self):
        """None if usable, otherwise a short message telling the user what is missing."""
        has = lambda m: importlib.util.find_spec(m) is not None
        if not (has("torch") and has("torchvision") and has("PIL")):
            return "Photo recognition needs: pip install -r requirements-vision.txt (then restart the app)."
        if not all(os.path.exists(os.path.join(self.model_dir, f)) for f in ("classifier.pt", "classes.json")):
            return "The image model is not trained yet. Train it (see README) or type your ingredients instead."
        return None

    def available(self):
        return self.reason() is None

    def mode(self):
        return "trained" if self.available() else None

    def classes_list(self):
        try:
            with open(os.path.join(self.model_dir, "classes.json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return []

    def _load(self):
        with self._lock:
            if self._ready:
                return
            import torch
            import torchvision
            from torchvision import transforms
            self.torch = torch
            self.classes = self.classes_list()
            m = torchvision.models.mobilenet_v2()
            m.classifier[1] = torch.nn.Linear(1280, len(self.classes))
            m.load_state_dict(torch.load(os.path.join(self.model_dir, "classifier.pt"), map_location="cpu"))
            self.model = m.eval()
            self.tf = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
                                          transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
            self._ready = True

    def predict(self, data, k=3):
        """Top-k guesses for one image (raw bytes). Raises ValueError for files that are not images."""
        self._load()
        from PIL import Image, UnidentifiedImageError
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except (UnidentifiedImageError, OSError) as e:
            raise ValueError("That file is not a readable image.") from e
        x = self.tf(img).unsqueeze(0)
        with self.torch.no_grad():
            p = self.torch.softmax(self.model(x)[0], 0)
        top = p.topk(min(k, len(self.classes)))
        return {"mode": "trained",
                "predictions": [{"label": self.classes[i], "confidence": round(float(c), 3)}
                                for c, i in zip(top.values, top.indices)]}
