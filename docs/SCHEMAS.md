# Schemas & storage contracts

Synaptic stores data in two places:

1) **Append-only ledgers** (JSONL):
- `atoms.jsonl`: immutable creation events (one per atom)
- `activations.jsonl`: queries and which atoms were used (receipts)

2) **SQLite index** (mutable, derived):
- `atoms`: current metadata + strength (`w`) + usage counters
- `atoms_fts`: full-text search (FTS5 when available)
- `edges`: neighbor + co-activation graph

## Stability rules
- JSONL line formats should remain **backward-compatible** whenever possible.
- SQLite schema may evolve, but migrations should be explicit (or index rebuildable from JSONL).
- If you change on-disk formats: bump version and document in `CHANGELOG.md`.
