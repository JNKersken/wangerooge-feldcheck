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
names = ', '.join(sorted({md(FM.kurz(FM.sender(d)[0])) for _, d in subs})) or '?'   # public PR: initials only
parts = [f"{cnt[k]} {w}" for k, w in (('ok', 'bestätigt'), ('fehlt', 'fehlen'), ('woanders', 'verschoben'), ('nf', 'nicht gefunden'), ('neu', 'neu')) if cnt[k]]
titel = f"Feldcheck von {names}: " + (', '.join(parts) or 'keine gültigen Einträge') + (f" ({cnt['übersprungen']} übersprungen)" if cnt['übersprungen'] else '')
open(title_file, 'w').write(titel.replace('\\', '') + '\n')

# previews: changed spots circled on the colour sheets that contain them
os.makedirs(BASE + '/out/vorschau', exist_ok=True)
COL = {'ok': (46, 157, 87), 'fehlt': (207, 65, 54), 'woanders': (217, 138, 28), 'neu': (43, 111, 214), 'nf': (142, 142, 147)}
VERB_S = {'ok': 'stimmt', 'fehlt': 'fehlt', 'fehlt (2× nicht gefunden)': 'fehlt', 'woanders': 'woanders', 'nf': 'nicht gefunden'}
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

# ---------- hints: what deserves a closer look before approving ----------
import math
PTS = {f['properties']['id']: f for f in json.load(open(BASE + '/data/points_v1.geojson', encoding='utf-8'))['features']}
hints = []   # (id, text, [(e, n, colour)])
def _f(x):
    try: return float(x)
    except (TypeError, ValueError): return None
for e in log:
    E, N, E0, N0, acc, d = (_f(e.get(k)) for k in ('e', 'n', 'e0', 'n0', 'acc', 'd'))
    if E is not None and E0 is not None and math.hypot(E - E0, N - N0) > 75:
        hints.append((e['id'], f"um {round(math.hypot(E - E0, N - N0))} m verschoben", [(E0, N0, (142, 142, 147)), (E, N, COL['woanders'])]))
    if acc is not None and acc > 20:
        hints.append((e['id'], f"GPS ungenau (± {round(acc)} m)", [(E, N, COL['woanders'])] if E is not None else []))
    if d is not None and d > 150 and e['aktion'] in ('ok', 'fehlt', 'fehlt (2× nicht gefunden)', 'nf'):
        hints.append((e['id'], f"„{VERB_S.get(e['aktion'], e['aktion'])}“ aus {round(d)} m Entfernung", [(E, N, COL['fehlt'])] if E is not None else []))
# different helpers disagree about one object (in this batch)
per = collections.defaultdict(dict)
for fn, d_ in subs:
    who = FM.kurz(FM.sender(d_)[0]); vs = d_.get('verdicts') if isinstance(d_.get('verdicts'), dict) else {}
    for id_, v in vs.items():
        if isinstance(v, dict) and v.get('st') in FM.VERDICTS and v.get('st') != 'zurueck': per[str(id_)][who] = v['st']
for id_, by in sorted(per.items()):
    if len(set(by.values())) > 1:
        p_ = PTS.get(id_); xy = [(*p_['geometry']['coordinates'], COL['woanders'])] if p_ else []
        hints.append((id_, 'widersprüchlich: ' + ', '.join(f"{w} {VERB_S.get(st, st)}" for w, st in sorted(by.items())), xy))
# new objects that may already exist
for e in log:
    if e['aktion'] != 'neu' or e['id'] not in PTS: continue
    p_ = PTS[e['id']]['properties']; E, N = PTS[e['id']]['geometry']['coordinates']
    for oid, f in PTS.items():
        if oid == e['id']: continue
        q = f['properties']; dd = math.hypot(f['geometry']['coordinates'][0] - E, f['geometry']['coordinates'][1] - N)
        if q['kategorie'] == p_['kategorie'] and dd < 15:
            hints.append((e['id'], f"evtl. doppelt: {q['kategorie']} {oid} liegt {round(dd)} m daneben", [(E, N, COL['neu']), (*f['geometry']['coordinates'], (142, 142, 147))])); break
        if p_['kategorie'] == 'Rettungspunkt' and p_['name'] and q['kategorie'] == 'Rettungspunkt' and q['name'] == p_['name'] and dd >= 15:
            hints.append((e['id'], f"SOS-Nummer {p_['name']} gibt es schon ({oid}, {round(dd)} m entfernt)", [(E, N, COL['neu']), (*f['geometry']['coordinates'], COL['fehlt'])])); break

_sheet_png = {}
def crop(key, marks):
    """Small map cut-out around the marks (colour sheet that contains them), circles in the given colours."""
    marks = [m for m in marks if m[0] is not None]
    if not marks: return None
    cx, cy = sum(m[0] for m in marks) / len(marks), sum(m[1] for m in marks) / len(marks)
    for name in DETAIL_ORDER:
        lay = R.sheet_layout(name); x0, y0, x1, y1 = lay['bbox']
        if not (x0 <= cx <= x1 and y0 <= cy <= y1): continue
        png = f'{BASE}/out/maps/{name}_color.png'
        if not os.path.exists(png): continue
        if name not in _sheet_png: _sheet_png[name] = Image.open(png).convert('RGB')
        im = _sheet_png[name]; px_mm = im.size[0] / lay['pw']
        to_px = lambda E, N: ((lay['mx'] + (E - x0) / lay['m']) * px_mm, (lay['ph'] - (lay['my'] + (N - y0) / lay['m'])) * px_mm)
        half = max(60, max(math.hypot(m[0] - cx, m[1] - cy) for m in marks) + 40) / lay['m'] * px_mm
        pcx, pcy = to_px(cx, cy)
        c = im.crop((int(pcx - half), int(pcy - half), int(pcx + half), int(pcy + half))).copy(); dr = ImageDraw.Draw(c)
        r = 3.2 * px_mm
        pts_px = [(to_px(m[0], m[1]), m[2]) for m in marks]
        if len(pts_px) == 2: dr.line([(p[0] - pcx + half, p[1] - pcy + half) for p, _ in pts_px], fill=(80, 80, 80), width=2)
        for (px, py), col in pts_px:
            px, py = px - pcx + half, py - pcy + half
            dr.ellipse([px - r, py - r, px + r, py + r], outline=col, width=max(3, int(px_mm / 2.4)))
        c = c.resize((320, 320), Image.LANCZOS); fn = f'h_{re.sub(r"[^A-Za-z0-9]", "", key)}.jpg'
        c.save(f'{BASE}/out/vorschau/{fn}', quality=85); return fn
    return None

VERB = {'ok': '✓ bestätigt', 'fehlt': '✗ fehlt – wird entfernt', 'fehlt (2× nicht gefunden)': '✗ fehlt – zweimal nicht gefunden, wird entfernt',
        'woanders': '↦ verschoben', 'nf': '? nicht gefunden – bleibt, bitte prüfen', 'neu': '★ neu', 'übersprungen': '⚠ übersprungen (fehlerhaft)'}
print(f'## {titel}\n')
for fn, d in subs:
    print(f"- **{md(FM.kurz(FM.sender(d)[0]))}** · gesendet {md(FM.text(d.get('gesendet'), 16).replace('T', ' '))} · `{md(fn)}`")
print('\n| Aktion | Anzahl |\n|---|---|')
for k in ('ok', 'fehlt', 'woanders', 'nf', 'neu', 'übersprungen'):
    if cnt[k]: print(f"| {VERB[k]} | {cnt[k]} |")
if hints:
    grp = {}   # one entry and one cut-out per object
    for id_, txt, marks in hints:
        g = grp.setdefault(id_, ([], [])); g[0].append(txt); g[1].extend(m for m in marks if m not in g[1])
    print(f'\n### ⚠ Bitte genauer ansehen ({len(grp)})\n')
    for id_, (txts, marks) in grp.items():
        p_ = PTS.get(id_, {}).get('properties', {}); nm = p_.get('name') or next((e['name'] for e in log if e['id'] == id_), '') or p_.get('typ', '')
        print(f"- **{md(id_)}** {md(nm)} – {md('; '.join(txts))}")
        fn = crop(id_, marks)
        if fn: print(f'  <br><img src="{RAW}/{fn}?v={run}" width="200" alt="Ausschnitt {md(id_)}">')
else:
    print('\n✓ Keine Auffälligkeiten (große Verschiebungen, ungenaues GPS, Bewertung aus der Ferne, Widersprüche, Doppelte).')
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
