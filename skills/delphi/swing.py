# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.3.5"]
# ///
import json, time, urllib.request, datetime as dt
from concurrent.futures import ThreadPoolExecutor
import numpy as np

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"}
F = "https://fapi.binance.com"


def get(u):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20) as r:
        return json.load(r)


def sq():
    p = get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD")[0]["spreadProfilePrices"][0]
    return p["bid"], p["ask"], float(get(f"{F}/fapi/v1/premiumIndex?symbol=XAUUSDT")["indexPrice"])


now = int(time.time() * 1000)
t0s = list(range(now - 60 * 86400000, now, 1500 * 60000))
with ThreadPoolExecutor(16) as ex:
    pg = list(ex.map(lambda s: get(f"{F}/fapi/v1/indexPriceKlines?pair=XAUUSDT&interval=1m&startTime={s}&limit=1500"), t0s))
    f_perp = ex.submit(get, f"{F}/fapi/v1/klines?symbol=XAUUSDT&interval=1m&limit=60")
    f_agg = ex.submit(get, f"{F}/fapi/v1/aggTrades?symbol=XAUUSDT&limit=1000")
    f_dp = ex.submit(get, f"{F}/fapi/v1/depth?symbol=XAUUSDT&limit=500")
    f_ls = ex.submit(get, f"{F}/futures/data/globalLongShortAccountRatio?symbol=XAUUSDT&period=5m&limit=8")
    f_oi = ex.submit(get, f"{F}/futures/data/openInterestHist?symbol=XAUUSDT&period=5m&limit=14")
    f_sq = ex.submit(sq)
d = {k[0]: k for p in pg for k in p}
ks = [d[k] for k in sorted(d)]
T = np.array([k[0] for k in ks]) // 1000
O, H, L, C = (np.array([float(k[j]) for k in ks]) for j in (1, 2, 3, 4))
N = len(C)
hr = (T % 86400) // 3600
bid, ask, ixp = f_sq.result()
off = ixp - (bid + ask) / 2
S = lambda x: x - off  # index -> spot terms
print(f"now {dt.datetime.now(dt.UTC):%H:%M:%S}Z spot bid {bid:.2f} ask {ask:.2f} index {ixp:.2f} offset {off:.2f}  (all levels below in SPOT terms)")
ts = lambda i: dt.datetime.fromtimestamp(int(T[i]), dt.UTC).strftime("%H:%M")
perp = {k[0] // 1000: k for k in f_perp.result()}
print("last 12 bars:")
for i in range(N - 12, N):
    p = perp.get(int(T[i])); v = float(p[5]) if p else 0; tb = float(p[9]) / v if p and v else 0
    print(f"  {ts(i)} O {S(O[i]):.2f} H {S(H[i]):.2f} L {S(L[i]):.2f} C {S(C[i]):.2f} v {v:.0f} tb {tb:.2f}")
day = T >= (T[-1] // 86400) * 86400
roll = T >= ((T[-1] - 22 * 3600) // 86400) * 86400 + 22 * 3600
h1 = slice(N - 60, N)
print(f"UTC-day hi {S(H[day].max()):.2f} lo {S(L[day].min()):.2f} | since 22Z hi {S(H[roll].max()):.2f} lo {S(L[roll].min()):.2f} | last60 hi {S(H[h1].max()):.2f} lo {S(L[h1].min()):.2f} | last 240 lo {S(L[-240:].min()):.2f}")
pc = np.roll(C, 1); pc[0] = C[0]
TR = np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))
dd = np.diff(C[-200:])
rsi = lambda n: 100 * np.where(dd[-n:] > 0, dd[-n:], 0).sum() / max(abs(dd[-n:]).sum(), 1e-9)
print(f"ATR14 {TR[-15:-1].mean():.2f} ATR60 {TR[-61:-1].mean():.2f} | cutler RSI7 {rsi(7):.0f} RSI14 {rsi(14):.0f} RSI60 {rsi(60):.0f} | chg 5m {C[-1]-C[-6]:+.2f} 15m {C[-1]-C[-16]:+.2f} 60m {C[-1]-C[-61]:+.2f} 240m {C[-1]-C[-241]:+.2f}")
ema = lambda n: np.average(C[-4 * n:], weights=np.exp(np.arange(4 * n) / n * 1.0))
print(f"ema9 {S(ema(9)):.2f} ema21 {S(ema(21)):.2f} ema50 {S(ema(50)):.2f} ema200 {S(ema(200)):.2f}")


def states(thr):
    dr = np.zeros(N, np.int8); st = np.zeros(N); ex_ = np.zeros(N); exi = np.zeros(N, int); lid = np.zeros(N, int)
    legs = []
    D, mx, mxi, mn, mni, sp, si, k = 0, H[0], 0, L[0], 0, 0.0, 0, 0
    for i in range(1, N):
        if D == 0:
            if H[i] > mx: mx, mxi = H[i], i
            if L[i] < mn: mn, mni = L[i], i
            if mx - mn >= thr:
                if mxi < mni: D, sp, si = -1, mx, mxi
                else: D, sp, si = 1, mn, mni
        elif D == 1:
            if H[i] > mx: mx, mxi = H[i], i
            elif mx - L[i] >= thr:
                legs.append((si, sp, mxi, mx, 1)); k += 1; D, sp, si, mn, mni = -1, mx, mxi, L[i], i
        else:
            if L[i] < mn: mn, mni = L[i], i
            elif H[i] - mn >= thr:
                legs.append((si, sp, mni, mn, -1)); k += 1; D, sp, si, mx, mxi = 1, mn, mni, H[i], i
        dr[i] = D; st[i] = sp; lid[i] = k
        ex_[i], exi[i] = (mx, mxi) if D == 1 else (mn, mni)
    return dr, st, ex_, exi, lid, legs


def fp(i, up, dn, hz=90):
    for j in range(i + 1, min(N, i + 1 + hz)):
        u, w = H[j] >= up, L[j] <= dn
        if u and w: return 0, j - i
        if u: return 1, j - i
        if w: return -1, j - i
    return 0, hz


i0 = N - 1
for thr in (3.0, 5.0, 8.0):
    dr, st, ex_, exi, lid, legs = states(thr)
    D0 = int(dr[i0]); s0 = abs(ex_[i0] - st[i0]); r0 = abs(ex_[i0] - C[i0]); age = i0 - exi[i0]
    print(f"\n== zigzag ${thr:g}: pivots " + " ".join(f"{'H' if g[4]==1 else 'L'}{S(g[3]):.2f}@{ts(g[2])}" for g in legs[-5:]))
    print(f" now {'UP' if D0 > 0 else 'DOWN'} leg from {S(st[i0]):.2f}, ext {S(ex_[i0]):.2f} ({age}m ago), size {s0:.2f}, pullback {r0:.2f}; reversal confirms at {S(ex_[i0] - D0 * thr):.2f}")
    sel, seen = [], set()
    for i in range(1500, N - 91):
        if dr[i] != D0 or lid[i] in seen: continue
        s = abs(ex_[i] - st[i]); r = abs(ex_[i] - C[i])
        if 0.7 * s0 <= s <= 1.5 * s0 and 0.6 * r0 - 0.2 <= r <= 1.4 * r0 + 0.3 and abs((i - exi[i]) - age) <= max(3, age):
            sel.append(i); seen.add(lid[i])
    sel = np.array(sel)
    if len(sel) < 20:
        print(f" analogs n={len(sel)}: too few"); continue
    cont = []; f = {2.5: [], 5.0: []}; mfe = []; mae = []
    for i in sel:
        e = ex_[i]
        res = fp(i, e + 1.0, e - thr)[0] if D0 > 0 else fp(i, e + thr, e - 1.0)[0]
        cont.append(res == D0)
        for X in f: f[X].append(fp(i, C[i] + X, C[i] - X)[0])
        w = slice(i + 1, i + 31)
        mfe.append(H[w].max() - C[i]); mae.append(C[i] - L[w].min())
    cont = np.array(cont); lon = np.abs(hr[sel] - hr[i0]) <= 1
    out = f" analogs n={len(sel)}: P(leg makes new extreme by $1 before reversal) {cont.mean():.2f}"
    if lon.sum() >= 10: out += f" | same hour±1 n={lon.sum()} {cont[lon].mean():.2f}"
    print(out)
    for X, v in f.items():
        v = np.array(v); k = v != 0
        print(f"  P(+${X:g} before -${X:g}) {(v[k]==1).mean():.2f} (n {k.sum()})" + (f" | same hour {(v[k&lon]==1).mean():.2f} (n {(k&lon).sum()})" if (k & lon).sum() >= 10 else ""))
    print(f"  next 30m: up excursion med {np.median(mfe):.2f} p75 {np.percentile(mfe,75):.2f}; down excursion med {np.median(mae):.2f} p75 {np.percentile(mae,75):.2f}")

# hour-of-day seasonality for next 30/60 min, last 60d, at this minute of day
m0 = (T[i0] % 86400) // 60
idx = np.where(((T % 86400) // 60 == m0) & (np.arange(N) < N - 61) & (np.arange(N) > 300))[0]
a = np.array([(C[i + 15] - C[i], C[i + 30] - C[i], C[i + 60] - C[i], C[i] - C[i - 240], H[i + 1:i + 31].max() - C[i], C[i] - L[i + 1:i + 31].min()) for i in idx if H[i - 5:i + 1].max() > L[i - 5:i + 1].min()])
print(f"\nSEASONAL at {ts(i0)}Z, n={len(a)} days: next15 mean {a[:,0].mean():+.2f} up% {(a[:,0]>0).mean():.2f}; next30 mean {a[:,1].mean():+.2f} up% {(a[:,1]>0).mean():.2f}; next60 mean {a[:,2].mean():+.2f} up% {(a[:,2]>0).mean():.2f}; |next60| mean {abs(a[:,2]).mean():.2f}")
dn = a[a[:, 3] < -10]
if len(dn) >= 8: print(f"  days with prior 4h < -$10 (n={len(dn)}): next30 mean {dn[:,1].mean():+.2f} up% {(dn[:,1]>0).mean():.2f}; next60 mean {dn[:,2].mean():+.2f} up% {(dn[:,2]>0).mean():.2f}; 30m up-exc med {np.median(dn[:,4]):.2f} down-exc med {np.median(dn[:,5]):.2f}")

print("\nMICRO (perp):")
dp = f_dp.result(); b = np.array(dp["bids"], float); a_ = np.array(dp["asks"], float); mid = (b[0, 0] + a_[0, 0]) / 2; po = mid - (bid + ask) / 2
for bp in (3, 10, 25):
    bb = b[b[:, 0] >= mid * (1 - bp / 1e4), 1].sum(); aa = a_[a_[:, 0] <= mid * (1 + bp / 1e4), 1].sum()
    print(f"  book ±{bp}bp bids {bb:.0f} asks {aa:.0f} imb {(bb-aa)/(bb+aa):+.2f}")
big = lambda s: sorted(s, key=lambda r: -r[1])[:4]
print("  big bids (spot terms)", [(round(float(p - po), 1), round(float(q))) for p, q in big(b[b[:, 0] >= mid - 15])], "big asks", [(round(float(p - po), 1), round(float(q))) for p, q in big(a_[a_[:, 0] <= mid + 15])])
ag = f_agg.result(); tn = ag[-1]["T"]
for w in (30, 60, 180):
    s = [x for x in ag if x["T"] >= tn - w * 1000]
    bu = sum(float(x["q"]) for x in s if not x["m"]); se = sum(float(x["q"]) for x in s if x["m"])
    print(f"  flow {w}s buy {bu:.0f} sell {se:.0f} delta {bu-se:+.0f}" + (" (sample capped)" if s[0] is ag[0] else ""))
oi = [float(x["sumOpenInterest"]) for x in f_oi.result()]
print(f"  OI chg 15m {(oi[-1]/oi[-4]-1)*100:+.2f}% 1h {(oi[-1]/oi[-13]-1)*100:+.2f}% | L/S accts {[round(float(x['longShortRatio']),2) for x in f_ls.result()[-5:]]}")
