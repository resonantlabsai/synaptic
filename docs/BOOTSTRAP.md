# Bootstrap

```bash
python -m synaptic.cli init
python -m synaptic.cli add --type idea --scope colony --tags synaptic \
  --content "Store thoughts as atoms; retrieve via briefs; strengthen on use; prune under budget."
python -m synaptic.cli brief "what is synaptic?" --k 8 --l2 6 --meta 2 --decay
python scripts/smoke.py
```

Environment:
- `SYNAPTIC_HOME=/path/to/storage`
- `SYNAPTIC_EMBED_DIM=256`
- `SYNAPTIC_DECAY_HALF_LIFE_DAYS=30` (default: 30)
- `SYNAPTIC_DECAY_ON_RETRIEVAL=1` (dynamic decay used for ranking; default: 1)
