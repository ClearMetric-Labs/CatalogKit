"""Policy-gated consumer catalog emitter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from clearmetric.compiler.models import CompiledGraph
from clearmetric.core import render_json
from clearmetric.projection import project_consumer_catalog

if TYPE_CHECKING:
    from clearmetric.policy import GatedContext


def emit_consumer_catalog(compiled: CompiledGraph, ctx: GatedContext) -> str:
    catalog = project_consumer_catalog(
        compiled.artifact,
        identity=ctx.identity,
        rules=ctx.rules,
    )
    return json.dumps(render_json(catalog), indent=2, sort_keys=False)
