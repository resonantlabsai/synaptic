from __future__ import annotations
from typing import Any, Dict, List, Tuple

from .models import Retrieved
from .util import safe_truncate

def format_atom_line(r: Retrieved) -> str:
    row = r.row
    typ = row.get("type", "?")
    w = float(row.get("w") or 0.0)
    uses = int(row.get("uses") or 0)
    sid = row.get("atom_id")
    summary = (row.get("summary") or "").strip()
    summary = safe_truncate(summary.replace("\n", " "), 220)
    why = ", ".join(r.reasons[:3]) if r.reasons else ""
    return f"- [{sid}] ({typ}, w={w:.2f}, uses={uses}) {summary}" + (f"  _({why})_" if why else "")

def build_brief(query: str, seeds: List[Retrieved], l2_suggestions: List[Dict[str, Any]] | None = None,
                meta: List[Dict[str, Any]] | None = None) -> str:
    lines: List[str] = []
    lines.append(f"## Synaptic memory brief")
    lines.append(f"**Query:** {query}")
    lines.append("")
    lines.append("### L1: Most relevant atoms")
    for r in seeds:
        lines.append(format_atom_line(r))
    if l2_suggestions:
        lines.append("")
        lines.append("### L2: Adjacent suggestions")
        for s in l2_suggestions:
            lines.append(f"- [{s['atom_id']}] score={s['score']:.2f} reasons={','.join(s.get('reasons',[]))}")
    if meta:
        lines.append("")
        lines.append("### L2: Pattern candidates (meta-atoms)")
        for m in meta:
            members = ", ".join(m.get("members", []))
            lines.append(f"- {m.get('title','Pattern')} score={m.get('score',0):.2f} members=[{members}]")
    return "\n".join(lines) + "\n"
