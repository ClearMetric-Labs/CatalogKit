"""Frontend contract emitter."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from clearmetric.compiler.models import CompiledGraph
from clearmetric.core.contracts import QueryContract, require_compiled_query_contract
from clearmetric.core.errors import CompilerError
from clearmetric.core.models import Node
from clearmetric.projection import project_for_emit

if TYPE_CHECKING:
    from clearmetric.policy import GatedContext


def emit_frontend_contract(compiled: CompiledGraph, ctx: GatedContext) -> str:
    gated = project_for_emit(
        compiled.artifact,
        identity=ctx.identity,
        rules=ctx.rules,
    )
    violations: list[str] = []
    validated: list[tuple[str, QueryContract, Node]] = []
    for node in gated.nodes:
        if node.kind != "query":
            continue
        try:
            sql, contract = require_compiled_query_contract(node)
        except CompilerError as exc:
            violations.append(str(exc))
            continue
        validated.append((sql, contract, node))
    if violations:
        raise CompilerError("; ".join(violations))
    contracts = [
        {
            "id": node.id,
            "name": node.name,
            "sql": sql,
            "parameters": contract.parameters,
        }
        for sql, contract, node in validated
    ]
    return json.dumps({"version": "1", "queries": contracts}, indent=2, sort_keys=False)
