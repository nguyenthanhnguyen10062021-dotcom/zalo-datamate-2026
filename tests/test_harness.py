"""Exercise the harness with synthetic files; no competition data or network."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "harness.py"


@pytest.fixture
def harness():
    assert SCRIPT.is_file(), "Harness CLI has not been implemented"
    spec = importlib.util.spec_from_file_location("datamate_harness", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path,source,clue", [
    ("business/sales.py", "from loader import load_business", "loader"),
    ("business/sales.py", "from ..loader import build", "loader"),
    ("loader/build.py", "import os, business", "business"),
    ("business/sales.py", "import verify_business", "verify_business"),
    ("evaluate/evaluate.py", "import pandas", "stdlib"),
    ("business/sales.py", "import requests", "offline"),
    ("loader/io.py", "from urllib.request import urlopen", "offline"),
    ("business/sales.py", "gold = 'train/answers.jsonl'", "gold"),
    ("loader/io.py", "gold = Path('answers.jsonl')", "gold"),
    ("business/sales.py", "def broken(:", "syntax"),
])
def test_source_violation_has_location_and_remediation(harness, path, source, clue):
    errors = harness.check_source(path, source)
    assert errors and any(clue in error for error in errors)
    assert all(path in error and ":1:" in error for error in errors)


@pytest.mark.parametrize("path,source", [
    ("business/sales.py", "import pandas as pd\nfrom .periods import DateRange"),
    ("loader/build.py", "from .mapping import Dictionaries\nimport numpy as np"),
    ("evaluate/evaluate.py", "from collections import Counter\nimport json"),
    ("tests/test_example.py", "import business\nx = 'answers.jsonl'"),
])
def test_source_allowed_dependencies(harness, path, source):
    assert harness.check_source(path, source) == []


@pytest.mark.parametrize("name", [
    "train/data/shop/README.md", "public_test/questions.jsonl", "cache/tables.json",
    "reports/run.json", ".env", ".env.production", ".venv/pyvenv.cfg", "sample.csv",
    "surveys/survey_raw.md", "load_report.md", "gold_report.md", "generalize_report.md",
])
def test_forbidden_tracked_files_are_rejected(harness, tmp_path, name):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("synthetic", encoding="utf-8")
    errors = harness.check_paths(tmp_path, [name])
    assert any(name in error and "Git" in error for error in errors)


def test_current_doc_links_are_checked_without_loading_history(harness, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "Thử file.md").write_text("# Hi", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[ok](<docs/Thử file.md#hi>) [web](https://example.com) [self](#hi)\n"
        "[broken](docs/missing.md)", encoding="utf-8",
    )
    archive = tmp_path / "ai_collaboration" / "rounds"
    archive.mkdir(parents=True)
    (archive / "old.md").write_text("[old](missing.md)", encoding="utf-8")
    errors = harness.check_paths(tmp_path, ["README.md", "ai_collaboration/rounds/old.md"])
    assert len(errors) == 1 and "docs/missing.md" in errors[0]


def test_agents_budget_prevents_context_bloat(harness, tmp_path):
    (tmp_path / "AGENTS.md").write_text("x" * 6001, encoding="utf-8")
    assert any("6000" in error for error in harness.check_paths(tmp_path, ["AGENTS.md"]))


@pytest.mark.parametrize("result", [
    {}, {"compared": 0, "matched_gold": 0, "errors": []},
    {"compared": 3, "matched_gold": 2, "errors": []},
    {"compared": 3, "matched_gold": 3, "errors": [{"error": "bad"}]},
])
def test_empty_or_failed_data_verification_cannot_pass(harness, result):
    assert harness.validate_verification(result)


def test_nonempty_matching_data_verification_passes(harness):
    assert harness.validate_verification({"compared": 3, "matched_gold": 3, "errors": []}) == []


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.mark.parametrize("forced", [
    "train/answers.jsonl", "surveys/survey_raw.md", "load_report.md",
    "gold_report.md", "generalize_report.md",
])
def test_inventory_includes_forced_tracked_data_but_skips_ignored_env(harness, tmp_path, forced):
    git(tmp_path, "init", "-q")
    (tmp_path / ".gitignore").write_text(forced + "\n.venv/\n", encoding="utf-8")
    artifact = tmp_path / forced
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "private.txt").write_text("hidden", encoding="utf-8")
    git(tmp_path, "add", "-f", forced)
    paths = harness.repository_paths(tmp_path)
    assert forced in paths
    assert ".venv/private.txt" not in paths
    assert any(forced in error for error in harness.check_paths(tmp_path, paths))


def test_data_preflight_lists_missing_inputs(harness, tmp_path):
    errors = harness.data_prerequisites(tmp_path)
    assert any("train/answers.jsonl" in error for error in errors)
    assert any("cache" in error for error in errors)


def test_context_follows_relative_imports_and_transitive_dependents(harness, tmp_path):
    files = {
        "pkg/__init__.py": "from .engine import Engine\n",
        "pkg/engine.py": "from .rules import Rule\nclass Engine:\n    def total(self, n: int = 1) -> int:\n        return n\n",
        "pkg/rules.py": "class Rule:\n    pass\n",
        "run.py": "from pkg import Engine\n",
        "train/private.py": "def PRIVATE_COMPETITION_TEXT(): pass\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    graph = harness.build_code_map(tmp_path, list(files))
    assert "train/private.py" not in graph
    context = harness.file_context(graph, "pkg/rules.py", limit=20)
    assert context["dependents"] == ["pkg/__init__.py", "pkg/engine.py", "run.py"]
    api = harness.file_context(graph, "pkg/engine.py", limit=20)
    assert api["imports"] == ["pkg/rules.py"]
    assert any(item["name"] == "Engine.total" and item["line"] == 3 for item in api["api"])


def test_context_reads_uncommitted_edits_and_bounds_output(harness, tmp_path):
    path = tmp_path / "api.py"
    path.write_text("def first(): pass\ndef second(): pass\n", encoding="utf-8")
    graph = harness.build_code_map(tmp_path, ["api.py"])
    limited = harness.file_context(graph, "api.py", limit=1)
    assert len(limited["api"]) == 1 and limited["api_total"] == 2
    path.write_text("def renamed(): pass\n", encoding="utf-8")
    fresh = harness.file_context(harness.build_code_map(tmp_path, ["api.py"]), "api.py", limit=20)
    assert fresh["api"][0]["name"] == "renamed"
    with pytest.raises(ValueError, match="not indexed"):
        harness.file_context(graph, "missing.py", limit=20)


def test_context_tracks_package_initializer_side_effects(harness, tmp_path):
    files = {
        "pkg/__init__.py": "from .config import VALUE\n",
        "pkg/config.py": "VALUE = 1\n",
        "pkg/engine.py": "def run(): pass\n",
        "main.py": "import pkg.engine\n",
    }
    for name, source in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    graph = harness.build_code_map(tmp_path, list(files))
    assert harness.file_context(graph, "pkg/config.py", limit=20)["dependents"] == ["main.py", "pkg/__init__.py"]


def test_context_index_rejects_missing_evidence_and_matches_file_scope(harness, tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "rules.md").write_text("# Evidence", encoding="utf-8")
    path = tmp_path / "docs" / "context-index.json"
    entry = {"id": "errors", "touches": ["business/**"], "read": ["docs/rules.md"], "summary": "Do not hide data errors"}
    path.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    assert harness.related_knowledge(tmp_path, "business/sales.py") == [entry]
    assert harness.related_knowledge(tmp_path, "loader/io.py") == []
    entry["read"] = ["docs/missing.md"]
    path.write_text(json.dumps({"entries": [entry]}), encoding="utf-8")
    with pytest.raises(ValueError, match="missing.md"):
        harness.related_knowledge(tmp_path, "business/sales.py")


def test_cli_uses_repository_root_from_another_cwd(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "doctor"], cwd=tmp_path,
        capture_output=True, text=True, encoding="utf-8",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert str(SCRIPT.parents[1]) in result.stdout
    assert sys.executable in result.stdout
