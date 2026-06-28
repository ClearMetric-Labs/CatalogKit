"""Policy rules loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from clearmetric.core.errors import PolicyError
from pydantic import ValidationError

from .models import PolicyRulesFile


@dataclass(frozen=True)
class GatedContext:
    identity: str
    rules: PolicyRulesFile


def require_gated_identity(identity: str | None) -> str:
    """Validate and normalize identity for gated consumer operations."""
    if not identity or not identity.strip():
        raise PolicyError("gated operation requires identity")
    return identity.strip()


def load_rules(path: str | Path) -> PolicyRulesFile:
    rules_path = Path(path)
    if not rules_path.is_file():
        raise PolicyError(f"Policy rules file not found: {rules_path}")
    try:
        raw = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise PolicyError(f"Policy rules file is not valid YAML: {rules_path}") from exc
    if raw is None:
        raw = {"rules": []}
    if not isinstance(raw, dict):
        raise PolicyError(f"Policy rules file must be a mapping: {rules_path}")
    try:
        return PolicyRulesFile.model_validate(raw)
    except ValidationError as exc:
        raise PolicyError(
            f"Policy rules file failed validation: {rules_path}: {exc}"
        ) from exc


def gated_context(*, rules_path: str | Path, identity: str | None) -> GatedContext:
    """Load identity and policy rules for a gated consumer operation."""
    return GatedContext(
        identity=require_gated_identity(identity),
        rules=load_rules(rules_path),
    )
