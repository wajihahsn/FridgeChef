import io
import os

import pytest

from app import create_app
from conftest import ROOT


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    d = tmp_path_factory.mktemp("models")
    app = create_app(os.path.join(ROOT, "data", "sample_recipes.json"), model_dir=str(d), use_embeddings_cache=False)
    return app.test_client()


def post(client, url, body):
    return client.post(url, json=body)


def test_home_and_static(client):
    assert client.get("/").status_code == 200
    for f in ("style.css", "app.js"):
        assert client.get("/" + f).status_code == 200


def test_status_and_ingredients(client):
    s = client.get("/api/status").get_json()
    assert s["recipes"] >= 100 and s["image_model"] is None and s["image_hint"] and "salt" in s["staples"]
    assert "tomato" in client.get("/api/ingredients").get_json()


def test_recommend_basic(client):
    d = post(client, "/api/recommend", {"ingredients": ["Tomatoes", "eggs", "2 onions"], "max_time": 30, "max_missing": 2}).get_json()
    assert d["have"] == ["egg", "onion", "tomato"] and d["unknown"] == []
    assert d["results"] and len(d["results"]) <= 5 and d["elapsed_ms"] >= 0
    for r in d["results"]:
        assert r["minutes"] <= 30 and len(r["missing"]) <= 2 and "breakdown" in r
        assert set(r["have"]) <= set(d["have"])


def test_recommend_substitutions_have_reason(client):
    d = post(client, "/api/recommend", {"ingredients": ["pasta", "milk", "garlic"], "max_missing": 3}).get_json()
    subs = [s for r in d["results"] for s in r["substitutions"]]
    assert subs and all(s["reason"] and s["source"] in ("rule", "embedding") for s in subs)


def test_recommend_methods(client):
    body = {"ingredients": ["egg", "bread", "milk"]}
    assert post(client, "/api/recommend", {**body, "method": "baseline"}).get_json()["results"]
    c = post(client, "/api/recommend", {**body, "method": "compare"}).get_json()
    assert c["results"] and c["baseline_results"]
    assert post(client, "/api/recommend", {**body, "method": "nope"}).status_code == 400


def test_recommend_unknown_and_empty(client):
    d = post(client, "/api/recommend", {"ingredients": ["dragonfruit", "egg"]}).get_json()
    assert d["unknown"] == ["dragonfruit"] and "egg" in d["have"]
    assert post(client, "/api/recommend", {"ingredients": []}).get_json()["results"] == []
    assert post(client, "/api/recommend", {"ingredients": ["", "  "]}).get_json()["results"] == []


@pytest.mark.parametrize("body", [
    {"ingredients": "egg"}, {"ingredients": [1, 2]}, {"ingredients": ["egg"], "max_time": "abc"},
    {"ingredients": ["egg"], "max_missing": -1}, {"ingredients": ["egg"], "k": 999}, [1, 2],
])
def test_recommend_bad_input_is_a_clean_400(client, body):
    r = post(client, "/api/recommend", body)
    assert r.status_code == 400 and "error" in r.get_json()


def test_recommend_not_json(client):
    r = client.post("/api/recommend", data="garbage", content_type="text/plain")
    assert r.status_code == 400 and "error" in r.get_json()


def test_normalize_endpoint(client):
    d = post(client, "/api/normalize", {"ingredients": ["2 cloves minced garlic", "tomatto", "zzzz"]}).get_json()
    assert [(i["name"], i["known"]) for i in d["items"]] == [("garlic", True), ("tomato", True), ("zzzz", False)]


def test_detect_without_model(client):
    assert client.post("/api/detect").status_code == 400
    r = client.post("/api/detect", data={"image": (io.BytesIO(b"x"), "a.jpg")}, content_type="multipart/form-data")
    assert r.status_code == 503 and "error" in r.get_json()


def test_unknown_route_is_json(client):
    r = client.get("/api/nothing")
    assert r.status_code == 404 and r.get_json()["error"]
