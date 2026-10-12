"""Overview sheet: 3 families x all symbols: large form, print size x2 on paper, print size x2 on meadow with contour (shows knockout)."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from symbols2 import draw, KINDS
HAND = fm.FontProperties(fname=BASE + '/fonts/Caveat-Bold.ttf')
fams = [('A', 'A · Feinlinie'), ('B', 'B · Silhouette'), ('C', 'C · OL-reduziert')]
ink, paper, meadow, brown = '#1d1d1f', '#fffdf7', '#fbefb8', '#b0662a'
W, H = 210, 30 + 11 * len(KINDS)
fig = plt.figure(figsize=(W / 25.4, H / 25.4)); fig.patch.set_facecolor(paper)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off'); ax.set_aspect('equal')
Y = lambda v: H - v
ax.text(8, Y(9), 'Symbolfamilien zur Auswahl', fontproperties=HAND, fontsize=20, va='center')
ax.text(8, Y(16), 'je Familie:  Form (groß)  ·  Druckgröße ×2 auf Papier  ·  Druckgröße ×2 auf Wiese mit Höhenlinie (zeigt die Freistellung)', fontsize=6.5, color='#666', va='center')
cols = [62, 112, 162]
for (f, lab), cx in zip(fams, cols):
    ax.text(cx, Y(24), lab, fontproperties=HAND, fontsize=13, ha='center', va='center', color='#9b3fb5')
for i, (k, name) in enumerate(KINDS):
    y = Y(34 + i * 11)
    ax.text(8, y, name, fontsize=8, va='center', color=ink)
    ax.plot([6, 204], [y - 5.5, y - 5.5], color='#e8e2d6', lw=0.4)
    for (f, _), cx in zip(fams, cols):
        col = brown if k == 'pit' else ink
        draw(ax, k, cx - 14, y, 1.0, col, f, size=4.5, paper=paper, knock=False)
        draw(ax, k, cx + 3, y, 1.0, col, f, size=2.0, paper=paper)
        ax.add_patch(plt.Rectangle((cx + 8, y - 3.6), 11, 7.2, fc=meadow, ec='none', zorder=1))
        xx = np.linspace(cx + 8, cx + 19, 30); ax.plot(xx, y - 1.2 + 1.6 * np.sin((xx - cx) * 0.6), color=brown, lw=0.9, zorder=2)
        draw(ax, k, cx + 13.5, y, 1.0, col, f, size=2.0, paper=meadow)
plt.savefig(BASE + '/out/symbol_families.png', dpi=200, facecolor=paper)
print('ok')
