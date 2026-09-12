import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const SRC = path.join(ROOT, 'index.html');
const OUT = path.join(ROOT, '_site');
const ASSETS = path.join(OUT, 'assets');

let html = await readFile(SRC, 'utf8');

const replacements = new Map([
  ['https://commons.wikimedia.org/wiki/Special:Redirect/file/Elephant%20Trunk%20Hill%20Guilin.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:Redirect/file/ElephantTrunkHill.jpg?width=1200'],
  ['https://commons.wikimedia.org/wiki/Special:Redirect/file/Longji%20rice%20terraces%20Guangxi.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Longji%20rice%20terraces.jpg?width=1200'],
  ['https://commons.wikimedia.org/wiki/Special:Redirect/file/Li%20River%20China.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Li%20River%20cruise%20from%20Guilin%20to%20Yangshuo.JPG?width=1200'],
  ['https://commons.wikimedia.org/wiki/Special:Redirect/file/Detian%20Waterfall.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Full%20Sight%20for%20Detian%20Waterfalls%20%26%20Ban%20Gioc%20Waterfalls.jpg?width=1200'],
  ['https://commons.wikimedia.org/wiki/Special:Redirect/file/Ban%20Gioc%20-%20Detian%20Falls.jpg?width=1200', 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Ban%20Gioc%20-%20Detian%20Falls14.jpg?width=1200'],
]);
for (const [from, to] of replacements) html = html.split(from).join(to);

await mkdir(ASSETS, { recursive: true });

const fallback = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#dbe9df"/><stop offset="1" stop-color="#8fb3a6"/></linearGradient></defs><rect width="1200" height="800" fill="url(#g)"/><path d="M0 620L280 340l170 170 180-250 190 210 160-130 220 280v180H0z" fill="#315e53" opacity=".7"/><circle cx="930" cy="180" r="78" fill="#f3d39a"/><text x="600" y="720" text-anchor="middle" font-size="42" fill="#f8fbf9" font-family="sans-serif">广西 · 山水到海</text></svg>`;
await writeFile(path.join(ASSETS, 'fallback.svg'), fallback);

const urls = [...new Set([...html.matchAll(/src="(https:\/\/commons\.wikimedia\.org\/wiki\/Special:Redirect\/file\/[^"]+)"/g)].map(m => m[1]))];

function extFor(contentType) {
  if (contentType.includes('jpeg')) return '.jpg';
  if (contentType.includes('png')) return '.png';
  if (contentType.includes('webp')) return '.webp';
  if (contentType.includes('gif')) return '.gif';
  if (contentType.includes('svg')) return '.svg';
  return '.img';
}

async function cacheOne(rawUrl, index) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(rawUrl, {
      redirect: 'follow',
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; GuangxiJourneyEdgeOne/1.0)',
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
      },
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const contentType = (response.headers.get('content-type') || '').toLowerCase();
    if (!contentType.startsWith('image/')) throw new Error(`unexpected content-type ${contentType}`);
    const bytes = Buffer.from(await response.arrayBuffer());
    const digest = createHash('sha1').update(rawUrl).digest('hex').slice(0, 12);
    const name = `travel-${String(index).padStart(2, '0')}-${digest}${extFor(contentType)}`;
    await writeFile(path.join(ASSETS, name), bytes);
    console.log(`OK ${index}: ${contentType} ${bytes.length} bytes -> ${name}`);
    return [rawUrl, `assets/${name}`, true];
  } catch (err) {
    console.error(`FAILED ${index}: ${rawUrl} :: ${err}`);
    return [rawUrl, 'assets/fallback.svg', false];
  } finally {
    clearTimeout(timer);
  }
}

const results = await Promise.all(urls.map((url, i) => cacheOne(url, i + 1)));
let ok = 0;
for (const [rawUrl, local, success] of results) {
  html = html.split(rawUrl).join(local);
  if (success) ok += 1;
}

await writeFile(path.join(OUT, 'index.html'), html, 'utf8');
console.log(`Cached ${ok}/${urls.length} unique remote images locally; fallback=${urls.length - ok}.`);
