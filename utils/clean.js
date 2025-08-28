// Utility functions for Telugu text cleaning

function stripHtml(input) {
  // Remove HTML tags
  return input.replace(/<[^>]*>/g, "");
}

function normalizeUnicode(input) {
  // NFC normalization for consistent Unicode form
  try {
    return input.normalize("NFC");
  } catch (_) {
    return input;
  }
}

function keepTeluguOnly(input) {
  // Keep Telugu block characters, whitespace, common punctuation, and ZWJ/ZWNJ
  // Telugu Unicode block: U+0C00–U+0C7F
  // Also retain spaces/newlines, digits, and extended punctuation used in text
  // Allowed punctuation: . , ! ? ; : ( ) " ' - — … ₹ (and en dash)
  const allowed = /[^\u0C00-\u0C7F0-9\s\.,!\?;:\(\)\'"\-\u2013\u2014\u2026\u20B9\u200C\u200D]/g;
  return input.replace(allowed, "");
}

function removeDuplicateLines(input) {
  const seen = new Set();
  const lines = input.split(/\r?\n/);
  const out = [];
  for (let line of lines) {
    const trimmed = line.trim();
    if (!seen.has(trimmed)) {
      seen.add(trimmed);
      out.push(trimmed);
    }
  }
  return out.join("\n");
}

function trimWhitespace(input) {
  // Trim each line and collapse trailing/leading whitespace
  return input
    .split(/\r?\n/)
    .map((l) => l.trim())
    .join("\n")
    .trim();
}

function cleanText(raw) {
  if (typeof raw !== "string") return "";
  let s = raw;
  s = stripHtml(s);
  s = normalizeUnicode(s);
  s = keepTeluguOnly(s);
  s = removeDuplicateLines(s);
  s = trimWhitespace(s);
  return s;
}

module.exports = { cleanText };
