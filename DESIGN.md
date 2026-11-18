---
name: Noted
description: The stewards' notice board, one sheet per ruling.
colors:
  board: "#14214f"
  board-2: "#22336e"
  board-3: "#2c3f82"
  sheet: "#ffffff"
  ink: "#0d1324"
  mute: "#4f5a80"
  rule: "#a3b1d6"
  hair: "#d6dcec"
  wash: "#eef1f8"
  stamp-red: "#c8231d"
  amber: "#f2a900"
  amber-wash: "#fff2cc"
  car-0: "#2f5fd0"
  car-1: "#0d1324"
  car-2: "#8a5a00"
typography:
  display:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(24px, 5.5vw, 40px)"
    fontWeight: 750
    lineHeight: 1.08
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 92"
  title:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 800
    letterSpacing: "0.1em"
    fontVariation: "'wdth' 80"
  body:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.45
  body-long:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  stamp:
    fontFamily: "Archivo, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "0.06em"
    fontVariation: "'wdth' 72"
  number:
    fontFamily: "IBM Plex Mono, ui-monospace, Menlo, monospace"
    fontSize: "14px"
    fontWeight: 500
    fontFeature: "'tnum'"
rounded:
  none: "0px"
spacing:
  seam: "1px"
  chip: "3px"
  gutter: "16px"
  section: "28px"
components:
  board-row:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "7px 10px"
    height: "52px"
  car-chip:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.sheet}"
    typography: "{typography.number}"
    rounded: "{rounded.none}"
    padding: "0 5px"
  stamp-heavy:
    textColor: "{colors.stamp-red}"
    typography: "{typography.stamp}"
    rounded: "{rounded.none}"
    padding: "5px 7px 4px"
  stamp-light:
    backgroundColor: "{colors.amber-wash}"
    textColor: "{colors.ink}"
    typography: "{typography.stamp}"
    rounded: "{rounded.none}"
    padding: "5px 7px 4px"
  stamp-none:
    textColor: "{colors.mute}"
    typography: "{typography.stamp}"
    rounded: "{rounded.none}"
    padding: "5px 7px 4px"
  ruling-sheet:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "20px 16px 28px"
  choice:
    backgroundColor: "{colors.board-2}"
    textColor: "{colors.sheet}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "44px"
  choice-hover:
    backgroundColor: "{colors.board-3}"
  choice-selected:
    backgroundColor: "{colors.amber}"
    textColor: "{colors.ink}"
  replay-button:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    height: "40px"
---

# Design System: Noted

## Overview

**Creative North Star: "The Official Notice Board"**

Noted looks like the paddock's official notice board. A deep blue board holds flat white sheets, one per document, pinned in the order they were published. Each sheet carries its time and document number in a mono face, the cars involved as small black chips, a one-line subject, and a rubber verdict stamp. Opening a ruling lifts one sheet off the board and shows it at reading size.

The system is flat and dense. Sheets are separated by one pixel of board, not by shadows or gaps. Colour is a signal: stamp red means a real penalty, the amber wash means a lighter one, amber itself means something live that the reader is doing. Everything else is blue, white and ink.

This world was the direction roll's assigned card (seed:ba1a8be983988203), locked by default because the decision page was never answered. The user has not confirmed it yet. The build differs from the direction contract in three places, and the build is what this file records: stamp red darkened to #c8231d for contrast; the board's secondary text lightened to #a3b1d6; and warning, reprimand and fine stamps moved off solid amber onto an ink outline over an amber wash, so that amber stays free for live states.

**Key Characteristics:**
- Blue board, flat white sheets, one-pixel seams.
- One mono face for every number, always tabular and aligned in columns.
- Rubber stamps are the only rotated element and the heaviest type.
- Square corners everywhere.
- Amber belongs to the reader: focus, their pick, their marker.

## Colors

Three blues, white, ink and one red, with amber held back for what the reader is doing right now.

### Primary
- **Notice Board Blue** (board): the page background and the frame every sheet is pinned to. Also used as the label colour on sheets.
- **Board Seam Blue** (board-2) and **Raised Board Blue** (board-3): header and footer rules, the steward buttons at rest and on hover, the scrollbar.

### Secondary
- **Stamp Red** (stamp-red): heavy penalties only (time penalties, stop-go, grid drops, disqualification), the "harsher" comparison and harsher dots on the precedent scale, and the penalty count on the season index.
- **Live Amber** (amber): the focus ring, text selection, the reader's chosen ruling, the play button while playing, the YOU marker on the precedent scale, and the outline of the steward record line.
- **Amber Wash** (amber-wash): the fill of light stamps (warning, reprimand, fine), always with an ink outline.

### Tertiary
- **Incident Car Blue, Ink and Bronze** (car-0, car-1, car-2): the trails, dots and legend keys of the cars in the replay. Reserved for car identity.

### Neutral
- **Sheet White** (sheet): every sheet, and text on the board.
- **Stewards' Ink** (ink): text on sheets, car chips, the stewards' answer outline.
- **Sheet Grey-Blue** (mute): secondary text on sheets (6.6:1 on white) and the text of "no further action" stamps.
- **Board Rule Blue** (rule): secondary text on the board (7.4:1 on the board).
- **Hairline** (hair): dividers and borders inside a sheet, the replay track.
- **Wash** (wash): row hover, cited-quote highlight, the steward panel after the reveal.

### Named Rules
**The Live Amber Rule.** Amber marks only a live state: focus, selection, the reader's pick, the YOU marker, playback. A stamp, label or decoration is never amber.

**The Red Means Penalty Rule.** Stamp red appears only where a penalty is heavy or harsher. Incident cars never use it.

## Typography

**Word Font:** Archivo (variable width, with Helvetica Neue and Arial as fallbacks)
**Number Font:** IBM Plex Mono (with ui-monospace and Menlo as fallbacks)

**Character:** Archivo carries the words and narrows for headers and stamps, like printed notice text. Plex Mono carries every time, document number, car number, count and scale label, so numbers line up like a timing screen.

### Hierarchy
- **Display** (750, 24px to 40px, 1.08): event and ruling titles. Slightly narrowed (92% width).
- **Title** (800, 13px, 0.1em tracking, uppercase, 80% width): session headers on the board and field labels on a sheet.
- **Body** (400, 15px, 1.45): rows, notes and controls.
- **Body Long** (400, 16px, 1.6, up to 68ch): the stewards' decision and reasons on a ruling sheet.
- **Stamp** (800, 12px, 0.06em tracking, uppercase, 72% width): verdict stamps. The headline stamp on a ruling is 17px.
- **Number** (500, 11px to 14px, tabular): every number. Car chips use it at 600.

### Named Rules
**The One Number Face Rule.** Every number is set in Plex Mono with tabular figures, in a fixed-width column. No number appears in Archivo.

## Layout

Content sits in a single column up to 880px wide, centred on the board, with a 16px gutter. Board rows are a four-column grid: time over document number (50px), car chips (122px), subject (the rest, clamped to two lines), stamp (84px, right-aligned). Rows are at least 52px high and stack with a 1px seam. Sections are 28px apart.

Below 420px the row columns shrink to 44px, 58px, flexible and 64px, car chips stack vertically, and stamps lose their minimum width. The ruling sheet uses 16px side padding on phones and 40px from 720px up.

Each ruling sheet reads in a fixed order: title, then car chips with the meta line (session, issue time, document number), then the verdict, the stewards' text, the replay, the precedents and the source link. The meta line always sits after the title, never above it.

Without JavaScript, the steward controls and the replay are hidden and every field is shown.

## Elevation & Depth

The system is flat. Sheets sit directly on the board with no shadow; depth comes only from white on blue. Inset strokes stand in for borders where a border would shift layout: the two-pixel underline on a cited quote, the outline of "lighter" dots, the amber outline of the YOU marker and the hover underline in the session jump bar.

### Named Rules
**The Pinned Flat Rule.** Nothing casts a shadow. A sheet is separated from the next by one pixel of board.

## Shapes

Every corner is square (0px): sheets, rows, chips, stamps, buttons and the replay stage. The one round shape is the coloured dot in the replay legend, which matches the round car markers on the track. Stamps are the only rotated shapes, tilted between -0.6 and -2.5 degrees, with the angle varying from row to row like hand-pressed rubber.

## Components

### Board Row
A white sheet strip, one per document. Time and DOC number in mono at the left, car chips, a two-line subject, the stamp at the right. Hover turns the sheet to the wash colour. The whole row is the link.

### Car Chip
A small ink block with white mono text: the car number in a lighter blue, then the three-letter driver code. Square, 20px high.

### Stamps
- **Shape:** square, 2px outline in the text colour, condensed uppercase, rotated slightly.
- **Heavy:** stamp red text and outline on the sheet.
- **Light (warning, reprimand, fine):** ink text and ink outline over the amber wash.
- **None (no further action, approved):** grey-blue text with a rule-blue outline.
- **Verdict stamp:** 17px with a 3px outline. On reveal it lands in 420ms from a larger, blurred, steeper tilt. With reduced motion it simply appears.

### Steward Buttons
- **Shape:** square, at least 44px high, condensed bold label, in an auto-filling grid of 86px minimum.
- **At rest:** board-2 fill, board-3 outline, white text. Hover goes to board-3.
- **Selected:** amber fill and outline, ink text.
- **After the reveal:** unpicked buttons turn white with grey text; the stewards' answer gets a 2px ink outline and a small ink "Stewards" tag on its top edge.
- **Skip link:** an underlined text button in rule blue.

### Ruling Sheet
A full white sheet on the board. Field labels in the Title style, in board blue. Cited quotes have a wash fill, a board-blue underline and a small mono tag naming the reason. Machine-made labels and rankings carry a short grey note saying so.

### Replay
A white stage with a hairline border. The track is a quiet hairline stroke; incident cars use the three reserved car colours, with a legend of round keys. Controls are square white buttons with a hairline outline that darkens to ink on hover; the play button turns amber while playing. The scrubber uses the board blue as its accent.

### Precedent Scale
One fixed horizontal penalty scale with dashed ticks and mono labels. Earlier rulings are small numbered blocks: ink for the same penalty, red for harsher, white with an ink outline for lighter. This ruling is a vertical ink line marked THIS; the reader's pick is a white block with an amber outline marked YOU. Below it, precedent rows list place, subject, stamp and a same, harsher or lighter word.

### Navigation
The top bar holds the NOTED wordmark (heavy, condensed, wide-tracked uppercase) followed by "Stewards' board" in rule blue, then breadcrumbs. The session jump bar is a row of condensed uppercase links with mono counts; hover turns them white with a white underline.

## Do's and Don'ts

### Do:
- **Do** keep amber (#f2a900) for focus, selection, the reader's pick, playback and the YOU marker.
- **Do** give warning, reprimand and fine stamps an ink outline on the amber wash (#fff2cc).
- **Do** set every number in IBM Plex Mono with tabular figures, in aligned columns.
- **Do** separate sheets with 1px of board, and keep every corner square.
- **Do** put the meta line after the title.
- **Do** show every field when JavaScript is off, and hide the steward controls and replay.
- **Do** say plainly when a label or ranking was made by a machine.

### Don't:
- **Don't** use stamp red (#c8231d) for anything but heavy or harsher penalties; incident cars never take it.
- **Don't** fill a stamp with solid amber.
- **Don't** rotate anything except stamps.
- **Don't** add shadows, rounded corners or paper texture to sheets.
- **Don't** put a kicker or meta line above a title.
