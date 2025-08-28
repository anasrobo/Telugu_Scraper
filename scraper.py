# #!/usr/bin/env python3
# # -*- coding: utf-8 -*-
# """
# General Telugu text scraper.

# Usage:
#   python scraper.py <url> [--follow] [--limit N]

# - Input: Public webpage URL (e.g., Sakshi, Eenadu, Andhra Jyothi, Telugu Wikipedia)
# - Scraper: Fetch via requests, extract text from <p> and <article> tags.
#            If --follow is provided and the URL is a listing/section page, it will also follow links
#            from the same domain (up to --limit pages) and extract from those as well.
# - Cleaning:
#   * Preserve Telugu script (\u0C00–\u0C7F), digits (0–9), and extended punctuation: . , ! ? ; : ( ) " ' - — … ₹ (incl. en dash)
#   * Remove English letters, random symbols, and junk
#   * Deduplicate lines
#   * Keep only lines with > 20 characters
# - Output: Save cleaned lines to auto-incremented raw_telugu_N.txt (UTF-8) and print number of lines saved.
# """

# import argparse
# import re
# import sys
# from collections import OrderedDict
# import os
# from urllib.parse import urljoin, urlparse

# import requests
# from bs4 import BeautifulSoup

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/124.0.0.0 Safari/537.36"
#     ),
#     "Accept-Language": "te,en;q=0.8,*;q=0.5",
# }

# TELUGU_RANGE = "\u0C00-\u0C7F"
# # Allow Telugu letters, ASCII letters (to keep entities like AP, COVID-19, ETV, names), digits, whitespace, and extended punctuation
# # Allowed punctuation: . , ! ? ; : ( ) " ' - / — … ₹ (and en dash)
# CLEAN_RE = re.compile(fr"[^ {TELUGU_RANGE}0-9A-Za-z\s\.,!\?;:\(\)\"'\-\/\u2013\u2014\u2026\u20B9]+")
# MULTISPACE_RE = re.compile(r"\s+")
# # UI words removal regex (needs to be module-level; used in filter_telugu and main)
# ui_words_re = re.compile(r"\b(click|download|pdf|live\s*updates?)\b", re.I)


# def fetch(url: str) -> str:
#     resp = requests.get(url, headers=HEADERS, timeout=20)
#     resp.raise_for_status()
#     # Many Telugu sites are UTF-8; requests will decode via apparent encoding
#     resp.encoding = resp.encoding or "utf-8"
#     return resp.text


# def extract_paragraphs(html: str) -> list[str]:
#     soup = BeautifulSoup(html, "html.parser")
#     texts: list[str] = []

#     # Prefer <article> content paragraphs
#     for art in soup.find_all("article"):
#         for p in art.find_all("p"):
#             t = p.get_text(separator=" ", strip=True)
#             if t:
#                 texts.append(t)

#     # Fallback to all <p> tags if needed
#     if not texts:
#         for p in soup.find_all("p"):
#             t = p.get_text(separator=" ", strip=True)
#             if t:
#                 texts.append(t)

#     return texts


# def extract_headline(html: str) -> str:
#     soup = BeautifulSoup(html, "html.parser")
#     h = (soup.find("h1") or soup.find("h2"))
#     if not h:
#         return ""
#     t = h.get_text(separator=" ", strip=True)
#     return MULTISPACE_RE.sub(" ", t).strip()


# def clean_line(line: str) -> str:
#     # Remove everything outside Telugu block and allowed punctuation/space
#     line = CLEAN_RE.sub(" ", line)
#     # Normalize whitespace
#     line = MULTISPACE_RE.sub(" ", line).strip()
#     return line


# def filter_telugu(lines: list[str]) -> list[str]:
#     out: list[str] = []
#     seen = OrderedDict()
#     telugu_char = re.compile(fr"[{TELUGU_RANGE}]")
#     junk_patterns = [
#         re.compile(r"డౌన్\s*లోడ్", re.I),
#         re.compile(r"డౌన్‌లోడ్", re.I),
#         re.compile(r"ఇక్కడ\s*చూడండి", re.I),
#         re.compile(r"క్లిక్", re.I),
#         re.compile(r"click", re.I),
#         re.compile(r"pdf", re.I),
#     ]
#     address_re = re.compile(r"\b\d{1,4}(?:[-\/]\d{1,4}){1,4}\b(?:[^\n]*?\b\d{3}\s?-?\s?\d{3}\b)?")
#     important_note_re = re.compile(r"(పరీక్ష|సూచనలు|ప్రకటన|అధికారిక|హెచ్చరిక|జాగ్రత్త|advisory|notice|guidelines)", re.I)

#     def wrap_addresses(t: str) -> str:
#         return address_re.sub(lambda m: f"[ADDRESS] {m.group(0)} [/ADDRESS]", t)

#     def mostly_english(t: str) -> bool:
#         letters = len(re.sub(r"[^A-Za-z]", "", t))
#         return (letters > 0) and (letters / max(len(t), 1) > 0.6)

#     def is_date_or_number(t: str) -> bool:
#         if re.fullmatch(r"\d{1,4}", t):
#             return True
#         if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", t):
#             return True
#         if re.fullmatch(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", t):
#             return True
#         return False

#     for raw in lines:
#         cl = clean_line(raw)
#         if not cl:
#             continue
#         # Remove UI junk words within the line
#         cl = ui_words_re.sub("", cl)
#         cl = MULTISPACE_RE.sub(" ", cl).strip()
#         if not cl:
#             continue
#         # filter junk
#         if any(p.search(cl) for p in junk_patterns):
#             continue
#         # గమనిక handling: drop unless contains important keywords
#         if re.match(r"^గమనిక[\s:,-]", cl):
#             if not important_note_re.search(cl):
#                 continue
#         # Wrap address-like substrings
#         cl = wrap_addresses(cl)
#         # Skip mostly English lines unless they are addresses
#         if mostly_english(cl) and "[ADDRESS]" not in cl:
#             continue
#         # Keep lines with Telugu and >= 10 chars, or short numeric/date lines
#         if (len(cl) >= 10 and telugu_char.search(cl)) or (len(cl) < 10 and is_date_or_number(cl)):
#             if cl not in seen:
#                 seen[cl] = True
#     out = list(seen.keys())
#     return out


# def apply_post_rules(cleaned_lines: list[str]) -> list[str]:
#     """
#     Apply post-scrape, post-clean rules on already cleaned lines.

#     Rules:
#       - Exclude lines containing '(ఫొటోలు)'
#       - Exclude lines starting with ':' (stray fake headlines)
#       - Exclude lines containing any of: 'బర్త్ డే', 'థాయిలాండ్', 'సింధు', 'దర్శకులతో'
#       - Structure: first remaining line -> HEADLINE; others -> BODY

#     Returns the filtered list of lines (without labels). Labeling is done in main.
#     """
#     side_story_terms = ["బర్త్ డే", "థాయిలాండ్", "సింధు", "దర్శకులతో"]

#     kept: list[str] = []
#     for line in cleaned_lines:
#         if not line:
#             continue
#         if "(ఫొటోలు)" in line:
#             continue
#         if line.startswith(":"):
#             continue
#         if any(term in line for term in side_story_terms):
#             continue
#         kept.append(line)
#     return kept


# def is_same_domain(seed: str, candidate: str) -> bool:
#     a, b = urlparse(seed), urlparse(candidate)
#     return a.netloc.lower() == b.netloc.lower()


# def collect_links(seed_url: str, html: str, limit: int = 20) -> list[str]:
#     soup = BeautifulSoup(html, "html.parser")
#     found: list[str] = []
#     seen = set()

#     for a in soup.find_all("a", href=True):
#         href = a["href"].strip()
#         full = urljoin(seed_url, href)
#         if full in seen:
#             continue
#         seen.add(full)
#         # Stay within the same domain
#         if not is_same_domain(seed_url, full):
#             continue
#         # Heuristic: likely article pages (not strict). Keep most links; caller limits count.
#         found.append(full)
#         if len(found) >= limit:
#             break
#     return found


# def scrape_url(url: str) -> list[str]:
#     try:
#         html = fetch(url)
#     except Exception as e:
#         print(f"[warn] Failed to fetch {url}: {e}", file=sys.stderr)
#         return []
#     paras = extract_paragraphs(html)
#     return paras


# def next_output_path(base_dir: str = ".") -> str:
#     """Find next raw_telugu_N.txt in base_dir without overwriting old files."""
#     existing = [f for f in os.listdir(base_dir) if f.startswith("raw_telugu_") and f.endswith(".txt")]
#     nums = []
#     for f in existing:
#         try:
#             n = int(f[len("raw_telugu_"):-4])
#             nums.append(n)
#         except Exception:
#             pass
#     n = max(nums) + 1 if nums else 1
#     return os.path.join(base_dir, f"raw_telugu_{n}.txt")


# def main():
#     parser = argparse.ArgumentParser(description="General Telugu text scraper")
#     parser.add_argument("url", help="Seed/page URL to scrape")
#     parser.add_argument("--follow", action="store_true", help="Also follow links from the seed page (same domain)")
#     parser.add_argument("--limit", type=int, default=20, help="Max pages to follow when --follow is set (default: 20)")
#     args = parser.parse_args()

#     seed_url = args.url

#     # 1) Scrape the seed page
#     all_paras: list[str] = []
#     seed_html = None
#     try:
#         seed_html = fetch(seed_url)
#     except Exception as e:
#         print(f"[error] Failed to fetch seed: {e}", file=sys.stderr)
#         sys.exit(1)

#     # Extract paragraphs (we will derive headline from cleaned text per post-rules)
#     all_paras.extend(extract_paragraphs(seed_html))

#     # 2) Optionally follow internal links (listing/section pages)
#     if args.follow:
#         links = collect_links(seed_url, seed_html, limit=args.limit)
#         for i, link in enumerate(links, 1):
#             print(f"[info] ({i}/{len(links)}) Following: {link}")
#             all_paras.extend(scrape_url(link))

#     # 3) Clean, deduplicate, filter
#     cleaned_lines = filter_telugu(all_paras)
#     # 3b) Apply post-cleaning rules provided by user
#     post_lines = apply_post_rules(cleaned_lines)

#     # 4) Save (cap to 5000 lines)
#     post_lines = post_lines[:5000]
#     final_lines: list[str] = []
#     if post_lines:
#         # First line is the HEADLINE per rules
#         final_lines.append(f"HEADLINE: {post_lines[0]}")
#         # Article body section with preserved paragraph lines
#         final_lines.append("ARTICLE BODY:")
#         final_lines.extend(post_lines[1:])

#     out_path = next_output_path()
#     with open(out_path, "w", encoding="utf-8") as f:
#         for line in final_lines:
#             f.write(line + "\n")

#     print(f"Saved {len(final_lines)} lines (incl. headline) to {out_path}")


# if __name__ == "__main__":
#     main()




#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General Telugu text scraper + cleaner.

Usage:
  python scraper.py <url> [--follow] [--limit N]

Scraper:
  - Fetches page with requests.
  - Extracts text from <p> and <article> tags.
  - Optionally follows links from same domain.

Cleaning:
  - Preserves Telugu text, digits, and important punctuation.
  - Removes English UI junk (click, download, pdf, live updates).
  - Deduplicates lines.
  - Preserves addresses (wrapped in [ADDRESS] ... [/ADDRESS]).
  - Preserves numbers exactly as written.
  - Removes side stories, photo markers, irrelevant short lines.

Output:
  - Saved to raw_telugu_N.txt
  - Format:
      HEADLINE: <headline>
      ARTICLE BODY:
      <paragraphs...>
"""

# import argparse
# import re
# import sys
# from collections import OrderedDict
# import os
# from urllib.parse import urljoin, urlparse

# import requests
# from bs4 import BeautifulSoup

# HEADERS = {
#     "User-Agent": (
#         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#         "AppleWebKit/537.36 (KHTML, like Gecko) "
#         "Chrome/124.0.0.0 Safari/537.36"
#     ),
#     "Accept-Language": "te,en;q=0.8,*;q=0.5",
# }

# TELUGU_RANGE = "\u0C00-\u0C7F"
# # Regex to allow Telugu, digits, ASCII letters (for AP, COVID-19, etc.), punctuation
# CLEAN_RE = re.compile(fr"[^ {TELUGU_RANGE}0-9A-Za-z\s\.,!\?;:\(\)\"'\-\/\u2013\u2014\u2026\u20B9]+")
# MULTISPACE_RE = re.compile(r"\s+")
# ui_words_re = re.compile(r"\b(click|download|pdf|live\s*updates?)\b", re.I)


# def fetch(url: str) -> str:
#     resp = requests.get(url, headers=HEADERS, timeout=20)
#     resp.raise_for_status()
#     resp.encoding = resp.encoding or "utf-8"
#     return resp.text


# def extract_paragraphs(html: str) -> list[str]:
#     soup = BeautifulSoup(html, "html.parser")
#     texts: list[str] = []

#     # Prefer <article>
#     for art in soup.find_all("article"):
#         for p in art.find_all("p"):
#             t = p.get_text(separator=" ", strip=True)
#             if t:
#                 texts.append(t)

#     # Fallback to <p>
#     if not texts:
#         for p in soup.find_all("p"):
#             t = p.get_text(separator=" ", strip=True)
#             if t:
#                 texts.append(t)

#     return texts


# def clean_line(line: str) -> str:
#     line = CLEAN_RE.sub(" ", line)
#     line = MULTISPACE_RE.sub(" ", line).strip()
#     return line


# def filter_telugu(lines: list[str]) -> list[str]:
#     out: list[str] = []
#     seen = OrderedDict()
#     telugu_char = re.compile(fr"[{TELUGU_RANGE}]")
#     # Regex for junk
#     junk_patterns = [
#         re.compile(r"డౌన్\s*లోడ్", re.I),
#         re.compile(r"డౌన్‌లోడ్", re.I),
#         re.compile(r"ఇక్కడ\s*చూడండి", re.I),
#         re.compile(r"క్లిక్", re.I),
#         re.compile(r"click", re.I),
#         re.compile(r"pdf", re.I),
#     ]
#     # Address pattern
#     address_re = re.compile(r"\b\d{1,4}(?:[-\/]\d{1,4}){1,4}\b(?:[^\n]*?\b\d{3}\s?-?\s?\d{3}\b)?")
#     # Important notes
#     important_note_re = re.compile(r"(పరీక్ష|సూచనలు|ప్రకటన|అధికారిక|హెచ్చరిక|జాగ్రత్త|advisory|notice|guidelines)", re.I)

#     def wrap_addresses(t: str) -> str:
#         return address_re.sub(lambda m: f"[ADDRESS] {m.group(0)} [/ADDRESS]", t)

#     def mostly_english(t: str) -> bool:
#         letters = len(re.sub(r"[^A-Za-z]", "", t))
#         return (letters > 0) and (letters / max(len(t), 1) > 0.6)

#     def is_date_or_number(t: str) -> bool:
#         if re.fullmatch(r"\d{1,4}", t):
#             return True
#         if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", t):
#             return True
#         if re.fullmatch(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", t):
#             return True
#         return False

#     for raw in lines:
#         cl = clean_line(raw)
#         if not cl:
#             continue
#         # Remove UI junk
#         cl = ui_words_re.sub("", cl)
#         cl = MULTISPACE_RE.sub(" ", cl).strip()
#         if not cl:
#             continue
#         if any(p.search(cl) for p in junk_patterns):
#             continue
#         # గమనిక handling
#         if re.match(r"^గమనిక[\s:,-]", cl):
#             if not important_note_re.search(cl):
#                 continue
#         # Wrap addresses
#         cl = wrap_addresses(cl)
#         # Skip mostly English (unless address)
#         if mostly_english(cl) and "[ADDRESS]" not in cl:
#             continue
#         # Keep lines with Telugu or important numbers
#         if (len(cl) >= 10 and telugu_char.search(cl)) or (len(cl) < 10 and is_date_or_number(cl)):
#             if cl not in seen:
#                 seen[cl] = True
#     return list(seen.keys())


# def apply_post_rules(cleaned_lines: list[str]) -> list[str]:
#     """
#     Apply post-clean rules:
#       - Remove (ఫొటోలు)
#       - Remove stray ':'
#       - Remove unrelated side stories
#       - First line -> HEADLINE, rest -> BODY
#     """
#     side_story_terms = ["బర్త్ డే", "థాయిలాండ్", "సింధు", "దర్శకులతో"]

#     kept: list[str] = []
#     for line in cleaned_lines:
#         if not line:
#             continue
#         if "(ఫొటోలు)" in line:
#             continue
#         if line.startswith(":"):
#             continue
#         if any(term in line for term in side_story_terms):
#             continue
#         kept.append(line)
#     return kept


# def is_same_domain(seed: str, candidate: str) -> bool:
#     a, b = urlparse(seed), urlparse(candidate)
#     return a.netloc.lower() == b.netloc.lower()


# def collect_links(seed_url: str, html: str, limit: int = 20) -> list[str]:
#     soup = BeautifulSoup(html, "html.parser")
#     found: list[str] = []
#     seen = set()

#     for a in soup.find_all("a", href=True):
#         href = a["href"].strip()
#         full = urljoin(seed_url, href)
#         if full in seen:
#             continue
#         seen.add(full)
#         if not is_same_domain(seed_url, full):
#             continue
#         found.append(full)
#         if len(found) >= limit:
#             break
#     return found


# def scrape_url(url: str) -> list[str]:
#     try:
#         html = fetch(url)
#     except Exception as e:
#         print(f"[warn] Failed to fetch {url}: {e}", file=sys.stderr)
#         return []
#     return extract_paragraphs(html)


# def next_output_path(base_dir: str = ".") -> str:
#     existing = [f for f in os.listdir(base_dir) if f.startswith("raw_telugu_") and f.endswith(".txt")]
#     nums = []
#     for f in existing:
#         try:
#             n = int(f[len("raw_telugu_"):-4])
#             nums.append(n)
#         except Exception:
#             pass
#     n = max(nums) + 1 if nums else 1
#     return os.path.join(base_dir, f"raw_telugu_{n}.txt")


# def main():
#     parser = argparse.ArgumentParser(description="General Telugu text scraper")
#     parser.add_argument("url", help="Seed/page URL to scrape")
#     parser.add_argument("--follow", action="store_true", help="Also follow links from the seed page (same domain)")
#     parser.add_argument("--limit", type=int, default=20, help="Max pages to follow when --follow is set (default: 20)")
#     args = parser.parse_args()

#     seed_url = args.url

#     all_paras: list[str] = []
#     try:
#         seed_html = fetch(seed_url)
#     except Exception as e:
#         print(f"[error] Failed to fetch seed: {e}", file=sys.stderr)
#         sys.exit(1)

#     all_paras.extend(extract_paragraphs(seed_html))

#     if args.follow:
#         links = collect_links(seed_url, seed_html, limit=args.limit)
#         for i, link in enumerate(links, 1):
#             print(f"[info] ({i}/{len(links)}) Following: {link}")
#             all_paras.extend(scrape_url(link))

#     cleaned_lines = filter_telugu(all_paras)
#     post_lines = apply_post_rules(cleaned_lines)

#     post_lines = post_lines[:5000]
#     final_lines: list[str] = []
#     if post_lines:
#         final_lines.append(f"HEADLINE: {post_lines[0]}")
#         final_lines.append("ARTICLE BODY:")
#         final_lines.extend(post_lines[1:])

#     out_path = next_output_path()
#     with open(out_path, "w", encoding="utf-8") as f:
#         for line in final_lines:
#             f.write(line + "\n")

#     print(f"Saved {len(final_lines)} lines (incl. headline) to {out_path}")


# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
General Telugu text scraper (cleaned version rules applied).

Changes:
  * Preserves Telugu, numbers, addresses.
  * Wraps addresses in [ADDRESS] ... [/ADDRESS].
  * Removes junk UI words, duplicates, side stories.
  * Ensures no output starts with stray ':' — filters them out.
  * Disclaimers starting with "గమనిక" are excluded unless official/notice keywords present.
  * Output format: HEADLINE + ARTICLE BODY only.

Usage:
  python scraper.py <url> [--follow] [--limit N]
"""

import argparse
import re
import sys
from collections import OrderedDict
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "te,en;q=0.8,*;q=0.5",
}

TELUGU_RANGE = "\u0C00-\u0C7F"
# Allow Telugu letters, ASCII letters (entities like AP, COVID-19, etc.), digits, whitespace, and punctuation
CLEAN_RE = re.compile(fr"[^ {TELUGU_RANGE}0-9A-Za-z\s\.,!\?;:\(\)\"'\-\/\u2013\u2014\u2026\u20B9]+")
MULTISPACE_RE = re.compile(r"\s+")
ui_words_re = re.compile(r"\b(click|download|pdf|live\s*updates?)\b", re.I)


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = resp.encoding or "utf-8"
    return resp.text


def extract_paragraphs(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    texts: list[str] = []
    for art in soup.find_all("article"):
        for p in art.find_all("p"):
            t = p.get_text(separator=" ", strip=True)
            if t:
                texts.append(t)
    if not texts:
        for p in soup.find_all("p"):
            t = p.get_text(separator=" ", strip=True)
            if t:
                texts.append(t)
    return texts


def clean_line(line: str) -> str:
    line = CLEAN_RE.sub(" ", line)
    line = MULTISPACE_RE.sub(" ", line).strip()
    return line


def filter_telugu(lines: list[str]) -> list[str]:
    out: list[str] = []
    seen = OrderedDict()
    telugu_char = re.compile(fr"[{TELUGU_RANGE}]")
    junk_patterns = [
        re.compile(r"డౌన్\s*లోడ్", re.I),
        re.compile(r"డౌన్‌లోడ్", re.I),
        re.compile(r"ఇక్కడ\s*చూడండి", re.I),
        re.compile(r"క్లిక్", re.I),
        re.compile(r"click", re.I),
        re.compile(r"pdf", re.I),
    ]
    address_re = re.compile(r"\b\d{1,4}(?:[-\/]\d{1,4}){1,4}\b(?:[^\n]*?\b\d{3}\s?-?\s?\d{3}\b)?")
    important_note_re = re.compile(r"(పరీక్ష|సూచనలు|ప్రకటన|అధికారిక|హెచ్చరిక|జాగ్రత్త|notice|guidelines)", re.I)

    def wrap_addresses(t: str) -> str:
        return address_re.sub(lambda m: f"[ADDRESS] {m.group(0)} [/ADDRESS]", t)

    def mostly_english(t: str) -> bool:
        letters = len(re.sub(r"[^A-Za-z]", "", t))
        return (letters > 0) and (letters / max(len(t), 1) > 0.6)

    def is_date_or_number(t: str) -> bool:
        if re.fullmatch(r"\d{1,4}", t):
            return True
        if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", t):
            return True
        if re.fullmatch(r"\d{4}[/-]\d{1,2}[/-]\d{1,2}", t):
            return True
        return False

    for raw in lines:
        cl = clean_line(raw)
        if not cl:
            continue
        cl = ui_words_re.sub("", cl)
        cl = MULTISPACE_RE.sub(" ", cl).strip()
        if not cl:
            continue
        if any(p.search(cl) for p in junk_patterns):
            continue
        if re.match(r"^గమనిక[\s:,-]", cl):
            if not important_note_re.search(cl):
                continue
        cl = wrap_addresses(cl)
        if mostly_english(cl) and "[ADDRESS]" not in cl:
            continue
        if (len(cl) >= 10 and telugu_char.search(cl)) or (len(cl) < 10 and is_date_or_number(cl)):
            if cl not in seen:
                seen[cl] = True
    return list(seen.keys())


def apply_post_rules(cleaned_lines: list[str]) -> list[str]:
    side_story_terms = ["బర్త్ డే", "థాయిలాండ్", "సింధు", "దర్శకులతో"]
    kept: list[str] = []
    for line in cleaned_lines:
        if not line:
            continue
        if line.startswith(":"):
            continue
        if "(ఫొటోలు)" in line:
            continue
        if any(term in line for term in side_story_terms):
            continue
        kept.append(line)
    return kept


def next_output_path(base_dir: str = ".") -> str:
    existing = [f for f in os.listdir(base_dir) if f.startswith("raw_telugu_") and f.endswith(".txt")]
    nums = []
    for f in existing:
        try:
            n = int(f[len("raw_telugu_"):-4])
            nums.append(n)
        except Exception:
            pass
    n = max(nums) + 1 if nums else 1
    return os.path.join(base_dir, f"raw_telugu_{n}.txt")


def main():
    parser = argparse.ArgumentParser(description="General Telugu text scraper")
    parser.add_argument("url", help="Seed/page URL to scrape")
    parser.add_argument("--follow", action="store_true", help="Also follow links from same domain")
    parser.add_argument("--limit", type=int, default=20, help="Max pages to follow")
    args = parser.parse_args()

    try:
        html = fetch(args.url)
    except Exception as e:
        print(f"[error] Failed to fetch: {e}", file=sys.stderr)
        sys.exit(1)

    all_paras = extract_paragraphs(html)
    cleaned_lines = filter_telugu(all_paras)
    post_lines = apply_post_rules(cleaned_lines)

    post_lines = post_lines[:5000]
    final_lines: list[str] = []
    if post_lines:
        final_lines.append(f"HEADLINE: {post_lines[0]}")
        final_lines.append("ARTICLE BODY:")
        final_lines.extend(post_lines[1:])

    out_path = next_output_path()
    with open(out_path, "w", encoding="utf-8") as f:
        for line in final_lines:
            f.write(line + "\n")

    print(f"Saved {len(final_lines)} lines to {out_path}")


if __name__ == "__main__":
    main()
