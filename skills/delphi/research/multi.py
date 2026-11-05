import sys, numpy as np
from fast import *
asset, win = sys.argv[1], sys.argv[2]; W = {"5m": 300, "15m": 900}[win]
tp = Tape(asset, win, W); split = np.median(tp.Ts)
empty = len(tp.Ts) - len(np.unique(tp.wi))
print(f"{asset} {win}: windows {len(tp.Ts)} (no prints: {empty}) prints {len(tp.pr)} days {(tp.Ts[-1]-tp.Ts[0])/86400:.1f}")
for tau in (15, 30, 45, 60, 90):
    for lo, hi in ((0.85, 0.95), (0.81, 0.99), (0.90, 0.99)):
        idx = tp.first((tp.pr >= lo) & (tp.pr < hi) & (tp.k <= tau) & (tp.k >= 3))
        for lag, slip in ((0, 0.0), (2, 0.01)):
            j, fp = tp.fill(idx, lag); f, pn = tp.pnl(j, fp, slip)
            print(f" tau {tau:3d} {lo:.2f}-{hi:.2f} lag{lag}", stats(tp, j, f, pn, split))
