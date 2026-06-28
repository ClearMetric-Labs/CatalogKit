"""Backbone lab MVP subprocess demo."""

from __future__ import annotations

import json
from pathlib import Path

from tests.backbone_lab.helpers import setup_backbone_lab_project
from tests.wedge.helpers import run_cm_subprocess


def test_mvp_demo_same_canonical_id_flow(tmp_path: Path):
    project_dir = setup_backbone_lab_project(tmp_path / "lab")

    compile_json = run_cm_subprocess(project_dir, "compile", "--format", "json")
    assert compile_json.returncode == 0, compile_json.stderr
    graph = json.loads(compile_json.stdout)
    graph_ids = {node["id"] for node in graph["nodes"]}
    assert "column:orders.amount" in graph_ids
    assert "metric:executive_revenue" in graph_ids
    assert "query:executive_revenue" in graph_ids

    compile_catalog = run_cm_subprocess(project_dir, "compile", "--format", "catalog")
    assert compile_catalog.returncode == 0, compile_catalog.stderr
    catalog = json.loads(compile_catalog.stdout)
    catalog_ids = {node["id"] for node in catalog["nodes"]}
    assert "column:orders.amount" in catalog_ids
    assert "metric:executive_revenue" not in catalog_ids
    assert "query:executive_revenue" not in catalog_ids

    compile_openlineage = run_cm_subprocess(
        project_dir, "compile", "--format", "openlineage"
    )
    assert compile_openlineage.returncode == 0, compile_openlineage.stderr

    compile_consumer = run_cm_subprocess(
        project_dir,
        "compile",
        "--format",
        "consumer-catalog",
        "--identity",
        "analyst",
        experimental=True,
    )
    assert compile_consumer.returncode == 0, compile_consumer.stderr
    consumer = json.loads(compile_consumer.stdout)
    consumer_ids = {node["id"] for node in consumer["nodes"]}
    assert "column:orders.amount" in consumer_ids
    assert "metric:executive_revenue" in consumer_ids
    assert "query:executive_revenue" in consumer_ids

    compile_contracts = run_cm_subprocess(
        project_dir,
        "compile",
        "--format",
        "frontend-contract",
        "--identity",
        "analyst",
        experimental=True,
    )
    assert compile_contracts.returncode == 0, compile_contracts.stderr
    contracts = json.loads(compile_contracts.stdout)
    assert contracts["queries"][0]["id"] == "query:executive_revenue"
    assert "SELECT" in contracts["queries"][0]["sql"]

    impact = run_cm_subprocess(
        project_dir,
        "impact",
        "orders.amount",
        "--upstream",
    )
    assert impact.returncode == 0, impact.stderr
    assert "orders.amount" in impact.stdout or "column:orders.amount" in impact.stdout

    query = run_cm_subprocess(
        project_dir,
        "query",
        "--identity",
        "analyst",
        "query:executive_revenue",
        experimental=True,
    )
    assert query.returncode == 0, query.stderr
    rows = json.loads(query.stdout)
    assert rows[0]["net_revenue"] == 100
