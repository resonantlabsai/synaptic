from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from synaptic.config import get_config
from synaptic.store import SynapticStore
from synaptic.retrieve import Retriever

def main():
    cfg = get_config()
    st = SynapticStore(cfg)
    st.init()

    st.add_atom(
        type="principle",
        scope=["colony"],
        tags=["safety"],
        entities=["Synaptic"],
        content="Truth > coherence; store receipts and provenance.",
        summary="Truth > coherence; store receipts and provenance."
    )
    st.add_atom(
        type="idea",
        scope=["colony"],
        tags=["memory","l2"],
        entities=["Synaptic"],
        content="Use L2 neighbor expansion to surface bridging ideas and form meta-atoms.",
        summary="L2 neighbor expansion surfaces bridging ideas; meta-atoms compress memory."
    )

    r = Retriever(st, cfg)

    # Query should match via FTS/LIKE and also succeed under embedding similarity.
    seeds = r.l1_search("l2 neighbor expansion meta atoms", k=5)
    assert seeds, "Expected some retrieval results"

    st.close()
    print("OK")

if __name__ == "__main__":
    main()
