const express = require('express');
const multer = require('multer');
const cors = require('cors');
const morgan = require('morgan');
const compression = require('compression');
const path = require('path');
const fs = require('fs');
const axios = require('axios');
const cheerio = require('cheerio');
const { cleanText } = require('./utils/clean');

const app = express();
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 10 * 1024 * 1024 } }); // 10MB

// Middleware
app.use(morgan('dev'));
app.use(compression());
app.use(express.json({ limit: '2mb' }));
app.use(express.urlencoded({ extended: true }));

// CORS in development
if (process.env.NODE_ENV !== 'production') {
  app.use(cors({ origin: '*'}));
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Helpers for scraper-clean flow
function getNextOutputPath() {
  const rootDir = path.resolve(__dirname, '..');
  // Find next raw_telugu_N.txt
  let n = 1;
  // Scan existing numbers quickly
  const files = fs.readdirSync(rootDir).filter((f) => /^raw_telugu_\d+\.txt$/.test(f));
  if (files.length > 0) {
    const nums = files.map((f) => parseInt((f.match(/raw_telugu_(\d+)\.txt/) || [])[1], 10)).filter(Number.isFinite);
    if (nums.length) n = Math.max(...nums) + 1;
  }
  return path.join(rootDir, `raw_telugu_${n}.txt`);
}

function teluguStrictClean(lines) {
  // Keep Telugu block, digits, whitespace, and extended punctuation
  // Allowed punctuation: . , ! ? ; : ( ) " ' - — … ₹ (plus en dash)
  // Also allow ASCII letters to preserve meaningful English entities (AP, COVID-19, ETV, names)
  const teluguOnly = /[^\u0C00-\u0C7F0-9A-Za-z\s\.,!\?;:\(\)"'\-\/\u2013\u2014\u2026\u20B9]+/g;
  const teluguChar = /[\u0C00-\u0C7F]/;
  const junkPatterns = [
    /డౌన్\s*లోడ్/i,
    /ఇక్కడ\s*చూడండి/i,
    /క్లిక్/i,
    /click/i,
    /pdf/i,
    /డౌన్‌లోడ్/i,
    /download/i,
    /live\s*updates?/i,
  ];
  const uiWordsRE = /\b(click|download|pdf|live\s*updates?)\b/ig;
  const addressRE = /\b\d{1,4}(?:[-\/]\d{1,4}){1,4}\b(?:[^\n]*?\b\d{3}\s?-?\s?\d{3}\b)?/g; // e.g., 50-17-64 ... 500016
  const importantNoteRE = /(పరీక్ష|సూచనలు|ప్రకటన|అధికారిక|హెచ్చరిక|జాగ్రత్త|advisory|notice|guidelines)/i;
  const mostlyEnglish = (t) => {
    const letters = t.replace(/[^A-Za-z]/g, '').length;
    return letters > 0 && letters / t.length > 0.6;
  };
  const isDateOrNumber = (t) => {
    // Accept short numeric/date lines like 30, 2024, 26/08/2025, 10-10-2024
    if (/^\d{1,4}$/.test(t)) return true;
    if (/^\d{1,2}[\/-]\d{1,2}[\/-]\d{2,4}$/.test(t)) return true;
    if (/^\d{4}[\/-]\d{1,2}[\/-]\d{1,2}$/.test(t)) return true;
    return false;
  };
  const seen = new Set();
  const out = [];
  for (const raw of lines) {
    let t = String(raw || '').replace(/\s+/g, ' ').trim();
    if (!t) continue;
    t = t.replace(teluguOnly, ' ').replace(/\s+/g, ' ').trim();
    if (!t) continue;
    // Remove UI junk words within the line
    t = t.replace(uiWordsRE, '').replace(/\s+/g, ' ').trim();
    if (!t) continue;
    // Exclude junk
    if (junkPatterns.some((re) => re.test(t))) continue;
    // గమనిక handling: drop unless contains important keywords
    if (/^గమనిక[\s:,-]/.test(t)) {
      if (!importantNoteRE.test(t)) {
        continue;
      }
    }
    // Wrap address-like parts
    t = t.replace(addressRE, (m) => `[ADDRESS] ${m} [/ADDRESS]`);
    // If mostly English and not an address, likely non-article UI; skip
    if (mostlyEnglish(t) && !/\[ADDRESS\]/.test(t)) continue;
    // Keep if Telugu present and length >= 10, or if it is a short numeric/date line
    if ((t.length >= 10 && teluguChar.test(t)) || (t.length < 10 && isDateOrNumber(t))) {
      if (!seen.has(t)) {
        seen.add(t);
        out.push(t);
      }
    }
    if (out.length >= 5000) break; // default cap
  }
  return out;
}

// POST /scrape-clean { url }
// Scrapes, cleans, saves to auto-incremented file, and returns as download
app.post('/scrape-clean', async (req, res) => {
  try {
    const url = req.body && req.body.url;
    if (!url || typeof url !== 'string') {
      return res.status(400).json({ error: 'Missing or invalid "url" in JSON body.' });
    }

    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'te,en;q=0.8,*;q=0.5',
      },
    });
    const html = Buffer.from(response.data).toString('utf8');
    const $ = cheerio.load(html);

    // Gather headline (prefer h1 then h2)
    const rawHeadline = ($('h1').first().text() || $('h2').first().text() || '').replace(/\s+/g, ' ').trim();

    // Gather paragraphs with preference
    let $p = $('article p');
    if ($p.length === 0) $p = $('main p');
    if ($p.length === 0) $p = $('div[role="main"] p');
    if ($p.length === 0) $p = $('p');

    const rawParas = [];
    $p.each((_, el) => {
      const t = $(el).text();
      if (t && t.trim()) rawParas.push(t);
    });

    const cleanedLines = teluguStrictClean(rawParas);

    // Clean headline with same allow-list but no length constraint, and remove UI junk words
    const headlineClean = (() => {
      const teluguOnly = /[^\u0C00-\u0C7F0-9A-Za-z\s\.,!\?;:\(\)"'\-\/\u2013\u2014\u2026\u20B9]+/g;
      const uiWordsRE = /\b(click|download|pdf|live\s*updates?)\b/ig;
      let h = String(rawHeadline || '').replace(/\s+/g, ' ').trim();
      h = h.replace(teluguOnly, ' ').replace(/\s+/g, ' ').trim();
      h = h.replace(uiWordsRE, '').replace(/\s+/g, ' ').trim();
      return h;
    })();

    const finalLines = [];
    if (headlineClean) {
      finalLines.push(`HEADLINE: ${headlineClean}`);
    }
    finalLines.push(...cleanedLines);

    const outPath = getNextOutputPath();
    fs.writeFileSync(outPath, finalLines.join('\n'), { encoding: 'utf8' });

    // Return as attachment; also include filename in header
    res.setHeader('X-Filename', path.basename(outPath));
    res.setHeader('Content-Type', 'text/plain; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${path.basename(outPath)}"`);
    return res.status(200).send(finalLines.join('\n'));
  } catch (err) {
    console.error('Error in /scrape-clean:', err?.message || err);
    return res.status(500).json({ error: 'Failed to scrape and clean the provided URL.' });
  }
});

// POST /clean supports JSON body {text} or multipart with field 'file'
app.post('/clean', upload.single('file'), async (req, res) => {
  try {
    let inputText = '';

    if (req.is('application/json') && req.body && typeof req.body.text === 'string') {
      inputText = req.body.text;
    } else if (req.file) {
      // Attempt to decode buffer as UTF-8
      inputText = req.file.buffer.toString('utf8');
    } else if (typeof req.body.text === 'string') {
      // Fallback for form fields
      inputText = req.body.text;
    }

    if (!inputText || inputText.trim().length === 0) {
      return res.status(400).json({ error: 'No text provided. Send JSON {"text": "..."} or upload a .txt file field named "file".' });
    }

    const cleaned = cleanText(inputText);

    const wantsDownload = ['1', 'true', 'yes'].includes(String(req.query.download || '').toLowerCase());

    if (wantsDownload) {
      const filename = 'cleaned.txt';
      res.setHeader('Content-Type', 'text/plain; charset=utf-8');
      res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
      return res.status(200).send(cleaned);
    }

    // Default JSON response
    return res.json({ cleaned });
  } catch (err) {
    console.error('Error in /clean:', err);
    res.status(500).json({ error: 'Internal server error' });
  }
});

// POST /scrape { url }
// Fetches the page, parses HTML with Cheerio, extracts main <p> blocks, and returns raw Telugu text
app.post('/scrape', async (req, res) => {
  try {
    const url = req.body && req.body.url;
    if (!url || typeof url !== 'string') {
      return res.status(400).json({ error: 'Missing or invalid "url" in JSON body.' });
    }

    // Fetch page
    const response = await axios.get(url, {
      responseType: 'arraybuffer',
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept-Language': 'te,en;q=0.8,*;q=0.5',
      },
      // timeout could be added if necessary
    });

    // Assume UTF-8; many Telugu sites use UTF-8
    const html = Buffer.from(response.data).toString('utf8');
    const $ = cheerio.load(html);

    // Prefer structured containers first
    let $p = $('article p');
    if ($p.length === 0) $p = $('main p');
    if ($p.length === 0) $p = $('div[role="main"] p');
    if ($p.length === 0) $p = $('p');

    const teluguRegex = /[\u0C00-\u0C7F]/;
    const paragraphs = [];
    $p.each((_, el) => {
      const t = $(el).text().replace(/\s+/g, ' ').trim();
      if (!t) return;
      // Keep paragraphs that contain Telugu script, avoid ultra-short fragments
      if (teluguRegex.test(t) && t.length >= 10) {
        paragraphs.push(t);
      }
    });

    const text = paragraphs.join('\n\n');
    return res.json({ text });
  } catch (err) {
    console.error('Error in /scrape:', err?.message || err);
    return res.status(500).json({ error: 'Failed to scrape the provided URL.' });
  }
});

// Serve frontend build in production
const distPath = path.resolve(__dirname, '..', 'frontend', 'dist');
if (fs.existsSync(distPath)) {
  app.use(express.static(distPath));
  app.get('*', (req, res) => {
    res.sendFile(path.join(distPath, 'index.html'));
  });
}

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
