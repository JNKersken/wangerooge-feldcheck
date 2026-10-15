"""Copy submissions from the inbox into the public repo (used by .github/workflows/feldcheck.yml).

  feldcheck_inbox.py import <inbox folder> <public folder> [--anon]
      copies <inbox>/*.json and <inbox>/abgelehnt/*.json; with --anon (private inbox repo) the helper's name becomes
      initials, the file name gets the initials instead of the name and the device text is dropped
  feldcheck_inbox.py name <file> [--anon]
      prints the public file name of an inbox file (the workflow uses it to find rejected submissions)

Without --anon (inbox = branch 'eingang' of the public repo) files are copied unchanged."""
import json, os, re, shutil, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feldcheck_merge as FM

_NAME = re.compile(r'^(\d{4}-\d{2}-\d{2}-\d{2}-\d{2})_(.+)_([a-z0-9]{2,8})\.json$')


def public_name(fn, anon):
    base = os.path.basename(fn)
    if not anon: return base
    m = _NAME.match(base)
    if not m: return 'x_' + hashlib.sha256(base.encode()).hexdigest()[:10] + '.json'
    ini = ''.join(w[0] for w in m[2].split('-') if w)[:3] or 'x'
    return f'{m[1]}_{ini}_{m[3]}.json'


def anonymize(raw):
    try: d = json.loads(raw)
    except Exception: return raw                      # broken file: copied as is, the merge skips and reports it
    if not isinstance(d, dict): return raw
    d['name'] = FM.kurz(d.get('name'))
    d.pop('geraet', None)                             # browser text of old app versions
    return json.dumps(d, ensure_ascii=False, indent=1).encode('utf-8')


def do_import(src, dst, anon):
    n = 0
    for sub in ('', 'abgelehnt'):
        s_dir, d_dir = os.path.join(src, sub), os.path.join(dst, sub)
        if not os.path.isdir(s_dir): continue
        os.makedirs(d_dir, exist_ok=True)
        for fn in sorted(os.listdir(s_dir)):
            if not fn.endswith('.json'): continue
            out = os.path.join(d_dir, public_name(fn, anon))
            if anon:
                data = anonymize(open(os.path.join(s_dir, fn), 'rb').read())
                if not os.path.exists(out) or open(out, 'rb').read() != data: open(out, 'wb').write(data)
            else:
                shutil.copyfile(os.path.join(s_dir, fn), out)
            n += 1
    print(f'{n} Einsendungen übernommen', file=sys.stderr)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--anon']; anon = '--anon' in sys.argv
    if args[:1] == ['import'] and len(args) == 3: do_import(args[1], args[2], anon)
    elif args[:1] == ['name'] and len(args) == 2: print(public_name(args[1], anon))
    else: sys.exit(__doc__)
