# Consumer reference apps

Thin **read-only** viewers over a versioned **artifact bundle**. They prove the
backbone consumer pattern without duplicating policy, projection, or traversal.

```text
cm compile / cm impact
→ validated JSON bundle (bundle.manifest.json)
→ vanilla viewer reads bundle
→ no browser-side policy
```

## Quick start

From the repository root:

```bash
python -m http.server 8000 --directory examples/consumers
```

Open:

- **Catalog viewer:** `http://127.0.0.1:8000/catalog-viewer/index.html?bundle=../bundles/minimal`
- **Lineage explorer:** `http://127.0.0.1:8000/lineage-explorer/index.html?bundle=../bundles/lineage-demo`

The `?bundle=` parameter is **required**. It must point at a directory containing
`bundle.manifest.json`.

### Committed bundles

| Bundle | Fixture | Use |
|--------|---------|-----|
| **`minimal`** | wedge-jaffle (dbt + warehouse) | Catalog richness, warehouse metadata, `source_disagreement` warning. Column impact may be empty — that is honest for this fixture. |
| **`lineage-demo`** | sql_folder (plain SQL) | Non-empty column impact trace for lineage explorer screenshots. |

Cross-linking between viewers keeps the same `?bundle=` parameter so you can navigate within one bundle.

## Regenerate bundles

```bash
python scripts/consumers/build_bundle.py --scenario examples/consumers/scenarios/minimal
python scripts/consumers/build_bundle.py --scenario examples/consumers/scenarios/lineage-demo
```

## Layout

```text
examples/consumers/
  projects/lineage-sql-folder/  # ClearMetric project for lineage-demo
  shared/artifact-kit.mjs       # loader helpers only
  catalog-viewer/               # browse catalog artifact
  lineage-explorer/             # flat impact list + links
  scenarios/                    # scenario recipes + checks.yaml
  bundles/minimal/              # committed wedge fixture
  bundles/lineage-demo/         # committed sql_folder fixture
```

Apps bind to **`bundle.manifest.json` + declared lanes** — never to a specific
project id in code.

## Security

Viewers display **pre-emitted** artifacts only. RBAC, RLS, masking, and
governance projection run at compile time in `policy.gate` and
`projection.apply_policy`. The browser does not re-gate.

V0 bundles use the **admin lane** (`json`, `catalog`, ungated `impact`). The bundle
builder rejects lab consumer formats at build time. Lab formats (`consumer-catalog`,
`frontend-contract`, `ai-context`) remain optional scenario recipes behind
`CM_EXPERIMENTAL=1` — not part of the public wedge demo.

## Specs

- [`spec/consumer-bundle.schema.json`](../../spec/consumer-bundle.schema.json)
- [`spec/impact-output.schema.json`](../../spec/impact-output.schema.json)
- [`spec/consumer-envelope.schema.json`](../../spec/consumer-envelope.schema.json)
- [`spec/catalog-artifact.schema.json`](../../spec/catalog-artifact.schema.json)

Validation is centralized in `clearmetric.core.validate`.
