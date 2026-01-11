from __future__ import annotations

"""A minimal 'agent memory' loop without any model calls.

This shows how an agent could:
1) store an observation,
2) retrieve relevant context for a new query,
3) optionally strengthen what it used (CLI does this automatically; you can also do it programmatically).

Run:
  python examples/agent_memory_minimal.py
"""

import os
from pathlib import Path

from synaptic.config import get_config
from synaptic.store import SynapticStore
from synaptic.retrieve import Retriever

def main():
    os.environ.setdefault("SYNAPTIC_HOME", str(Path("./synaptic_data_examples").resolve()))
    cfg = get_config()

    st = SynapticStore(cfg)
    st.init()

    st.add_atom(
        type="observation",
        scope=["agent"],
        tags=["user_pref", "workflow"],
        entities=["User"],
        summary="User prefers small shippable chunks and preflighted patches.",
        content=(
            "When making changes, ship patch zips, run compileall + smoke, "
            "and keep turns small to avoid timeouts."
        ),
        pinned=True,
    )

    st.add_atom(
        type="principle",
        scope=["agent"],
        tags=["truth", "integrity"],
        entities=["Synaptic"],
        summary="Truth > coherence; label uncertainty.",
        content="Prefer correctness; cite sources; don't invent details when unsure."
    )

    r = Retriever(st, cfg)

    query = "How should I structure my work to avoid regressions?"
    hits = r.l1_search(query, k=5)

    print(f"Query: {query}")
    print("Memory context:")
    for h in hits:
        print(f"- {h.score:.3f} :: {h.row.get('summary','')}")

    st.close()

if __name__ == "__main__":
    main()
