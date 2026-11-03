# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.3.5", "ta-lib==0.8.3", "websockets==15.0.1"]
# ///
import argparse
import csv
import datetime as dt
import io
import json
import math
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from importlib.util import module_from_spec, spec_from_file_location
from zoneinfo import ZoneInfo

import numpy as np
import talib

ZIP = "https://data.binance.vision/data/spot/monthly/klines/PAXGUSDT/15m/PAXGUSDT-15m-{y}-{m:02d}.zip"
API = "https://api.binance.com/api/v3/klines"
DELPHI = "/home/ed/.agents/skills/delphi/delphi.py"
LDN, NYC = ZoneInfo("Europe/London"), ZoneInfo("America/New_York")
DAY = 86400
LEG = 0.11  # $/oz per leg, 0.22 round trip
MULT = 3  # cost multiplier for a leg inside the release window
WINDOW = 900  # +-15 min, seconds
SWAP = 0.07  # annual on notional, longs only; shorts 0%
ROLL = 22 * 3600  # UTC swap rollover
TRAIN = 0.70
ALPHA = 0.05
VOL_T = 0.10  # TSMOM target vol, annual
MIN_N = 30  # below this a t-stat has no power


def months():
    now = dt.datetime.now(dt.UTC)
    y, m, out = 2020, 8, []
    while (y, m) <= (now.year, now.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def api_rows(t0, t1):
    out = []
    while t0 < t1:
        url = f"{API}?symbol=PAXGUSDT&interval=15m&startTime={t0}&endTime={t1}&limit=1000"
        with urllib.request.urlopen(url, timeout=30) as r:
            page = json.load(r)
        if not page:
            break
        out += page
        t0 = page[-1][0] + 1
    return out


def month_rows(y, m):
    try:
        with urllib.request.urlopen(ZIP.format(y=y, m=m), timeout=60) as r:
            raw = r.read()
    except urllib.error.HTTPError:
        lo = dt.datetime(y, m, 1, tzinfo=dt.UTC)
        hi = dt.datetime(y + (m == 12), m % 12 + 1, 1, tzinfo=dt.UTC)
        return api_rows(int(lo.timestamp() * 1000), int(hi.timestamp() * 1000))
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        text = z.read(z.namelist()[0]).decode()
    return [row for row in csv.reader(io.StringIO(text)) if row and row[0].isdigit()]


def load_15m():
    with ThreadPoolExecutor(8) as ex:
        parts = list(ex.map(lambda ym: month_rows(*ym), months()))
    a = np.array([r[:10] for p in parts for r in p], dtype=float)
    ms = np.where(a[:, 0] > 1e14, a[:, 0] / 1000, a[:, 0])  # 2025+ files are microseconds
    order = np.argsort(ms, kind="stable")
    a, ms = a[order], ms[order]
    _, i = np.unique(ms, return_index=True)
    a, T = a[i], ms[i] / 1000
    k = (T // DAY + 3) % 7 < 5  # Mon-Fri only, Thursday epoch offset
    return {"T": T[k], "o": a[k, 1], "h": a[k, 2], "l": a[k, 3], "c": a[k, 4], "v": a[k, 5], "tb": a[k, 9]}


def agg(b, dur):
    k = np.floor(b["T"] / dur)
    i = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
    last = np.r_[i[1:] - 1, len(k) - 1]
    return {
        "T": k[i] * dur, "o": b["o"][i], "h": np.maximum.reduceat(b["h"], i),
        "l": np.minimum.reduceat(b["l"], i), "c": b["c"][last],
        "v": np.add.reduceat(b["v"], i), "tb": np.add.reduceat(b["tb"], i),
    }


def releases():
    out = []
    for y in range(2020, 2028):
        for m in range(1, 13):
            d = dt.date(y, m, 1)
            while d.weekday() != 4:
                d += dt.timedelta(1)
            out.append(d)
            d = dt.date(y, m, 12)
            while d.weekday() > 4:
                d += dt.timedelta(1)
            out.append(d)
    return np.array(sorted(dt.datetime(d.year, d.month, d.day, 8, 30, tzinfo=NYC).timestamp() for d in out))


REL = releases()  # rough mask: first Friday (NFP) and ~12th weekday (CPI-like), 08:30 ET
DAYS = []
_d = dt.date(2020, 8, 1)
while _d < dt.date(2027, 1, 1):
    if _d.weekday() < 5:
        DAYS.append(_d)
    _d += dt.timedelta(1)
OL = np.array([dt.datetime(d.year, d.month, d.day, 8, 0, tzinfo=LDN).timestamp() for d in DAYS])
NY = np.array([dt.datetime(d.year, d.month, d.day, 17, 0, tzinfo=NYC).timestamp() for d in DAYS])


def hot(t):
    i = np.clip(np.searchsorted(REL, t), 1, len(REL) - 1)
    return np.minimum(np.abs(REL[i] - t), np.abs(REL[i - 1] - t)) <= WINDOW


def nights(t):
    return np.floor((t - ROLL) / DAY)


def evaluate(b, P, lo, hi):
    # P[t] is the signed weight held from open[t] to open[t+1]
    T, o = b["T"], b["o"]
    Pb = P[:-1]
    r = Pb * (o[1:] / o[:-1] - 1)
    dP = np.abs(np.diff(P, prepend=0.0))[:-1]
    r -= dP * LEG * np.where(hot(T[:-1]), MULT, 1) / o[:-1]
    r -= np.maximum(Pb, 0) * SWAP / 365 * (nights(T[1:]) - nights(T[:-1]))
    d = np.sign(P)
    cp = np.flatnonzero(np.diff(d, prepend=0.0) != 0)
    k = np.flatnonzero(d[cp] != 0)
    en = cp[k]
    ex = np.where(k + 1 < len(cp), cp[np.minimum(k + 1, len(cp) - 1)], len(T) - 1)
    ep, xp, dr = o[en], o[ex], d[en]
    legs = LEG * (np.where(hot(T[en]), MULT, 1) + np.where(hot(T[ex]), MULT, 1))
    sw = (dr > 0) * ep * SWAP / 365 * (nights(T[ex]) - nights(T[en]))
    net = dr * (xp - ep) - legs - sw
    m = (T[:-1] >= lo) & (T[:-1] < hi)
    tm = (T[en] >= lo) & (T[en] < hi)
    rp, tp = r[m], T[:-1][m]
    yrs = max((tp[-1] - tp[0]) / (365.25 * DAY), 1e-9)
    eq = np.cumprod(1 + rp)
    sd = rp.std(ddof=1)
    nt, bt = net[tm], net[tm] / ep[tm] * 1e4
    n = len(nt)
    tt = bt.mean() / (bt.std(ddof=1) / math.sqrt(n)) if n > 1 and bt.std(ddof=1) > 0 else 0.0
    cost = (legs + sw)[tm].sum()
    return {  # n trades, h hit, e exp $/oz, b exp bps, a annual, s sharpe, d max dd, w swap share of cost, t t-stat, p p-value
        "n": n,
        "h": float((nt > 0).mean()) if n else 0.0,
        "e": float(nt.mean()) if n else 0.0,
        "b": float(bt.mean()) if n else 0.0,
        "a": float(eq[-1] ** (1 / yrs) - 1),
        "s": float(rp.mean() / sd * math.sqrt(len(rp) / yrs)) if sd > 0 else 0.0,
        "d": float((eq / np.maximum.accumulate(eq) - 1).min()),
        "w": float(sw[tm].sum() / cost) if cost > 0 else 0.0,
        "t": float(tt),
        "p": math.erfc(abs(tt) / math.sqrt(2)),
    }


def lagged(x, k):
    return np.r_[np.full(k, x[0]), x[:-k]]


def shift(s):
    return np.r_[0.0, s[:-1]]


def tsmom(d, lb):
    lc = np.log(d["c"])
    if lb:
        s = np.sign(lc - lagged(lc, lb))
    else:
        s = np.sign(sum(np.sign(lc - lagged(lc, L)) for L in (21, 63, 126, 252)))
    vol = np.nan_to_num(talib.STDDEV(np.diff(lc, prepend=lc[0]), 20))
    w = np.minimum(VOL_T / np.maximum(vol * math.sqrt(252), 1e-9), 2) * (vol > 0)
    idx = np.arange(len(lc)) // 21 * 21  # monthly rebalance, held 21 bars
    return shift(s[idx] * w[idx])


def donch(d, n, k):
    h, l, c = d["h"], d["l"], d["c"]
    hi, lo = lagged(talib.MAX(h, n), 1), lagged(talib.MIN(l, n), 1)
    atr = talib.ATR(h, l, c, 14)
    s = np.zeros(len(c))
    pos, stop = 0.0, 0.0
    for t in range(len(c)):
        if pos == 0:
            if c[t] > hi[t]:
                pos, stop = 1.0, c[t] - k * atr[t]
            elif c[t] < lo[t]:
                pos, stop = -1.0, c[t] + k * atr[t]
        elif (pos > 0 and (c[t] < lo[t] or c[t] < stop)) or (pos < 0 and (c[t] > hi[t] or c[t] > stop)):
            pos = 0.0
        s[t] = pos
    return shift(s)


def ma(d):
    c = d["c"]
    return shift(np.nan_to_num(np.sign(talib.SMA(c, 50) - talib.SMA(c, 200))))


def held(T, starts, ends, dirs):
    i = np.maximum(np.searchsorted(starts, T, side="right") - 1, 0)
    return np.where((T >= starts[i]) & (T < ends[i]), dirs[i], 0.0)


def news(b, dirn):
    T = b["T"]
    i = np.minimum(np.searchsorted(T, REL), len(T) - 1)
    sg = np.sign(b["c"][i] - b["o"][i]) * (T[i] == REL)
    k = sg != 0
    s = REL[k] + WINDOW
    return held(T, s, s + 3600, dirn * sg[k])


def load_delphi():
    spec = spec_from_file_location("delphi", DELPHI)
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).date().isoformat()


def run():
    b15 = load_15m()
    b1h, bd = agg(b15, 3600), agg(b15, DAY)
    T = b15["T"]
    t0, t1 = T[0], T[-1] + 1
    cut = t0 + TRAIN * (t1 - t0)
    res = []

    def add(group, name, b, P, k, sb):
        d = k * talib.ATR(sb["h"], sb["l"], sb["c"], 14)[-1]
        res.append({"g": group, "v": name, "d": float(d), "tr": evaluate(b, P, t0, cut), "ho": evaluate(b, P, cut, t1)})

    for lb in (21, 63, 126, 252, 0):
        add("TSMOM", f"{lb}d" if lb else "composite", bd, tsmom(bd, lb), 2, bd)
    for n in (20, 50, 100):
        for k in (2, 3):
            add("Donchian", f"N={n} stop={k}xATR", bd, donch(bd, n, k), k, bd)
    add("MA 50/200", "sma50 vs sma200", bd, ma(bd), 2, bd)
    add("LDN->NY long", "08:00 LDN to 17:00 NY", b15, held(T, OL, NY, np.ones(len(OL))), 2, b1h)
    add("LDN->NY short", "08:00 LDN to 17:00 NY", b15, held(T, OL, NY, -np.ones(len(OL))), 2, b1h)
    add("NY->LDN long", "17:00 NY to 08:00 LDN", b15, held(T, NY[:-1], OL[1:], np.ones(len(OL) - 1)), 2, b1h)
    add("NY->LDN short", "17:00 NY to 08:00 LDN", b15, held(T, NY[:-1], OL[1:], -np.ones(len(OL) - 1)), 2, b1h)
    add("news cont", "1h after release bar", b15, news(b15, 1), 2, b1h)
    add("news fade", "1h after release bar", b15, news(b15, -1), 2, b1h)
    for _, nm, a, ce in load_delphi().feats(b15):
        a = np.asarray(a, dtype=float)
        c0 = np.nanmedian(a[T < cut]) if ce is None else ce
        S = np.nan_to_num(np.sign(a - c0))
        for sg in (1, -1):
            add("delphi bench", f"{nm} {'trend' if sg > 0 else 'contra'}", b15, sg * shift(S), 2, b15)

    n_var = len(res)
    best = {}
    for r in res:
        if r["g"] not in best or r["tr"]["s"] > best[r["g"]]["tr"]["s"]:
            best[r["g"]] = r
    bh = {"g": "buy & hold", "v": "long, 1 entry", "d": 0.0, "tr": evaluate(bd, np.ones(len(bd["T"])), t0, cut), "ho": evaluate(bd, np.ones(len(bd["T"])), cut, t1)}
    rows = []
    for r in list(best.values()) + [bh]:
        pa = min(1.0, r["ho"]["p"] * n_var)
        rows.append({
            "g": r["g"], "v": r["v"], "emin": 100 * r["d"], "tr": r["tr"], "ho": r["ho"], "pa": pa,
            "ok": r["g"] != "buy & hold" and pa < ALPHA and r["ho"]["e"] > 0,
            "lp": r["ho"]["n"] < MIN_N,
        })
    meta = {"N": n_var, "from": iso(t0), "cut": iso(cut), "to": iso(t1), "bars15": len(T),
            "zero_vol": float((b15["v"] == 0).mean())}
    return meta, rows


def table(meta, rows):
    head = (f"{'candidate':<14}{'variant':<26}{'trBps':>7}{'n':>5}{'hit':>6}{'exp$':>8}{'bps':>8}"
            f"{'ann%':>8}{'shrp':>6}{'mdd%':>7}{'swap':>6}{'t':>6}{'pBonf':>7}{'pass':>5}{'minEq$':>8}")
    out = [f"PAXGUSDT 15m {meta['from']}..{meta['to']} split {meta['cut']} bars {meta['bars15']} "
           f"zero-vol {meta['zero_vol'] * 100:.1f}% N={meta['N']}", head]
    for r in rows:
        h, tr = r["ho"], r["tr"]
        em = "-" if r["g"] == "buy & hold" else f"{r['emin']:.0f}"
        out.append(f"{r['g']:<14}{r['v'][:25]:<26}{tr['b']:>7.1f}{h['n']:>5}{h['h'] * 100:>5.0f}%{h['e']:>8.2f}"
                   f"{h['b']:>8.1f}{h['a'] * 100:>8.1f}{h['s']:>6.2f}{h['d'] * 100:>7.1f}{h['w'] * 100:>5.0f}%"
                   f"{h['t']:>6.2f}{r['pa']:>7.3f}{('YES' if r['ok'] else 'no'):>5}{em:>8}"
                   f"{' lowN' if r['lp'] else ''}")
    return "\n".join(out)


def size_table(rows):
    out = [f"{'candidate':<14}{'variant':<26}{'stop $/oz':>10}{'minEq $':>10}"]
    for r in rows:
        if r["g"] != "buy & hold":
            out.append(f"{r['g']:<14}{r['v'][:25]:<26}{r['emin'] / 100:>10.2f}{r['emin']:>10.0f}")
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser(prog="xau.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("test")
    t.add_argument("--json", action="store_true")
    sub.add_parser("size")
    a = p.parse_args()
    meta, rows = run()
    if a.cmd == "size":
        print(size_table(rows))
    elif a.json:
        print(json.dumps({"meta": meta, "rows": rows}, indent=1))
    else:
        print(table(meta, rows))


if __name__ == "__main__":
    main()
