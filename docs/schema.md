# Result schema v1.0

Top-level fields:

- `schema_version`
- `tool`
- `input`
- `provenance`
- `summary`
- `findings`
- `metrics`
- `backlog`

Each finding includes `check_id`, `severity`, `message`, `evidence`, and optional `suggested_action`.

Each backlog item exposes `severity`, `impact`, `effort`, and `priority` where `priority = (severity_weight × impact) ÷ effort`.
