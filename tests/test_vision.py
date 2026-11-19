"""Image pipeline smoke test with a randomly initialised network (needs torch; skipped otherwise)."""
import io
import os

import pytest

torch = pytest.importorskip("torch")
torchvision = pytest.importorskip("torchvision")
from PIL import Image  # noqa: E402

from app import create_app  # noqa: E402
from classifier import IngredientClassifier  # noqa: E402
from conftest import ROOT  # noqa: E402


@pytest.fixture()
def model_dir(tmp_path):
    classes = ["lemon", "tomato", "carrot"]
    m = torchvision.models.mobilenet_v2()
    m.classifier[1] = torch.nn.Linear(1280, len(classes))
    torch.save(m.state_dict(), tmp_path / "classifier.pt")
    (tmp_path / "classes.json").write_text('["lemon", "tomato", "carrot"]')
    return str(tmp_path)


def png(color=(200, 30, 30)):
    b = io.BytesIO()
    Image.new("RGB", (80, 60), color).save(b, "PNG")
    return b.getvalue()


def test_predict(model_dir):
    c = IngredientClassifier(model_dir)
    assert c.available() and c.mode() == "trained"
    out = c.predict(png())
    assert len(out["predictions"]) == 3
    assert abs(sum(p["confidence"] for p in out["predictions"]) - 1) < 0.01
    with pytest.raises(ValueError):
        c.predict(b"not an image")


def test_detect_endpoint(model_dir):
    app = create_app(os.path.join(ROOT, "data", "sample_recipes.json"), model_dir=model_dir, use_embeddings_cache=False)
    cl = app.test_client()
    assert cl.get("/api/status").get_json()["image_model"] == "trained"
    ok = cl.post("/api/detect", data={"image": (io.BytesIO(png()), "a.png")}, content_type="multipart/form-data")
    assert ok.status_code == 200 and ok.get_json()["predictions"]
    bad = cl.post("/api/detect", data={"image": (io.BytesIO(b"junk"), "a.png")}, content_type="multipart/form-data")
    assert bad.status_code == 400 and "not a readable image" in bad.get_json()["error"]
