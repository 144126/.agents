import sys, math, numpy as np
from fast import *
asset, win = (sys.argv[1:3] + ["btc", "5m"][len(sys.argv[1:3]):]) if len(sys.argv) > 1 else ("btc", "5m")
sym = {"btc": "BTCUSDT", "eth": "ETHUSDT", "sol": "SOLUSDT", "xrp": "XRPUSDT"}[asset]
W = {"5m": 300, "15m": 900}[win]
tp = Tape(asset, win, W); md = Model(sym)
split = float(sys.argv[3]) if len(sys.argv) > 3 else np.median(tp.Ts)
print(f"{asset} {win}: windows {len(tp.Ts)} prints {len(tp.pr)} days {(tp.Ts[-1]-tp.Ts[0])/86400:.1f} split {split:.0f}")
pu = md.fair_up(tp.T, tp.ts - 1, W=W); P = np.where(tp.sd == 0, pu, 1 - pu)
E = P - tp.pr - fee(tp.pr)
def bot(lo, hi, tau, m=None, lag=0, slip=0.0, kmin=3, EE=E):
    idx = tp.first((tp.pr >= lo) & (tp.pr < hi) & (tp.k <= tau) & (tp.k >= kmin))
    if m is not None: idx = idx[EE[idx] >= m]
    idx, fp = tp.fill(idx, lag)
    f, pn = tp.pnl(idx, fp, slip)
    return idx, f, pn
def show(lbl, *a, **k): print(f"{lbl:<44}", stats(tp, *bot(*a, **k), split))
print("\n== current fav rule (81-99c, <=90s), A = first half, B = second half")
for m in (None, 0.02):
    for lag, slip in ((0, 0), (0, 0.01), (2, 0.01)):
        show(f" filter={m} lag={lag} slip={slip}", 0.81, 0.99, 90, m, lag, slip)
# how much did the old side-ordered pick differ?
msk = (tp.pr >= 0.81) & (tp.pr < 0.99) & (tp.k <= 90) & (tp.k >= 3)
new = tp.first(msk)
ix = np.where(msk)[0]; o = np.lexsort((tp.ts[ix], tp.sd[ix], tp.wi[ix])); ix = ix[o]; old = ix[np.unique(tp.wi[ix], return_index=True)[1]]
print(f" bug check: windows where old pick != new pick: {np.sum(old != new)} of {len(new)}; old win {tp.won[old].mean()*100:.1f}% new win {tp.won[new].mean()*100:.1f}%")
print("\n== plain fav grid (no filter, lag 2, slip 1c): roi by tau x lo")
for tau in (15, 30, 45, 60, 90, 120, 180):
    for lo in (0.70, 0.75, 0.81, 0.85, 0.90, 0.95):
        show(f" tau {tau:3d} lo {lo:.2f}", lo, 0.995, tau, None, 2, 0.01)
print("\n== late rule (35-81c, <=60s, model edge >= m), lag 2 slip 1c, model variants")
for mult, sb in ((1.0, 0.0), (1.0, 0.00039), (0.905, 0.00039)):
    pu2 = md.fair_up(tp.T, tp.ts - 1, mult, sb, W); P2 = np.where(tp.sd == 0, pu2, 1 - pu2); E2 = P2 - tp.pr - fee(tp.pr)
    for m in (0.02, 0.05, 0.10):
        show(f" mult {mult} sb {sb} m {m}", 0.35, 0.81, 60, m, 2, 0.01, EE=E2)
