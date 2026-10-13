"""Summary + preview images for a field-check pull request.
Usage: feldcheck_report.py <list of new submission files> <run id>   -> writes /tmp/titel.txt and prints the PR body (Markdown)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import json, sys, os, datetime, collections
from PIL import Image, ImageDraw
import matplotlib; matplotlib.use('Agg')
import render_map as R

files = [l.strip() for l in open(sys.argv[1]) if l.strip().endswith('.json')]
run = sys.argv[2] if len(sys.argv) > 2 else '0'
RAW = 'https://raw.githubusercontent.com/JNKersken/wangerooge-feldcheck/feldcheck-update/karte/out/vorschau'
subs = []
for f in files:
    p = f if os.path.isabs(f) else os.path.join(os.path.dirname(BASE), f)
    try: subs.append((os.path.basename(f), json.load(open(p))))
    except Exception as e: print(f'<!-- {f}: {e} -->')
ids = set(); who = []
for fn, d in subs:
    ids |= set((d.get('verdicts') or {}).keys()) | {'F' + k for k in (d.get('neu') or {}).keys()}
    who.append((d.get('name') or '?').strip())
log = [e for e in json.load(open(BASE + '/data/feldcheck_log.json')) if e['id'] in ids]
cnt = collections.Counter(e['aktion'] for e in log)
names = ', '.join(sorted(set(who))) or '?'
titel = f"Feldcheck von {names}: {cnt['ok']} bestätigt, {cnt['fehlt']} fehlen, {cnt['woanders']} verschoben, {cnt['neu']} neu"
open('/tmp/titel.txt', 'w').write(titel + '\n')

# previews: changed spots circled on the colour sheets that contain them
os.makedirs(BASE + '/out/vorschau', exist_ok=True)
COL = {'ok': (46, 157, 87), 'fehlt': (207, 65, 54), 'woanders': (217, 138, 28), 'neu': (43, 111, 214)}
imgs = []
for name in R.DETAIL_ORDER:
    cfg = R.SHEETS[name]; x0, y0, x1, y1 = cfg['bbox']
    hits = [e for e in log if e['e'] != '' and x0 <= float(e['e']) <= x1 and y0 <= float(e['n']) <= y1]
    png = f'{BASE}/out/maps/{name}_color.png'
    if not hits or not os.path.exists(png): continue
    im = Image.open(png).convert('RGB'); dpi = im.size[0] / (297 if cfg['orient'] == 'L' else 210) * 25.4
    m = cfg['scale'] / 1000; pw, ph = (297, 210) if cfg['orient'] == 'L' else (210, 297)
    mx = 8 if name == 'uebersicht' else (pw - (x1 - x0) / m) / 2; my = 22
    dr = ImageDraw.Draw(im); r = 3.2 * dpi / 25.4
    for e in hits:
        px = (mx + (float(e['e']) - x0) / m) * dpi / 25.4; py = (ph - (my + (float(e['n']) - y0) / m)) * dpi / 25.4
        dr.ellipse([px - r, py - r, px + r, py + r], outline=COL.get(e['aktion'], (0, 0, 0)), width=max(3, int(dpi / 60)))
    w = 1600; im = im.resize((w, int(im.size[1] * w / im.size[0])), Image.LANCZOS)
    im.save(f'{BASE}/out/vorschau/{name}.jpg', quality=82); imgs.append((name, cfg['sub']))

VERB = {'ok': '✓ bestätigt', 'fehlt': '✗ fehlt – wird entfernt', 'woanders': '↦ verschoben', 'neu': '★ neu'}
print(f'## {titel}\n')
for fn, d in subs:
    print(f"- **{(d.get('name') or '?')}** · gesendet {d.get('gesendet', '')[:16].replace('T', ' ')} · `{fn}`")
print('\n| Aktion | Anzahl |\n|---|---|')
for k in ('ok', 'fehlt', 'woanders', 'neu'): print(f'| {VERB[k]} | {cnt[k]} |')
print('\n<details><summary>Alle Änderungen</summary>\n')
for e in sorted(log, key=lambda e: (e['aktion'], e['id'])):
    nm = f"SOS-Schild {e['name']}" if e['kategorie'] == 'Rettungspunkt' and str(e['name']).isdigit() else e['name']
    print(f"- {VERB.get(e['aktion'], e['aktion'])}: **{e['id']}** {nm} ({e['kategorie']}) – {e['von']}" + (f" – „{e['notiz']}“" if e.get('notiz') else ''))
print('\n</details>\n')
if imgs:
    print('### Vorschau (Kreise: grün bestätigt · rot fehlt · orange verschoben · blau neu)\n')
    for n, sub in imgs: print(f'**{sub}**\n\n![{sub}]({RAW}/{n}.jpg?v={run})\n')
print('---\n**Freigeben:** „Merge pull request“ – danach aktualisieren sich App und PDF-Export nach wenigen Minuten.  \n'
      '**Ablehnen:** „Close pull request“ – die Karte bleibt unverändert, die Einsendung wird beiseitegelegt.')
