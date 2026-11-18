-- Noted: friends' steward-mode votes. One vote per voter per ruling; a later vote replaces it.
-- Apply with: npx wrangler d1 execute noted-votes --remote --file=schema.sql
CREATE TABLE IF NOT EXISTS votes (
  ruling INTEGER NOT NULL,   -- ruling id, as in r/<id>.html
  voter  TEXT    NOT NULL,   -- random id the browser makes, [A-Za-z0-9_-]{8,64}
  choice TEXT    NOT NULL,   -- one of the ten steward-mode choices
  at     TEXT    NOT NULL,   -- ISO 8601 UTC time of the (latest) vote
  PRIMARY KEY (ruling, voter)
);
