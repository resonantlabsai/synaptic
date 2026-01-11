# Command Protocol (optional)

If you build a local browser-side listener + local daemon, you can expose Synaptic via a strict JSON envelope.

Recommended format (sent by *you*, executed locally):

```
/cmd
```json
{
  "id": "2026-01-11T04:10:00Z-0001",
  "op": "synaptic.brief",
  "args": {
    "query": "what are our safety constraints?",
    "k": 12,
    "l2": 8
  }
}
```

Return format (local tool → pasted back into chat):

```json
{
  "id": "...",
  "ok": true,
  "result": {
    "brief": "...",
    "atom_ids": ["atom_..."],
    "l2_suggestions": [{"atom_id":"...", "score":0.42, "reasons":["coact","sim"]}],
    "meta_candidates": [{"title":"...", "members":["..."], "score":0.31}]
  }
}
```

**Safety note:** keep writes/exec behind human approval in your local tool.
