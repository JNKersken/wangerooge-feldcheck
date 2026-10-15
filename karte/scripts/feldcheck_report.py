"""Summary + preview images for a field-check pull request.
Usage: feldcheck_report.py <file with list of new submission files> <run id> <title file>
-> writes the PR title to the title file and prints the PR body (Markdown). Counts only entries whose winning copy
sits in one of the new files (feldcheck_merge keeps the first file for repeated entries)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE, GH_REPO, DETAIL_ORDER
import json, sys, os, re, collections
from PIL import Image, ImageDraw
import matplotlib; matplotlib.use('Agg')
import render_map as R
import feldcheck_merge as FM

files = [l.strip() for l in open(sys.argv[1]) if l.strip().endswith('.json')]
run = sys.argv[2] if len(sys.argv) > 2 else '0'
title_file = sys.argv[3]
RAW = f'https://raw.githubusercontent.com/{GH_REPO}/vorschau'   # the workflow puts the images on their own branch, never into main
md = lambda s: re.sub(r'([\\`*_\[\]<>|#])', r'\\\1', str(s or ''))   # helper names and notes are plain text, not Markdown

new = {os.path.basename(f) for f in files}
subs = []
for f in files:
    p = f if os.path.isabs(f) else os.path.join(os.path.dirname(BASE), f)
    d, _ = FM.read(p)
    subs.append((os.path.basename(f), d or {}))
log = [e for e in json.load(open(BASE + '/data/feldcheck_log.json', encoding='utf-8')) if e.get('datei') in new]
cnt = collections.Counter('fehlt' if e['aktion'].startswith('fehlt') else e['aktion'] for e in log)
names = ', '.join(sorted({md(FM.sender(d)[0]) for _, d in subs})) or '?'
parts = [f"{cnt[k]} {w}" for k, w in (('ok', 'bestätigt'), ('fehlt', 'fehlen'), ('woanders', 'verschoben'), ('nf', 'nicht gefunden'), ('neu', 'neu')) if cnt[k]]
titel = f"Feldcheck von {names}: " + (', '.join(parts) or 'keine gültigen Einträge') + (f" ({cnt['übersprungen']} übersprungen)" if cnt['übersprungen'] else '')
open(title_file, 'w').write(titel.replace('\\', '') + '\n')

# previews: changed spots circled on the colour sheets that contain them
os.makedirs(BASE + '/out/vorschau', exist_ok=True)
COL = {'ok': (46, 157, 87), 'fehlt': (207, 65, 54), 'woanders': (217, 138, 28), 'neu': (43, 111, 214), 'nf': (142, 142, 147)}
imgs = []
for name in DETAIL_ORDER:
    lay = R.sheet_layout(name); x0, y0, x1, y1 = lay['bbox']
    hits = [e for e in log if e.get('e') not in ('', None) and x0 <= float(e['e']) <= x1 and y0 <= float(e['n']) <= y1]
    png = f'{BASE}/out/maps/{name}_color.png'
    if not hits or not os.path.exists(png): continue
    im = Image.open(png).convert('RGB'); px_mm = im.size[0] / lay['pw']
    dr = ImageDraw.Draw(im); r = 3.2 * px_mm
    for e in hits:
        px = (lay['mx'] + (float(e['e']) - x0) / lay['m']) * px_mm; py = (lay['ph'] - (lay['my'] + (float(e['n']) - y0) / lay['m'])) * px_mm
        col = COL['fehlt'] if e['aktion'].startswith('fehlt') else COL.get(e['aktion'], (0, 0, 0))
        dr.ellipse([px - r, py - r, px + r, py + r], outline=col, width=max(3, int(px_mm / 2.4)))
    w = 1600; im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)
    im.save(f'{BASE}/out/vorschau/{name}.jpg', quality=82); imgs.append((name, lay['sub']))

VERB = {'ok': '✓ bestätigt', 'fehlt': '✗ fehlt – wird entfernt', 'fehlt (2× nicht gefunden)': '✗ fehlt – zweimal nicht gefunden, wird entfernt',
        'woanders': '↦ verschoben', 'nf': '? nicht gefunden – bleibt, bitte prüfen', 'neu': '★ neu', 'übersprungen': '⚠ übersprungen (fehlerhaft)'}
print(f'## {titel}\n')
for fn, d in subs:
    print(f"- **{md(FM.sender(d)[0])}** · gesendet {md(FM.text(d.get('gesendet'), 16).replace('T', ' '))} · `{md(fn)}`")
print('\n| Aktion | Anzahl |\n|---|---|')
for k in ('ok', 'fehlt', 'woanders', 'nf', 'neu', 'übersprungen'):
    if cnt[k]: print(f"| {VERB[k]} | {cnt[k]} |")
print('\n<details><summary>Alle Änderungen</summary>\n')
for e in sorted(log, key=lambda e: (e['aktion'], e['id'])):
    nm = f"SOS-Schild {e['name']}" if e['kategorie'] == 'Rettungspunkt' and str(e['name']).isdigit() else e['name']
    print(f"- {VERB.get(e['aktion'], md(e['aktion']))}: **{md(e['id'])}** {md(nm)}" + (f" ({md(e['kategorie'])})" if e['kategorie'] else '')
          + (f" – {md(e['von'])}" if e['von'] else '') + (f" – „{md(e['notiz'])}“" if e.get('notiz') else ''))
print('\n</details>\n')
if imgs:
    print('### Vorschau (Kreise: grün bestätigt · rot fehlt · orange verschoben · grau nicht gefunden · blau neu)\n')
    for n, sub in imgs: print(f'**{sub}**\n\n![{sub}]({RAW}/{n}.jpg?v={run})\n')
print('---\n**Freigeben:** „Merge pull request“ – danach aktualisieren sich App und PDF-Export nach wenigen Minuten.  \n'
      '**Ablehnen:** „Close pull request“ – die Karte bleibt unverändert, die Einsendung wird beiseitegelegt.')
