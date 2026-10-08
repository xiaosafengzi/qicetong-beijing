import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def company():
    return copy.deepcopy(json.loads((ROOT / "data/companies.json").read_text(encoding="utf-8"))[0])


@pytest.fixture
def policies():
    return {p["id"]: p for p in json.loads((ROOT / "data/policies.json").read_text(encoding="utf-8"))}


@pytest.fixture
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setenv("QCT_RUNTIME", str(tmp_path))
    from qicetong import store
    store.initialize()
    return store
