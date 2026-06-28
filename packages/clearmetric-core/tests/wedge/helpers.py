"""Shared helpers for wedge/compiler tests."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

JAFFLE_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "lineage"
    / "projects"
    / "jaffle_shop"
)
JAFFLE_WAREHOUSE_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "wedge"
    / "jaffle_warehouse_schema.json"
)


def copy_jaffle_fixture(project_dir: Path) -> None:
    target = project_dir / "target"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(JAFFLE_FIXTURE / "manifest.json", target / "manifest.json")
    compiled_src = JAFFLE_FIXTURE / "compiled"
    if compiled_src.is_dir():
        shutil.copytree(compiled_src, target / "compiled", dirs_exist_ok=True)


def write_policy(project_dir: Path) -> None:
    policy_dir = project_dir / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "rules.yaml").write_text("rules: []\n", encoding="utf-8")


def write_warehouse_schema(project_dir: Path) -> None:
    shutil.copy2(JAFFLE_WAREHOUSE_SCHEMA, project_dir / "warehouse_schema.json")


def write_wedge_config(project_dir: Path) -> None:
    write_policy(project_dir)
    (project_dir / "clearmetric.yaml").write_text(
        yaml.safe_dump(
            {
                "version": 1,
                "dialect": "postgres",
                "sources": {
                    "warehouse": {
                        "kind": "information_schema",
                        "path": "./warehouse_schema.json",
                    },
                    "dbt": {"manifest": "./target/manifest.json"},
                },
                "posture": "strict",
                "policy": {"rules": "./policy/rules.yaml"},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def setup_wedge_project(project_dir: Path) -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    copy_jaffle_fixture(project_dir)
    write_warehouse_schema(project_dir)
    write_wedge_config(project_dir)
    return project_dir


def run_cm_subprocess(
    project_dir: Path,
    *args: str,
    experimental: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if experimental:
        env["CM_EXPERIMENTAL"] = "1"
    else:
        env.pop("CM_EXPERIMENTAL", None)
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "clearmetric.cli",
            "--project-dir",
            str(project_dir),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
