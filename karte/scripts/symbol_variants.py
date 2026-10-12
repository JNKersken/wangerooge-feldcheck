import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from symbols2 import draw, SERIFB, PT
HAND = fm.FontProperties(fname=BASE + '/fonts/Caveat-Bold.ttf')
ink, paper, red = '#1d1d1f', '#fffdf7', '#8e1b1b'
rows = [('SOS-Schild', [('rescue', 'cross', '1 Kreuz im Quadrat'), ('rescue', 'sos', '2 Mini-Schild „SOS“'), ('rescue', 'sign', '3 Schild am Pfosten'), ('rescue', 'tri', '4 Warndreieck')]),
        ('Bank', [('bench', None, '1 Sitz + Beine'), ('bench', 'side', '2 Seitenansicht mit Lehne')]),
        ('Gastronomie', [('food', 'cup', '1 Tasse'), ('food', 'cutlery', '2 Besteck')]),
        ('Feuerstelle', [('fire', None, '1 Lagerfeuer'), ('fire', 'drop', '2 Flamme')]),
        ('Gruppe (Anzahl)', [('g_roman', None, '1 römisch, Balken'), ('g_dots', None, '2 Punkte'), ('g_num', None, '3 Ziffer klein')])]
W, H = 210, 18 + 22 * len(rows)
fig = plt.figure(figsize=(W / 25.4, H / 25.4)); fig.patch.set_facecolor(paper)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off'); ax.set_aspect('equal')
ax.text(8, H - 9, 'Motiv-Varianten (Familie A / B jeweils nebeneinander)', fontproperties=HAND, fontsize=17, va='center')
def roman_bars(x, y, h, n=4):
    txt = {3: 'III', 4: 'IV', 6: 'VI'}[n]; wI, wV, g = 0.32 * h, 0.62 * h, 0.12 * h; xs = x
    for ch in txt:
        if ch == 'I': ax.plot([xs + wI / 2] * 2, [y - h / 2, y + h / 2], color=red, lw=1.2); xs += wI + g
        else: ax.plot([xs, xs + wV / 2, xs + wV], [y + h / 2, y - h / 2, y + h / 2], color=red, lw=1.2); xs += wV + g
    ax.plot([x - 0.06 * h, xs - g + 0.06 * h], [y + h / 2] * 2, color=red, lw=1.2); ax.plot([x - 0.06 * h, xs - g + 0.06 * h], [y - h / 2] * 2, color=red, lw=1.2)
for i, (name, vs) in enumerate(rows):
    y = H - 24 - i * 22
    ax.text(8, y, name, fontsize=8.5, va='center', color=ink)
    for j, (k, v, lab) in enumerate(vs):
        cx = 55 + j * 38
        if k.startswith('g_'):
            draw(ax, 'bench', cx - 6, y, 1.0, ink, 'A', size=4.0, paper=paper, knock=False)
            if k == 'g_roman': roman_bars(cx + 1.5, y, 3.2)
            elif k == 'g_dots':
                for d in range(4): ax.add_patch(plt.Circle((cx + 2.2 + (d % 2) * 1.8, y + 1.0 - (d // 2) * 1.8), 0.6, color=red))
            else: ax.text(cx + 1.6, y, '4', fontproperties=SERIFB, fontsize=13, color=red, va='center')
        else:
            draw(ax, k, cx - 6, y, 1.0, ink, 'A', size=4.0, paper=paper, variant=v, knock=False)
            draw(ax, k, cx + 6, y, 1.0, ink, 'B', size=4.0, paper=paper, variant=v, knock=False)
        ax.text(cx, y - 7.5, lab, fontsize=6.5, ha='center', va='center', color='#555')
    ax.plot([6, 204], [y - 11, y - 11], color='#e8e2d6', lw=0.4)
plt.savefig(BASE + '/out/symbol_variants.png', dpi=200, facecolor=paper); print('ok')
