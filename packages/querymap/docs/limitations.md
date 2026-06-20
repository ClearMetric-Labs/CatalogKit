# querymap Limitations

`querymap` is intentionally deterministic and narrow.

## Supported Input

`querymap` accepts exactly one supported statement per invocation:

- `SELECT ...`
- `INSERT ... SELECT ...`
- `CREATE ... AS SELECT ...`

## Guarantees

`querymap` guarantees:

- one supported SQL statement per invocation
- dialect-aware parsing through `sqlglot`
- canonical table and CTE relations
- deterministic relation dependency edges
- stable `QueryMap` output for the public package surface
- loud failure on unsupported input

## Current Boundaries

`querymap` does **not** currently model:

- output column lineage
- output-source attribution
- first-class join edges
- wrapper targets as output nodes
- Mermaid rendering

## Warning-Based Behavior

`querymap` warns instead of failing when the relation structure is still clear
enough to model honestly.
