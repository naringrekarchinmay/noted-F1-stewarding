"""The current season's rules: article references in a ruling, and the rulebooks they point to.

A 2026 ruling cites two books by article:
  - the FIA 2026 F1 Regulations, Section B [Sporting]: "Article B1.8.5", "Articles B8.2.2a read with B8.2.3";
  - Appendix L of the International Sporting Code: "Appendix L, Chapter IV, Article 2 d)".
Earlier seasons used other rulebooks with other numbering, so only 2026 rulings are linked.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SEASON = 2026
BOOKS = {
    "sporting": {
        "title": "FIA 2026 F1 Regulations – Section B [Sporting]",
        "short": "Sporting Regulations",
        "issue": "Issue 9, 1 October 2026",
        "url": "https://www.fia.com/system/files/documents/fia_2026_f1_regulations_-_section_b_sporting_-_iss_09_-_2026-10-01.pdf",
        "file": "fia_2026_f1_regulations_-_section_b_sporting_-_iss_09_-_2026-10-01.pdf",
    },
    "appendix_l": {
        "title": "International Sporting Code, Appendix L – 2026",
        "short": "Appendix L",
        "issue": "Published 23 June 2026",
        "url": "https://www.fia.com/system/files/documents/appendix_l_2026_publie_le_24_juin_2026.pdf",
        "file": "appendix_l_2026_publie_le_24_juin_2026.pdf",
    },
}


@dataclass(frozen=True)
class Ref:
    start: int  # span in the text that was searched
    end: int
    book: str  # key of BOOKS
    article: str  # "B1.8.5" (letter suffix dropped: "B8.2.2a" cites B8.2.2), or "IV.2" for Appendix L
    point: str = ""  # the sub-point the ruling names, "a" or "d", for display only


# A Section B article number; the B prefix keeps it apart from the Sporting Code's own "Article 12.2.1.i".
_SPORTING = re.compile(r"\bB(\d+(?:\.\d+)+)([a-z])?(?!\w)")
_APPENDIX_L = re.compile(
    r"Appendix\s+L\s*,?\s*Chapter\s+([IVX]+)\s*,?\s*Articles?\s+(\d+)(?:\s*\.?\s*([a-z])\)?)?(?![\w])", re.I)


def references(text: str) -> list[Ref]:
    """Every Section B and Appendix L article cited in the text, in order."""
    refs = [Ref(m.start(), m.end(), "sporting", f"B{m.group(1)}", m.group(2) or "") for m in _SPORTING.finditer(text)]
    refs += [Ref(m.start(), m.end(), "appendix_l", f"{m.group(1).upper()}.{m.group(2)}", (m.group(3) or "").lower())
             for m in _APPENDIX_L.finditer(text)]
    return sorted(refs, key=lambda r: r.start)
