import numpy as np, glob, os, json, gzip, math
from scipy.special import ndtr
D = os.environ.get("DELPHI_RESEARCH", os.path.expanduser("~/.local/share/delphi/research"))
def load_px(sym):
    f = glob.glob(f"{D}/px_{sym}_*.bin")[0]
    t0 = int(f.rsplit("_", 1)[1].split(".")[0])
    px = np.fromfile(f, dtype=np.float64)
    ok = ~np.isnan(px); idx = np.where(ok, np.arange(len(px)), 0); np.maximum.accumulate(idx, out=idx)
    LP = np.log(px[idx]); r = np.diff(LP, prepend=LP[0])
    return t0, LP, np.concatenate([[0], np.cumsum(r * r)]), np.concatenate([[0], np.cumsum(LP)])
class Model:
    def __init__(s, sym): s.t0, s.LP, s.C2, s.CL = load_px(sym)
    def I(s, x): return np.asarray(x, dtype=np.int64) - s.t0
    def fair_up(s, T, now, mult=1.0, sb=0.0, W=300):
        """delphi p_fav (TWAP60 end), info up to the close of second `now`, strike = binance close at T"""
        I = s.I; T = np.asarray(T, dtype=np.int64); now = np.asarray(now, dtype=np.int64)
        y0 = s.LP[I(T)]; yt = s.LP[I(now)] - y0
        sg = np.sqrt((s.C2[I(now) + 1] - s.C2[I(now) + 1 - 600]) / 600) * mult
        tau = (T + W - now).astype(float)
        a = T + W - 59; n = np.maximum(now - a + 1, 0)
        sreal = np.where(n > 0, s.CL[I(now) + 1] - s.CL[np.minimum(I(a), I(now) + 1)] - n * y0, 0.0)
        mean = np.where(tau >= 60, yt, (np.where(n > 0, sreal / np.maximum(n, 1), 0) * (60 - tau) + tau * yt) / 60)
        var = np.where(tau >= 60, sg ** 2 * (tau - 60 + 20.3), sg ** 2 * tau * (tau + 1) * (2 * tau + 1) / (6 * 3600)) + sb * sb
        return ndtr(mean / np.sqrt(np.maximum(var, 1e-30)))
def fee(p): return 0.07 * p * (1 - p)
class Tape:
    """BUY prints of one asset/window, rows in TIME order within each window (both sides mixed)"""
    def __init__(s, asset, win, W=300, kmin=1):
        rows, Ts, up = [], [], []
        for f in sorted(glob.glob(f"{D}/tape_{asset}_{win}_*.jsonl.gz")):
            for l in gzip.open(f, "rt"):
                w = json.loads(l)
                if not w["c"] or w["op"] not in ('["1", "0"]', '["0", "1"]'): continue
                j = len(Ts); Ts.append(w["T"]); up.append(w["op"] == '["1", "0"]')
                rows += [(j, x[0], x[1], x[2], x[3]) for x in w["tr"] if w["T"] < x[0] <= w["T"] + W - kmin]
        s.Ts, s.up, s.W = np.array(Ts), np.array(up), W
        a = np.array(rows, dtype=np.float64); del rows
        o = np.lexsort((a[:, 2], a[:, 1], a[:, 0])); a = a[o]          # window, then time, then side
        s.wi, s.ts, s.sd, s.pr, s.sz = a[:, 0].astype(np.int64), a[:, 1].astype(np.int64), a[:, 2].astype(np.int64), a[:, 3], a[:, 4]
        s.T = s.Ts[s.wi]; s.k = s.T + W - s.ts
        s.won = np.where(s.sd == 0, s.up[s.wi], ~s.up[s.wi])
        s.key = s.wi * 2 + s.sd
        s.o2 = np.lexsort((s.ts, s.key)); s.c2 = s.key[s.o2] * 10**10 + s.ts[s.o2]
    def first(s, msk):
        """earliest-in-time row per window among rows where msk is true"""
        idx = np.where(msk)[0]
        return idx[np.unique(s.wi[idx], return_index=True)[1]]
    def fill(s, idx, lag, cap=0.02, within=10):
        """price we would get: next print on the same window+side at >= ts+lag (within `within` s) priced <= signal + cap"""
        if lag == 0: return idx, s.pr[idx]
        j = np.minimum(np.searchsorted(s.c2, s.key[idx] * 10**10 + s.ts[idx] + lag), len(s.c2) - 1); g = s.o2[j]
        ok = (s.key[g] == s.key[idx]) & (s.ts[g] >= s.ts[idx] + lag) & (s.ts[g] <= s.ts[idx] + lag + within) & (s.pr[g] <= s.pr[idx] + cap)
        return idx[ok], s.pr[g[ok]]
    def pnl(s, idx, fillp, slip=0.0):
        f = np.minimum(fillp + slip, 0.995)
        return f, np.where(s.won[idx], 1 - f, -f) - fee(f)
def stats(tp, idx, f, pn, split):
    out = []
    for nm, m in (("A", tp.Ts[tp.wi[idx]] < split), ("B", tp.Ts[tp.wi[idx]] >= split)):
        n = int(m.sum())
        if n < 5: out.append(f"{nm} n={n}"); continue
        x = pn[m]; mu = x.mean(); se = x.std(ddof=1) / math.sqrt(n)
        out.append(f"{nm} n={n:4d} win={tp.won[idx][m].mean()*100:5.1f}% p={f[m].mean():.3f} roi={100*x.sum()/f[m].sum():+6.2f}% t={mu/se:+5.2f}")
    return "  ".join(out)
