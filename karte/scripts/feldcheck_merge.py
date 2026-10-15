"""Field-check submissions from the app -> one verdict per object and the new objects, ready for build_layers.

Files: data/feldcheck/eingang/*.json (submitted; in main = approved), data/feldcheck/abgelehnt/*.json (rejected pull requests;
older location eingang/abgelehnt/ is read too).
Rules
- Every entry is checked on its own; a broken entry is skipped and listed, a broken file never stops the run.
- Positions must lie inside the map frame, times between 2025-01-01 and tomorrow.
- Per device (field 'geraet_id'; older files: the helper's name) only that device's newest entry per object counts.
  'zurueck' withdraws the device's verdict, a new object with 'geloescht' is withdrawn.
- Across devices the newest remaining verdict decides the status. A corrected position ('woanders') stays even when
  someone confirms the object later ('ok'), unless a newer 'woanders' moves it again.
- 'nf' (nicht gefunden) keeps the object; it counts as 'fehlt' once two different devices reported 'nf' or 'fehlt'
  and nobody confirmed it afterwards.
- Entries that were part of a rejected submission are ignored when they arrive again unchanged (same object, same time).
- If the same entry arrives in several files, it belongs to the first file (so a pull request only counts what is new).
"""
import glob, json, math, os, re, sys, time, datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from base import BASE, FRAME

VERDICTS = ('ok', 'fehlt', 'woanders', 'nf', 'zurueck')
T_MIN = 1735689600000                      # 2025-01-01 in ms
_ID_V = re.compile(r'^[A-Za-z0-9_-]{1,40}$')   # ids of existing objects (BK001, PF30127227, FN…)
_ID_N = re.compile(r'^N[a-z0-9]{1,20}$')       # ids the app gives new objects ('N' + base36 time)
_CTRL = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
TZ = ZoneInfo('Europe/Berlin')


def _num(x):
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) else None


def _time(x, now_ms):
    t = _num(x)
    return t if t is not None and T_MIN <= t <= now_ms + 86400000 else None


def in_frame(e, n, pad=0):
    return e is not None and n is not None and FRAME[0] - pad <= e <= FRAME[2] + pad and FRAME[1] - pad <= n <= FRAME[3] + pad


def day(t_ms):
    return datetime.datetime.fromtimestamp(t_ms / 1000, TZ).strftime('%d.%m.%Y')


def text(x, n=500):
    """Plain single-paragraph text: strings only, no control characters, trimmed and capped."""
    return _CTRL.sub('', x).strip()[:n] if isinstance(x, str) else ''


def _clean_verdict(v, now_ms):
    if not isinstance(v, dict): return None, 'kein Eintrag'
    st, t = v.get('st'), _time(v.get('t'), now_ms)
    if st not in VERDICTS: return None, f'unbekanntes Urteil {text(str(st), 20)!r}'
    if t is None: return None, 'Zeitstempel fehlt oder ist unplausibel'
    out = dict(st=st, t=t, note=text(v.get('note')))
    d = _num(v.get('d'))
    if d is not None and 0 <= d < 100000: out['d'] = round(d)          # phone–object distance when the verdict was given
    if st == 'woanders':
        e, n = _num(v.get('e')), _num(v.get('n'))
        if not in_frame(e, n): return None, 'neue Position fehlt oder liegt außerhalb der Karte'
        out.update(e=e, n=n, acc=_num(v.get('acc')), src=text(v.get('src'), 10))
    return out, None


def _clean_new(n_, now_ms):
    if not isinstance(n_, dict): return None, 'kein Eintrag'
    t = _time(n_.get('t'), now_ms)
    if t is None: return None, 'Zeitstempel fehlt oder ist unplausibel'
    out = dict(t=t, typ=text(n_.get('typ'), 40), name=text(n_.get('name'), 80), note=text(n_.get('note')), geloescht=n_.get('geloescht') is True)
    if out['geloescht']: return out, None
    if isinstance(n_.get('pts'), list):
        pts = [(_num(p[0]), _num(p[1])) for p in n_['pts'] if isinstance(p, (list, tuple)) and len(p) >= 2]
        pts = [p for p in pts if in_frame(*p)]
        if len(pts) < 2: return None, 'Pfad mit weniger als zwei Punkten in der Karte'
        out['pts'] = pts
    else:
        e, n = _num(n_.get('e')), _num(n_.get('n'))
        if not in_frame(e, n): return None, 'Position fehlt oder liegt außerhalb der Karte'
        out.update(e=e, n=n, acc=_num(n_.get('acc')), src=text(n_.get('src'), 10))
    return out, None


def read(fn):
    """-> (dict, None) or (None, reason)"""
    try:
        with open(fn, encoding='utf-8') as f: d = json.load(f)
    except Exception as e:
        return None, f'Datei unlesbar ({e.__class__.__name__})'
    if not isinstance(d, dict): return None, 'Datei hat kein gültiges Format'
    return d, None


def sender(d):
    """(display name, device key) of a submission; old app versions sent no device id."""
    who = text(d.get('name'), 60) or 'Feldcheck'
    dev = text(d.get('geraet_id'), 60)
    return who, (dev if re.match(r'^d-[A-Za-z0-9-]{4,56}$', dev) else 'name:' + who)


def _entries(d):
    v, n = d.get('verdicts'), d.get('neu')
    for id_, x in (v.items() if isinstance(v, dict) else []): yield 'v', str(id_), x
    for id_, x in (n.items() if isinstance(n, dict) else []): yield 'n', str(id_), x


def load(base=BASE, now_ms=None):
    """-> dict(verd={id: v}, neu={nid: n}, skipped=[...], files=[...],
               stand={device: {'v': {id: t}, 'n': {nid: t}, 'x': {id: t}}})   v/n = newest entry seen, x = rejected entries
    The app compares stand with what it still keeps on the phone: merged and rejected entries are cleaned up there."""
    now_ms = now_ms or time.time() * 1000
    folder = base + '/data/feldcheck'
    rejected, stand = set(), {}
    for fn in sorted(glob.glob(folder + '/abgelehnt/*.json') + glob.glob(folder + '/eingang/abgelehnt/*.json')):
        d, _ = read(fn)
        if not d: continue
        dev = sender(d)[1]
        for kind, id_, x in _entries(d):
            t = _num(x.get('t')) if isinstance(x, dict) else None
            if not t: continue
            rejected.add((kind, id_, t))
            sx = stand.setdefault(dev, {'v': {}, 'n': {}}).setdefault('x', {})
            sx[id_] = max(sx.get(id_, 0), t)
    skipped, latest = [], {}
    files = sorted(glob.glob(folder + '/eingang/*.json'))
    for fn in files:
        name = os.path.basename(fn)
        d, err = read(fn)
        if err: skipped.append(dict(datei=name, id='', grund=err)); continue
        who, dev = sender(d)
        for kind, id_, x in _entries(d):
            if not (_ID_V if kind == 'v' else _ID_N).match(id_): skipped.append(dict(datei=name, id=text(id_, 40), grund='ungültige Kennung')); continue
            clean, err = (_clean_verdict if kind == 'v' else _clean_new)(x, now_ms)
            if err: skipped.append(dict(datei=name, id=id_, grund=err)); continue
            if (kind, id_, clean['t']) in rejected: continue          # unchanged entry from a rejected submission
            clean.update(who=who, dev=dev, datei=name)
            k = (kind, dev, id_)
            if k not in latest or clean['t'] > latest[k]['t']: latest[k] = clean   # same entry again in a later file: keep the first file
            sd = stand.setdefault(dev, {'v': {}, 'n': {}})[kind]
            sd[id_] = max(sd.get(id_, 0), clean['t'])
    # verdicts: per object over all devices
    per_obj = {}
    for (kind, dev, id_), v in latest.items():
        if kind == 'v' and v['st'] != 'zurueck': per_obj.setdefault(id_, []).append(v)
    verd = {}
    for id_, vs in per_obj.items():
        vs.sort(key=lambda v: (v['t'], v['datei']))
        top = dict(vs[-1])
        moved = [v for v in vs if v['st'] == 'woanders']
        if top['st'] in ('ok', 'nf') and moved:                 # someone corrected the position before: keep it
            m = moved[-1]
            top.update(e=m['e'], n=m['n'], acc=m.get('acc'), src=m.get('src'), lage_von=m['who'])
            if top['st'] == 'ok': top['st'] = 'woanders'; top['bestaetigt'] = True
        if top['st'] == 'nf':
            confirmed_t = max([v['t'] for v in vs if v['st'] in ('ok', 'woanders')], default=0)
            gone = [v for v in vs if v['st'] in ('nf', 'fehlt') and v['t'] > confirmed_t]
            top['nf_von'] = sorted({v['who'] for v in gone})
            if len({v['dev'] for v in gone}) >= 2: top.update(st='fehlt', zwei_nf=True)
        verd[id_] = top
    neu = {}
    for (kind, dev, id_), n_ in latest.items():
        if kind == 'n' and (id_ not in neu or n_['t'] > neu[id_]['t']): neu[id_] = n_
    neu = {k: v for k, v in neu.items() if not v['geloescht']}
    return dict(verd=verd, neu=neu, skipped=skipped, stand=stand, files=[os.path.basename(f) for f in files])
