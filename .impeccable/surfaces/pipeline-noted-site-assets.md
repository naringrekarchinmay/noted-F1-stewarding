---
version: 1
slug: "pipeline-noted-site-assets"
primary_target: "pipeline/noted/site_assets"
related_targets: []
---

THESIS
Each weekend is the stewards' notice board: documents pinned in the order published, each with its number, time and a verdict stamp. Chosen by default (the roll's assigned card) because the user did not answer the decision page and asked to keep going.

OWN-WORLD
The paddock's official notice board. Deep blue board (#14214f), flat white sheets (#fff), ink #0d1324, stamp red #e0312b for penalties, amber #f2a900 for warnings and reprimands, rule blue #8fa0c8 for secondary text on the board. Archivo (variable width, condensed for stamps and headers) for words; IBM Plex Mono tabular for every number. Flat: no paper texture, no shadows on sheets; sheets are separated by 1px of board.

STORY
Board (seasons and events) -> event board (sessions, Race first, one sheet-row per document) -> ruling sheet (verdict hidden in steward mode, the reader rules, then the stamp, decision, reason with cited quotes, and the precedents on one penalty scale) -> precedent links to other sheets.

FIRST VIEWPORT
Phone: blue board, NOTED wordmark with STEWARDS' BOARD, the race name, then session headers and white rows: time and DOC number in mono, car chips (number + code), one-line subject, rotated rubber stamp at right. Ruling page: white sheet on the board with meta, title, car chips, then the steward buttons.

FORM
seed:ba1a8be983988203. Raised lines: one tabular face for every number in strict columns; precedents on one fixed penalty scale; replay track as a quiet fixed layer, incident cars in reserved colours; one accent (amber outline) owns every live state: selected, focus and your own ruling.

FINISH
Stamps are the only rotated element and the only heavy type. Focus rings, selection, scrollbars and range inputs themed from the palette. Works without JS (everything visible). Reduced motion: the stamp's landing animation on reveal becomes an instant swap. Contrast AA on board and sheet.
