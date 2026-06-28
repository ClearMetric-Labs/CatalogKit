# Backbone Lab Example

> **Experimental / internal architecture proof / not a shipped capability / no stability guarantee.**

This example proves Module A primitives on the same graph as the wedge. It is **not**
part of the public product promise in the root README.

## Prerequisites

```bash
pip install -e "packages/clearmetric-core[dev,runtime]"
cd examples/backbone-lab
```

Warehouse and dbt fixtures are referenced from committed paths under
`packages/clearmetric-core/tests/fixtures/` (same pattern as wedge-jaffle).

## Demo

```bash
export CM_EXPERIMENTAL=1
cm compile --format json > graph.json
cm compile --format catalog > catalog.json
cm compile --format consumer-catalog --identity analyst > consumer_catalog.json
cm compile --format frontend-contract --identity analyst > contracts.json
cm impact orders.amount --upstream
cm query --identity analyst query:executive_revenue
```
