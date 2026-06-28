# Backbone Lab (Experimental / Internal)

> **Experimental / internal architecture proof / not a shipped capability / no stability guarantee.**

This document describes **Backbone Lab** flows used to prove that Module A primitives
(contracts, intent, policy gate, consumer catalog, frontend contracts, runtime harness)
work on the same graph as the wedge. These flows are **not** part of the public product
promise in [README.md](../README.md) or [v1-boundary.md](v1-boundary.md).

## Public vs lab split

| Public wedge (always) | Lab (experimental only) |
|-----------------------|-------------------------|
| Lineage, impact, cleaner | Intent YAML ingest |
| Admin catalog | Consumer catalog |
| OpenLineage export (ungated) | Frontend contract emitter |
| | `cm query` (DuckDB harness) |

**Adoption gate** blocks expanding README / marketing / production claims — not building
these primitives in code and tests.

## Enable lab CLI

Lab commands and compile formats require:

```bash
export CM_EXPERIMENTAL=1
```

Normal `cm --help` does not advertise lab formats. With `CM_EXPERIMENTAL=1`, help marks
them as experimental.

## Demo project

See [examples/backbone-lab/README.md](../examples/backbone-lab/README.md). The example
uses shared jaffle fixtures from `packages/clearmetric-core/tests/fixtures/`.

```bash
export CM_EXPERIMENTAL=1
cd examples/backbone-lab
cm compile --format json > graph.json
cm compile --format catalog > catalog.json
cm compile --format consumer-catalog --identity analyst > consumer_catalog.json
cm compile --format frontend-contract --identity analyst > contracts.json
cm impact orders.amount --upstream
cm query --identity analyst query:executive_revenue
```

## Architecture (lab code)

| Concern | Module / entry |
|---------|----------------|
| Identity + rules load | `policy.load.gated_context`, `require_gated_identity` |
| Consumer authz | `policy.gate.gate`, `require_allow` (sole authz entry) |
| Gated compile dispatch | `emitters.registry` (sole `gated_context` caller) |
| Consumer catalog | `emitters.consumer_catalog` via `project_consumer_catalog` |
| Frontend contracts | `emitters.frontend_contract` via `project_for_emit` |
| SQL compile onto graph | `compiler.compile_contracts.compile_query_contracts` (atomic two-pass) |
| Query execution | `runtime.execute_project_query` (gate → resolve → seed → DuckDB) |

Wedge compile formats (`json`, `text`, `catalog`, `openlineage`) never require `--identity`.

## Invariants (lab code)

- `policy.gate` is the sole consumer authz entry for projection, emitters, and runtime
- Missing `compiled_sql` → loud error at runtime (no `contract.sql` fallback)
- Missing fixture seed → loud `QueryExecutionError` (no silent skip)
- Policy exceptions → deny; empty rules → deny
- Admin `catalog` and `openlineage` remain ungated
- Lab CLI and formats are hidden unless `CM_EXPERIMENTAL=1`

## Not in lab scope

Live warehouse connector, cloud, catalog UI, dashboard renderer, AI agent product, docs
emitter, native RLS deployment, custom user checks, `cm serve`.
