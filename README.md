# Synaptic (fresh) — AI Memory Store

[![CI](https://github.com/resonantlabsai/synaptic/actions/workflows/ci.yml/badge.svg)](https://github.com/resonantlabsai/synaptic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/resonantlabsai/synaptic/blob/main/LICENSE)


Synaptic is a **local, cacheable memory system** designed to reduce context/token spend by turning valuable thoughts,
decisions, constraints, and insights into **small “memory atoms”** that can be retrieved, strengthened, decayed,
and pruned like synapses.

This repo is intentionally **not trading-specific**. It's a general-purpose AI memory layer.

## Core idea

- **Atoms** (neurons): small records worth keeping.
- **Strength** (synapse): the more an atom is used (retrieved/referenced), the more it strengthens.
- **Decay**: unused atoms slowly lose priority.
- **Pruning**: when space is constrained, weak / stale atoms are evicted.
- **L1 Retrieval**: find the most relevant atoms for a query.
- **L2 Discovery**: expand through neighbors + co-activation to surface adjacent ideas and propose new patterns
  (meta-atoms / clusters), similar in spirit to embeddings but richer.

Everything is **artifact-first**:
- append-only JSONL ledgers
- an SQLite index (FTS + edges)
- deterministic IDs + hashes

## Data layout

By default, Synaptic stores data in `./synaptic_data/` (override with `SYNAPTIC_HOME`).

```
synaptic_data/
  atoms.jsonl                 # memory atoms (append-only)
  activations.jsonl           # retrieval/use events (append-only)
  synaptic.sqlite             # SQLite index: atoms + FTS + edges + coactivations
  blobs/                      # optional larger payloads (future)
```

## Quick start

```bash
# from repo root
python -m synaptic.cli init

python -m synaptic.cli add --type idea --scope colony --tags orion,blob \
  --content "Guardian + TrustMeter gates are the civilizational control plane."

python -m synaptic.cli search "trust meter gates" --k 8
python -m synaptic.cli brief "what are our safety principles?" --k 10 --l2 8
python -m synaptic.cli prune --max-mb 50
```

## Slash-command / local tool integration

Synaptic is designed to sit behind a local executor. If you want a strict JSON protocol, see:
- `docs/COMMAND_PROTOCOL.md`

## Philosophy

- Truth > coherence: store receipts and provenance.
- Strong defaults: read-only behaviors; human approvals for destructive operations in external tools.
- Compression: meta-atoms emerge from repeated co-activation to reduce future context.

## License

MIT (see `LICENSE`).

## Decay + stable hashing

- Strength decays exponentially with a configurable half-life (`SYNAPTIC_DECAY_HALF_LIFE_DAYS`).
- Retrieval applies **dynamic decay** for ranking, and you can persist decay with `syn decay` (or `--decay`).
- The local hasher-embedder uses **sha256-based stable hashing** (deterministic across runs).

---

## GitHub-ready notes

- Local memory storage is **not** meant to be committed. By default Synaptic writes to `./synaptic_data/`.
  - Use `SYNAPTIC_HOME` to point storage elsewhere.
- CI is included via GitHub Actions: `.github/workflows/ci.yml`
- Console script: `syn` (after `pip install -e .`)

### Quick install (editable)
```bash
python -m pip install -e .
syn init
syn add --type idea --scope colony --tags synaptic --content "Hello memory."
syn brief "what did I just add?" --k 6 --l2 4 --meta 2
```

Repository: https://github.com/resonantlabsai/synaptic.git
