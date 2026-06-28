#!/usr/bin/env python3
"""Build or validate a consumer artifact bundle from a scenario recipe."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from clearmetric.cli.runner import run_cm
from clearmetric.core import __version__ as clearmetric_version
from clearmetric.core.errors import ValidationError
from clearmetric.core.validate import (
    load_artifact_file,
    load_bundle_manifest_file,
    load_impact_output_file,
    validate_bundle_artifact_file,
    validate_bundle_manifest_dict,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_BUNDLES = _REPO_ROOT / "examples" / "consumers" / "bundles"

_V0_COMPILE_FORMATS = frozenset({"json", "catalog"})
_MANIFEST_ARTIFACT_KEY = {"json": "graph", "catalog": "catalog"}
_V0_LANE = "admin"


def _load_scenario(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit(f"Scenario must be a YAML mapping: {path}")
    return payload


def _resolve_project_dir(scenario_path: Path, scenario: dict[str, Any]) -> Path:
    project_dir = scenario.get("project_dir")
    if not isinstance(project_dir, str) or not project_dir.strip():
        raise SystemExit("project_dir is required for mode=project")
    resolved = (scenario_path.parent / project_dir).resolve()
    if not resolved.is_dir():
        raise SystemExit(f"project_dir does not exist: {resolved}")
    return resolved


def _resolve_bundle_dir(
    scenario_path: Path,
    scenario: dict[str, Any],
    out: Path | None,
    *,
    mode: str,
) -> Path:
    if out is not None:
        return out.resolve()
    if mode == "prebuilt":
        bundle_dir = scenario.get("bundle_dir")
        if isinstance(bundle_dir, str) and bundle_dir.strip():
            resolved = (scenario_path.parent / bundle_dir.strip()).resolve()
            if not resolved.is_dir():
                raise SystemExit(f"bundle_dir does not exist: {resolved}")
            return resolved
    scenario_id = str(scenario.get("id") or scenario_path.parent.name)
    return (_DEFAULT_BUNDLES / scenario_id).resolve()


def _validate_scenario_output(item: dict[str, Any]) -> tuple[str, str, str]:
    compile_format = str(item.get("compile_format") or "").strip()
    relative_out = str(item.get("out") or "").strip()
    if not compile_format or not relative_out:
        raise SystemExit("each output requires compile_format and out")
    if compile_format not in _V0_COMPILE_FORMATS:
        supported = ", ".join(sorted(_V0_COMPILE_FORMATS))
        raise SystemExit(
            f"V0 bundle builder supports admin-lane compile_format: {supported}. "
            f"Got {compile_format!r}. Lab consumer formats are not buildable yet — "
            "see examples/consumers/scenarios/external/README.md."
        )
    lane = str(item.get("lane") or _V0_LANE).strip()
    if lane != _V0_LANE:
        raise SystemExit(
            f"V0 bundle builder supports lane {_V0_LANE!r} only. Got {lane!r}."
        )
    if "identity" in item:
        raise SystemExit(
            "V0 bundle builder does not support consumer-lane identity on outputs."
        )
    manifest_key = _MANIFEST_ARTIFACT_KEY[compile_format]
    return compile_format, relative_out, manifest_key


def _parse_impact_recipe(item: Any) -> tuple[str, str, str, str]:
    if not isinstance(item, dict):
        raise SystemExit("each impact must be a mapping")
    selection = str(item.get("selection") or "").strip()
    direction = str(item.get("direction") or "").strip()
    manifest_key = str(item.get("manifest_key") or "").strip()
    relative_out = str(item.get("out") or "").strip()
    if not selection or not direction or not manifest_key or not relative_out:
        raise SystemExit(
            "each impact requires selection, direction, manifest_key, and out"
        )
    if direction not in ("upstream", "downstream"):
        raise SystemExit(
            f"impact direction must be 'upstream' or 'downstream'; got {direction!r}"
        )
    return selection, direction, manifest_key, relative_out


def _parse_impact_recipes(impacts: list[Any]) -> list[tuple[str, str, str, str]]:
    recipes: list[tuple[str, str, str, str]] = []
    keys: set[str] = set()
    for item in impacts:
        recipe = _parse_impact_recipe(item)
        manifest_key = recipe[2]
        if manifest_key in keys:
            raise SystemExit(f"duplicate impact manifest_key {manifest_key!r}")
        keys.add(manifest_key)
        recipes.append(recipe)
    return recipes


def _resolve_default_impact_key(
    scenario: dict[str, Any], allowed_keys: set[str]
) -> str:
    defaults = scenario.get("defaults")
    if not isinstance(defaults, dict):
        raise SystemExit("scenario requires defaults.impact_key")
    default_key = str(defaults.get("impact_key") or "").strip()
    if not default_key or default_key not in allowed_keys:
        raise SystemExit(
            f"defaults.impact_key must name a manifest impact key; got {default_key!r}"
        )
    return default_key


def _write_and_validate_output(
    out_dir: Path,
    relative_path: str,
    content: str,
    *,
    kind: str,
    lane: str | None = None,
) -> None:
    target = out_dir / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    if kind == "catalog-artifact":
        if lane is None:
            raise SystemExit("catalog-artifact write requires lane")
        validate_bundle_artifact_file(target, lane=lane)
        return
    if kind == "impact-output":
        load_impact_output_file(target)
        return
    raise SystemExit(f"Unsupported artifact kind: {kind}")


def _build_project_bundle(
    scenario_path: Path,
    scenario: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    project_dir = _resolve_project_dir(scenario_path, scenario)
    outputs = scenario.get("outputs")
    impacts = scenario.get("impacts")
    if not isinstance(outputs, list) or not outputs:
        raise SystemExit("outputs must be a non-empty list")
    if not isinstance(impacts, list) or not impacts:
        raise SystemExit("impacts must be a non-empty list")

    impact_recipes = _parse_impact_recipes(impacts)
    default_key = _resolve_default_impact_key(
        scenario, {manifest_key for _s, _d, manifest_key, _o in impact_recipes}
    )

    artifact_refs: dict[str, Any] = {}
    for item in outputs:
        if not isinstance(item, dict):
            raise SystemExit("each output must be a mapping")
        compile_format, relative_out, manifest_key = _validate_scenario_output(item)
        if manifest_key in artifact_refs:
            raise SystemExit(
                f"duplicate manifest artifact key {manifest_key!r} in outputs"
            )
        result = run_cm(project_dir, "compile", "--format", compile_format)
        if result.returncode != 0:
            raise SystemExit(
                f"cm compile --format {compile_format} failed:\n{result.stderr}"
            )
        _write_and_validate_output(
            out_dir,
            relative_out,
            result.stdout,
            lane=_V0_LANE,
            kind="catalog-artifact",
        )
        artifact_refs[manifest_key] = {
            "path": relative_out,
            "kind": "catalog-artifact",
            "lane": _V0_LANE,
        }

    if "graph" not in artifact_refs or "catalog" not in artifact_refs:
        raise SystemExit("outputs must include json (graph) and catalog")

    impact_refs: dict[str, Any] = {}
    for selection, direction, manifest_key, relative_out in impact_recipes:
        flag = "--upstream" if direction == "upstream" else "--downstream"
        result = run_cm(project_dir, "impact", selection, flag, "--format", "json")
        if result.returncode != 0:
            raise SystemExit(f"cm impact failed for {selection}:\n{result.stderr}")
        _write_and_validate_output(
            out_dir,
            relative_out,
            result.stdout,
            kind="impact-output",
        )
        impact_refs[manifest_key] = {
            "path": relative_out,
            "selection": selection,
            "direction": direction,
        }

    manifest = {
        "schema_version": "1",
        "scenario_id": str(scenario.get("id") or scenario_path.parent.name),
        "label": str(scenario.get("label") or scenario_path.parent.name),
        "artifacts": {
            "graph": artifact_refs["graph"],
            "catalog": artifact_refs["catalog"],
            "impacts": impact_refs,
        },
        "defaults": {"impact_key": default_key},
    }
    provenance = scenario.get("provenance")
    if isinstance(provenance, str) and provenance.strip():
        manifest["provenance"] = provenance.strip()
    return manifest


def _validate_prebuilt_bundle(out_dir: Path) -> dict[str, Any]:
    manifest_path = out_dir / "bundle.manifest.json"
    if not manifest_path.is_file():
        raise SystemExit(
            f"prebuilt bundle missing bundle.manifest.json: {manifest_path}"
        )
    try:
        manifest = load_bundle_manifest_file(manifest_path)
    except ValidationError as exc:
        raise SystemExit(f"bundle.manifest.json validation failed:\n{exc}") from exc
    artifacts = manifest["artifacts"]
    for key in ("graph", "catalog"):
        ref = artifacts[key]
        validate_bundle_artifact_file(out_dir / ref["path"], lane=ref["lane"])
    for ref in artifacts["impacts"].values():
        load_impact_output_file(out_dir / ref["path"])
    return manifest


def _write_meta(out_dir: Path, manifest: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "clearmetric_version": clearmetric_version,
        "scenario_id": manifest["scenario_id"],
    }
    (out_dir / "meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )


def _write_manifest_and_meta(out_dir: Path, manifest: dict[str, Any]) -> None:
    try:
        validate_bundle_manifest_dict(manifest)
    except ValidationError as exc:
        raise SystemExit(f"bundle manifest validation failed:\n{exc}") from exc
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "bundle.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    _write_meta(out_dir, manifest)


def _staging_dir(target: Path) -> Path:
    return target.parent / f"{target.name}.tmp-build"


def _publish_staging_dir(staging: Path, target: Path) -> None:
    if staging.resolve() == target.resolve():
        raise SystemExit("staging dir must differ from target")
    if target.exists():
        shutil.rmtree(target)
    staging.rename(target)


def _cleanup_staging(staging: Path) -> None:
    if staging.is_dir():
        shutil.rmtree(staging)


def _build_project_bundle_atomic(
    scenario_path: Path,
    scenario: dict[str, Any],
    target: Path,
) -> dict[str, Any]:
    staging = _staging_dir(target)
    _cleanup_staging(staging)
    try:
        manifest = _build_project_bundle(scenario_path, scenario, staging)
        _write_manifest_and_meta(staging, manifest)
        load_artifact_file(staging / manifest["artifacts"]["graph"]["path"])
        _publish_staging_dir(staging, target)
        return manifest
    except BaseException:
        _cleanup_staging(staging)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scenario",
        required=True,
        type=Path,
        help="Path to scenario.yaml or scenario directory",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output bundle directory (default: examples/consumers/bundles/<id>/)",
    )
    args = parser.parse_args(argv)

    scenario_path = args.scenario.resolve()
    if scenario_path.is_dir():
        scenario_path = scenario_path / "scenario.yaml"
    if not scenario_path.is_file():
        raise SystemExit(f"Scenario file not found: {scenario_path}")

    scenario = _load_scenario(scenario_path)
    mode = str(scenario.get("mode") or "project").strip()
    out_dir = _resolve_bundle_dir(scenario_path, scenario, args.out, mode=mode)

    if mode == "project":
        manifest = _build_project_bundle_atomic(scenario_path, scenario, out_dir)
    elif mode == "prebuilt":
        manifest = _validate_prebuilt_bundle(out_dir)
        _write_meta(out_dir, manifest)
    else:
        raise SystemExit(f"Unsupported scenario mode: {mode!r}")

    print(f"bundle ready: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
