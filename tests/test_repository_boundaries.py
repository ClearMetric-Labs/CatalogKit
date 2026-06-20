from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGES_ROOT = REPO_ROOT / "packages"
CORE_IMPORT = "catalog_core"
SHARED_CLASS_NAMES = {"Node", "Edge", "Evidence", "Warning"}


def test_tool_packages_only_depend_on_catalog_core_and_themselves():
    package_names = _package_names()

    for package_name in package_names:
        package_root = PACKAGES_ROOT / package_name / package_name.replace("-", "_")
        if not package_root.exists():
            continue

        forbidden_prefixes = {
            other_name.replace("-", "_")
            for other_name in package_names
            if other_name not in {package_name, "catalog-core"}
        }
        if package_name == "catalog-core":
            forbidden_prefixes = {
                other_name.replace("-", "_")
                for other_name in package_names
                if other_name != "catalog-core"
            }

        violations: list[str] = []
        for path in package_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith(tuple(forbidden_prefixes)):
                            violations.append(f"{path}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    if node.module.startswith(tuple(forbidden_prefixes)):
                        violations.append(f"{path}: from {node.module} import ...")

        assert violations == []


def test_shared_model_class_names_exist_only_in_catalog_core():
    violations: list[str] = []
    core_models_path = PACKAGES_ROOT / "catalog-core" / "catalog_core" / "models.py"

    for path in PACKAGES_ROOT.rglob("*.py"):
        if path == core_models_path:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in SHARED_CLASS_NAMES:
                violations.append(f"{path}: class {node.name}")

    assert violations == []


def _package_names() -> list[str]:
    return sorted(path.name for path in PACKAGES_ROOT.iterdir() if path.is_dir())
