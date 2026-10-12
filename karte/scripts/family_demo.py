"""Render the same map crop (1:5000) with current symbols vs families A/B/C."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; sys.argv = ['x']; None
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
import render_map as R
import symbols2
from shapely.geometry import box
from PIL import Image
BB = (424300, 5960070, 424840, 5960230)
orig_sym, orig_halo = R.Sheet.sym, R.Sheet.halo
def crop(fam, out):
    if fam:
        def sym(S, kind, x, y, color, key, size=1.0, rot=0):
            symbols2.draw(S.ax, kind, x, y, S.m, color, fam, size * (1.05 if fam != 'C' else 1.0), paper=S.P['paper'])
        R.Sheet.sym = sym; R.Sheet.halo = lambda S, *a, **k: None
    else:
        R.Sheet.sym, R.Sheet.halo = orig_sym, orig_halo
    R.SHEETS['demo'] = dict(bbox=BB, scale=5000, orient='L', title='', sub='')
    S = R.Sheet.__new__(R.Sheet); S.cfg = R.SHEETS['demo']; S.mode = 'color'; S.P = R.PAL['color']
    S.x0, S.y0, S.x1, S.y1 = BB; S.scale = 5000; S.m = 5.0; S.dense = True; S.wobf = 0.3
    S.mw, S.mh = (S.x1 - S.x0) / S.m, (S.y1 - S.y0) / S.m
    S.fig = plt.figure(figsize=(S.mw / 25.4, S.mh / 25.4)); S.fig.patch.set_facecolor(S.P['paper'])
    S.ax = S.fig.add_axes([0, 0, 1, 1]); S.ax.set_xlim(S.x0, S.x1); S.ax.set_ylim(S.y0, S.y1); S.ax.set_aspect('equal'); S.ax.axis('off')
    S.clip = box(*BB); S.pw, S.ph = S.mw, S.mh; S.mx = S.my = 0
    R.layer_base(S); R.layer_areas(S); R.layer_contours(S); R.layer_ruhezone(S); R.layer_lines(S); R.layer_buildings(S); R.layer_points(S); R.layer_labels(S)
    S.fig.savefig(out, dpi=520, facecolor=S.P['paper']); plt.close(S.fig)
outs = []
for fam, lab in ((None, 'heute'), ('A', 'A · Feinlinie'), ('B', 'B · Silhouette'), ('C', 'C · OL-reduziert')):
    p = f'/tmp/claude-0/-home-claude/1a5b4d62-7e67-5e49-80a0-733f9e1c92d8/scratchpad/demo_{fam}.png'; crop(fam, p); outs.append((p, lab))
ims = [Image.open(p).convert('RGB') for p, _ in outs]; w, h = ims[0].size
canvas = Image.new('RGB', (w * 2 + 30, (h + 70) * 2 + 10), (255, 253, 247))
from PIL import ImageDraw, ImageFont
dr = ImageDraw.Draw(canvas); f = ImageFont.truetype(BASE + '/fonts/Caveat-Bold.ttf', 52)
for i, (im, (_, lab)) in enumerate(zip(ims, outs)):
    x = (i % 2) * (w + 30); y = (i // 2) * (h + 70)
    dr.text((x + 10, y + 5), lab, font=f, fill=(155, 63, 181)); canvas.paste(im, (x, y + 65))
canvas.save(BASE + '/out/symbol_map_demo.png'); print(canvas.size)
