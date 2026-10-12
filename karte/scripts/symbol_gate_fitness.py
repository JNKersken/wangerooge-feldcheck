"""Proposal sheet: gate + fitness alternatives next to the bench, true size on a map snippet + 6x enlarged."""
import os as _os, sys as _sys; _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__))); from base import BASE
import sys; None
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
import symbols2 as S2
FD = BASE + '/fonts/'
fm.fontManager.addfont(FD + 'Caveat-Bold.ttf'); fm.fontManager.addfont(FD + 'Caveat-Medium.ttf')
H = fm.FontProperties(fname=FD + 'Caveat-Bold.ttf'); HM = fm.FontProperties(fname=FD + 'Caveat-Medium.ttf')
INK, PAPER, BROWN = '#1d1d1f', '#fffdf7', '#b0662a'
G = [('gate', None, 'Tor heute'), ('gate', 'gatter', 'G1 Gatter'), ('gate', 'luecke', 'G2 Zaunlücke'), ('gate', 'schranke', 'G3 Schranke'), ('gate', 'bogen', 'G4 Torbogen')]
F = [('fitness', None, 'Fitness heute'), ('fitness', 'kettle', 'F1 Kettlebell'), ('fitness', 'diag', 'F2 Hantel schräg'), ('fitness', 'discs', 'F3 Hantelscheiben'), ('fitness', 'figur', 'F4 Hampelmann')]
fig = plt.figure(figsize=(200 / 25.4, 150 / 25.4)); fig.patch.set_facecolor(PAPER)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 200); ax.set_ylim(0, 150); ax.axis('off')
ax.text(6, 143, 'Tor / Durchlass und Fitnessgerät – Vorschläge (Stil B, neben der Bank)', fontproperties=H, fontsize=13, color=INK)
ax.text(6, 136.5, 'oben 6-fach vergrößert · darunter Kartenausschnitt 3-fach (Pfad, Höhenlinie, Bank, rechts überlappend)', fontproperties=HM, fontsize=9, color='#666')
for row, (lst, y0) in enumerate(((G, 108), (F, 48))):
    for i, (k, v, name) in enumerate(lst):
        x = 22 + i * 38
        S2.draw(ax, 'bench', x - 9, y0 + 12, 1.0, INK, size=6.0, paper=PAPER)
        S2.draw(ax, k, x + 6, y0 + 12, 1.0, INK, size=6.0, paper=PAPER, variant=v)
        ax.text(x - 1, y0 + 1, name, fontproperties=H, fontsize=10, color=INK if v else '#777', ha='center')
        # true size snippet: path line + contour behind, bench and candidate 2.5 mm apart
        yy = y0 - 16; Z = 3.0   # map snippet, everything 3x
        ax.plot([x - 16, x + 16], [yy - 4, yy + 4], color=INK, lw=0.6 * Z, dashes=(1.8, 1.4))
        ax.plot([x - 16, x + 16], [yy + 5.5, yy + 1.5], color=BROWN, lw=0.3 * Z)
        S2.draw(ax, 'bench', x - 9, yy - 1.5, 1.0, INK, size=Z, paper=PAPER)
        S2.draw(ax, k, x - 1.5, yy + 0.8, 1.0, INK, size=Z, paper=PAPER, variant=v)
        S2.draw(ax, 'bench', x + 7, yy - 1.0, 1.0, INK, size=Z, paper=PAPER)
        S2.draw(ax, k, x + 10.2, yy + 1.6, 1.0, INK, size=Z, paper=PAPER, variant=v)   # overlapping case
fig.savefig(sys.argv[1], dpi=int(sys.argv[2]) if len(sys.argv) > 2 else 300, facecolor=PAPER)
