"""Local/CI feedback for coding agents. Stdlib only; never installs or uploads."""
from __future__ import annotations

import argparse
import ast
from fnmatch import fnmatchcase
from importlib import metadata
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "AGENTS.md", "docs/README.md", "docs/architecture.md",
    "docs/harness-engineering.md", "docs/PROGRESS.md", "docs/validation.md",
    "docs/tasks/TEMPLATE.md", "loader/AGENTS.md", "business/AGENTS.md",
    "evaluate/AGENTS.md", "ai_collaboration/AGENTS.md",
    "docs/context-index.json",
)
DEV_MODULES = {
    "evaluate", "tests", "surveys", "scripts", "load_all", "check_with_gold",
    "generalize_check", "verify_business",
}
NETWORK_MODULES = {
    "socket", "http", "urllib", "requests", "httpx", "aiohttp", "openai",
    "anthropic", "grpc", "ftplib", "smtplib", "webbrowser",
}
PRIVATE_DIRS = {
    "train", "public_test", "data", "cache", "reports", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".aws", ".codex-log",
}
PRIVATE_SUFFIXES = {".csv", ".xlsx", ".xls", ".sqlite", ".db", ".parquet", ".zip", ".pyc"}
PRIVATE_PATHS = {"surveys/survey_raw.md", "load_report.md", "gold_report.md", "generalize_report.md"}


def private_file(name: str) -> bool:
    path = Path(name)
    return bool(path.as_posix() in PRIVATE_PATHS or set(path.parts) & PRIVATE_DIRS or path.suffix.lower() in PRIVATE_SUFFIXES
                or (path.name.startswith(".env") and path.name != ".env.example")
                or path.suffix == ".jsonl" and path.name.startswith(("submission", "errors", "abstain")))


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True,
        text=True, encoding="utf-8", errors="replace",
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Git command failed")
    return result.stdout


def repository_paths(root: Path) -> list[str]:
    """Include forced tracked files; do not walk ignored datasets/environments."""
    return sorted(set(filter(None, git(
        root, "ls-files", "-z", "--cached", "--others", "--exclude-standard",
    ).split("\0"))))


def check_source(path: str, source: str) -> list[str]:
    errors = []
    try:
        tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: syntax: {exc.msg}; fix Python syntax."]
    layer = path.split("/")[0]
    if layer not in {"loader", "business", "queryplan", "evaluate"} or Path(path).name.startswith("test_"):
        return errors
    for node in ast.walk(tree):
        location = f"{path}:{getattr(node, 'lineno', 1)}:"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            else:
                modules = [(node.module or "").split(".")[0]]
                if not node.module:
                    modules = [alias.name.split(".")[0] for alias in node.names]
            for module in modules:
                if module in NETWORK_MODULES:
                    errors.append(f"{location} offline: {module}; keep network clients outside runtime layers.")
                if layer == "evaluate":
                    if module not in sys.stdlib_module_names:
                        errors.append(f"{location} evaluator must use stdlib only: {module}; move integration outside evaluate/.")
                elif (module in DEV_MODULES
                      or layer == "loader" and module in {"business", "queryplan"}
                      or layer == "business" and module in {"loader", "queryplan"}
                      or layer == "queryplan" and module == "loader"):
                    errors.append(f"{location} dependency: {layer} cannot import {module}; pass data through the public API.")
        if layer in {"loader", "business", "queryplan"} and isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "answers.jsonl" in node.value.replace("\\", "/").lower():
                errors.append(f"{location} gold: answers.jsonl belongs in verification tools, never {layer}/.")
    return errors


def check_doc_links(root: Path, path: str, text: str) -> list[str]:
    # Only inline Markdown links in maintained docs. Skip code/examples/anchors.
    text = re.sub(r"```.*?```|`[^`\n]+`", "", text, flags=re.DOTALL)
    errors = []
    for match in re.finditer(r"\[[^\]\n]*\]\((<[^>\n]+>|[^)\s]+)(?:\s+[^)]*)?\)", text):
        target = match[1].strip("<>")
        if target.startswith(("#", "/")) or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        target = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if target and not (root / path).parent.joinpath(target).exists():
            errors.append(f"{path}: broken link {target}; update the target or link.")
    return errors


def check_paths(root: Path, paths: list[str]) -> list[str]:
    errors = []
    for name in paths:
        path = root / name
        if not path.is_file():
            continue  # A deleted file is not part of the proposed working tree.
        if not path.resolve().is_relative_to(root.resolve()):
            errors.append(f"{name}: file escapes repository; replace the external symlink.")
            continue
        if private_file(name):
            errors.append(f"{name}: private/generated file in Git inventory; untrack it and keep it local via .gitignore.")
            continue
        is_agents = path.name == "AGENTS.md"
        is_doc = (name in {"README.md", "ai_collaboration/README.md"}
                  or name.startswith("docs/") and not name.startswith("docs/superpowers/"))
        if path.suffix.lower() not in {".py", ".md"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{name}: cannot read UTF-8: {exc}; save source/docs as UTF-8.")
            continue
        if path.suffix == ".py":
            errors.extend(check_source(name, text))
        if is_agents:
            limit = 6000 if name == "AGENTS.md" else 3000
            if path.stat().st_size > limit:
                errors.append(f"{name}: exceeds {limit} byte context budget; move details into linked docs.")
        if path.suffix == ".md" and (is_doc or is_agents):
            errors.extend(check_doc_links(root, name, text))
    return errors


def build_code_map(root: Path, paths: list[str]) -> dict:
    """Fresh Python import graph and signatures, not a dynamic call graph."""
    trees, modules = {}, {}
    for name in sorted(paths):
        path = root / name
        if path.suffix != ".py" or private_file(name) or not path.is_file():
            continue
        if not path.resolve().is_relative_to(root.resolve()):
            continue
        trees[name] = ast.parse(path.read_text(encoding="utf-8-sig"), filename=name)
        module = name[:-3].replace("/", ".")
        modules[module.removesuffix(".__init__")] = name
    graph = {}
    for name, tree in trees.items():
        current = name[:-3].replace("/", ".")
        package = current.rsplit(".", 1)[0] if "." in current else ""
        imports, api = set(), []
        for node in ast.walk(tree):
            candidates = []
            if isinstance(node, ast.Import):
                candidates = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    prefix = package.split(".") if package else []
                    prefix = prefix[:len(prefix) - node.level + 1]
                    base = ".".join(prefix + ([node.module] if node.module else []))
                else:
                    base = node.module or ""
                candidates = [base] + [f"{base}.{alias.name}".strip(".") for alias in node.names]
            for candidate in candidates:
                # Longest local module prefix; unresolved/dynamic imports stay unknown.
                while candidate:
                    if candidate in modules:
                        if modules[candidate] != name:
                            imports.add(modules[candidate])
                        # Absolute submodule imports execute ancestor package initializers.
                        # The caller's own package has already been initialized.
                        pieces = candidate.split(".")
                        for size in range(1, len(pieces)):
                            ancestor = ".".join(pieces[:size])
                            initializer = modules.get(ancestor)
                            already_in_package = package == ancestor or package.startswith(ancestor + ".")
                            if initializer and initializer.endswith("/__init__.py") and not already_in_package:
                                imports.add(initializer)
                        break
                    candidate = candidate.rpartition(".")[0]

        def definitions(nodes, prefix=""):
            for node in nodes:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbol = prefix + node.name
                    signature = (f"class {node.name}" if isinstance(node, ast.ClassDef)
                                 else f"{node.name}({ast.unparse(node.args)})" +
                                 (f" -> {ast.unparse(node.returns)}" if node.returns else ""))
                    api.append({"name": symbol, "line": node.lineno, "end_line": node.end_lineno, "signature": signature})
                    if isinstance(node, ast.ClassDef):
                        definitions(node.body, symbol + ".")
        definitions(tree.body)
        graph[name] = {"imports": sorted(imports), "api": api}
    return graph


def file_context(graph: dict, name: str, limit: int) -> dict:
    if name not in graph:
        raise ValueError(f"{name} is not indexed; choose a repository Python file from map")
    seen, pending = {name}, [name]
    while pending:
        target = pending.pop()
        for caller, node in graph.items():
            if caller not in seen and target in node["imports"]:
                seen.add(caller)
                pending.append(caller)
    dependents = sorted(seen - {name})
    node = graph[name]
    return {"file": name, "imports": node["imports"], "api": node["api"][:limit],
            "api_total": len(node["api"]), "dependents": dependents[:limit],
            "dependents_total": len(dependents)}


def related_knowledge(root: Path, name: str) -> list[dict]:
    index = json.loads((root / "docs/context-index.json").read_text(encoding="utf-8"))
    if not isinstance(index, dict) or not isinstance(index.get("entries"), list):
        raise ValueError("docs/context-index.json must contain an entries list")
    selected, ids = [], set()
    for entry in index["entries"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("id"), str)
                or entry["id"] in ids or not isinstance(entry.get("summary"), str)):
            raise ValueError("context-index entry needs a unique id and summary")
        ids.add(entry["id"])
        for field in ("touches", "read"):
            values = entry.get(field)
            if not isinstance(values, list) or not values or not all(isinstance(v, str) and v for v in values):
                raise ValueError(f"context-index {entry['id']} needs nonempty {field} paths")
        for target in entry["read"]:
            path = root / target
            if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(f"context-index {entry['id']}: missing/local-only evidence {target}")
        if any(fnmatchcase(name, pattern) for pattern in entry["touches"]):
            selected.append(entry)
    return selected


def data_prerequisites(root: Path) -> list[str]:
    errors = []
    for name in ("train/rulebook.md", "train/questions.jsonl", "train/answers.jsonl"):
        if not (root / name).is_file():
            errors.append(f"Missing {name}; extract the official train download locally.")
    if not any((root / "cache").glob("*/don_hang.parquet")):
        errors.append("Missing cache/*/don_hang.parquet; run python load_all.py with local datasets first.")
    return errors


def validate_verification(result: dict) -> list[str]:
    compared, matched = result.get("compared"), result.get("matched_gold")
    if type(compared) is not int or compared <= 0:
        return ["Data verification compared zero questions or has an invalid report; inspect local input/cache and selection."]
    errors = []
    if type(matched) is not int or matched != compared:
        errors.append(f"Data verification matched_gold={matched}/{compared}; inspect reports/harness/business_verification.json.")
    if result.get("errors") != []:
        errors.append("Data verification has errors or lacks its error list; inspect the local report.")
    return errors


def report(errors: list[str]) -> bool:
    for error in errors:
        print(f"FAIL {error}", flush=True)
    return not errors


def run(root: Path, *args: str) -> bool:
    print("RUN " + " ".join(args), flush=True)
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run(list(args), cwd=root, env=env).returncode == 0


def doctor(root: Path) -> int:
    print(f"Repository: {root}\nPython: {sys.executable}\nVersion: {sys.version.split()[0]}")
    print("Git: " + git(root, "--version").strip())
    errors = []
    for package, wanted in re.findall(r"^([\w-]+)==([^\s#]+)", (root / "requirements.txt").read_text(encoding="utf-8"), re.MULTILINE):
        try:
            actual = metadata.version(package)
        except metadata.PackageNotFoundError:
            actual = "MISSING"
        print(f"Dependency: {package} {actual} (pinned {wanted})")
        if actual != wanted:
            errors.append(f"{package}: use this interpreter with -m pip install -r requirements.txt.")
    missing = data_prerequisites(root)
    print("Local data: " + ("not ready (optional for full/CI)" if missing else "ready for selected regression"))
    return 0 if report(errors) else 1


def check(root: Path, profile: str) -> int:
    if profile == "data" and not report(data_prerequisites(root)):
        return 1
    paths = repository_paths(root)
    errors = [f"{name}: required harness doc missing; restore it." for name in REQUIRED_DOCS if not (root / name).is_file()]
    errors.extend(check_paths(root, paths))
    if (root / "docs/context-index.json").is_file():
        try:
            related_knowledge(root, "")  # Validate every entry, including those not selected today.
        except ValueError as exc:
            errors.append(str(exc))
    if not report(errors):
        return 1
    if not run(root, "git", "diff", "--check") or not run(root, "git", "diff", "--cached", "--check"):
        return 1
    print(f"PASS fast: {len(paths)} repository files inspected; ignored local datasets not traversed.", flush=True)
    if profile == "fast":
        return 0
    if not run(root, sys.executable, "-m", "pytest", "tests/", "evaluate/", "-q", "-rs", "-m", "not local_data"):
        return 1
    if profile == "data":
        if not run(root, sys.executable, "-m", "pytest", "tests/", "evaluate/", "-q", "-rs", "-m", "local_data"):
            return 1
        output = root / "reports" / "harness" / "business_verification"
        if not run(root, sys.executable, "verify_business.py", "--out", str(output)):
            return 1
        result = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
        if not report(validate_verification(result)):
            return 1
        print(f"PASS selected data regression: {result['matched_gold']}/{result['compared']}; not full-train PA.")
    print(f"PASS {profile}", flush=True)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Inspect interpreter, pinned dependencies and optional local data")
    checks = commands.add_parser("check", help="Run the same checks used by agents and CI")
    checks.add_argument("--profile", choices=("fast", "full", "data"), default="full")
    for command in ("map", "context"):
        context = commands.add_parser(command, help="Fresh Python imports/API/related decisions (JSON; no model or cache)")
        if command == "context":
            context.add_argument("file", help="Repository-relative Python file")
        context.add_argument("--limit", type=int, default=30, help="Maximum entries per output section (1..200)")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 10):
        print("FAIL Python >=3.10 is required; use the project virtual environment.")
        return 1
    try:
        if args.command in {"map", "context"}:
            if not 1 <= args.limit <= 200:
                raise ValueError("--limit must be between 1 and 200")
            graph = build_code_map(ROOT, repository_paths(ROOT))
            if args.command == "map":
                result = {"files_total": len(graph), "files": [
                    {"file": name, "definitions": len(node["api"]), "imports": node["imports"]}
                    for name, node in list(graph.items())[:args.limit]
                ]}
            else:
                name = args.file.replace("\\", "/")
                result = file_context(graph, name, args.limit)
                knowledge = related_knowledge(ROOT, name)
                result.update(knowledge=knowledge[:args.limit], knowledge_total=len(knowledge))
            result["scope"] = "Current working-tree Python imports/signatures; dynamic calls and data dependencies require source review."
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        return doctor(ROOT) if args.command == "doctor" else check(ROOT, args.profile)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL harness: {exc}; run doctor and inspect the command/input above.", flush=True)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
