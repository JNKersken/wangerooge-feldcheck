import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from symbols2 import draw, KINDS, NEW_KINDS, draw_dots
HAND = fm.FontProperties(fname=BASE + '/fonts/Caveat-Bold.ttf')
ink, paper, meadow, brown, red = '#1d1d1f', '#fffdf7', '#fbefb8', '#b0662a', '#8e1b1b'
K = KINDS + NEW_KINDS
W, H = 210, 20 + 9 * ((len(K) + 1) // 2)
fig = plt.figure(figsize=(W / 25.4, H / 25.4)); fig.patch.set_facecolor(paper)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off'); ax.set_aspect('equal')
ax.text(8, H - 9, 'Familie B – Silhouette (überarbeitet)', fontproperties=HAND, fontsize=17, va='center')
for i, (k, name) in enumerate(K):
    col_i, row = divmod(i, (len(K) + 1) // 2); x0 = 8 + col_i * 102; y = H - 22 - row * 9
    ax.text(x0, y, name, fontsize=7.5, va='center', color=ink)
    draw(ax, k, x0 + 44, y, 1.0, brown if k == 'pit' else ink, 'B', size=3.6, paper=paper)
    ax.add_patch(plt.Rectangle((x0 + 55, y - 3.8), 30, 7.6, fc=meadow, ec='none', zorder=1))
    xx = np.linspace(x0 + 55, x0 + 85, 50); ax.plot(xx, y - 0.4 + 1.8 * np.sin((xx - x0) * 0.45), color=brown, lw=0.9, zorder=2)
    ax.plot([x0 + 55, x0 + 85], [y + 1.4, y - 1.6], color=ink, lw=1.3, zorder=2)
    draw(ax, k, x0 + 63, y, 1.0, brown if k == 'pit' else ink, 'B', size=2.0, paper=meadow)
    draw(ax, k, x0 + 76, y, 1.0, '#9b9b9b', 'B', size=2.0, paper=meadow, gray=True)
    if k == 'bench': draw_dots(ax, x0 + 64.9, y, 4, 2.0, red, paper=meadow)
plt.savefig(BASE + '/out/symbol_B.png', dpi=200, facecolor=paper); print('ok')
