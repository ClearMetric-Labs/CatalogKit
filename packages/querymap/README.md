# querymap

`querymap` maps one supported SQL statement into a deterministic `QueryMap`
artifact so you can answer "what feeds what in this query?" fast.

It is a narrow static-analysis tool:

- input: exactly one SQL statement from one SQL file
- output: canonical relations, relation usages, dependency edges, and warnings
- no warehouse credentials
- no dbt project
- no AI key

## Install

```bash
python -m pip install querymap
```

For local development:

```bash
python -m pip install -e ../catalog-core
python -m pip install -e ".[dev,release]"
```

## Quickstart

```bash
querymap --dialect postgres ./examples/ugly_real_world.sql
querymap --dialect postgres --format json ./examples/ugly_real_world.sql
```

## Output Contract

`querymap` preserves its public `QueryMap` shape:

- `summary`
- `relations`
- `relation_usages`
- `edges`
- `outputs`
- `warnings`

For CatalogKit composition, the package also exposes a shared
`CatalogArtifact` builder backed by `catalog-core`.

The shared core artifact contains:

- `version`
- `nodes`
- `edges`
- `warnings`

## Supported Statements

`querymap` accepts exactly one supported statement per invocation:

- `SELECT ...`
- `INSERT ... SELECT ...`
- `CREATE ... AS SELECT ...`

Unsupported statement shapes fail loudly.

## Contract Docs

- [`../catalog-core/docs/contract.md`](../catalog-core/docs/contract.md)
- [`docs/limitations.md`](docs/limitations.md)
