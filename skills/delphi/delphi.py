# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["numpy==2.3.5", "ta-lib==0.8.3", "websockets==15.0.1"]
# ///
import argparse
import asyncio
import datetime as dt
import json
import math
import os
import re
import stat
import subprocess
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

import numpy as np
import talib
import websockets

warnings.filterwarnings("ignore")
np.seterr(all="ignore")

HOME = Path(os.environ.get("DELPHI_HOME", Path.home() / ".local/share/delphi"))
# journal keys: t time, s slug, p P(up) fair, d side up|down, x price, m market P(up) mid (log), n note (log), v venue p|l (absent = log), a action, q shares, o order id, u status
JOURNAL = HOME / "journal.jsonl"
# snipe keys: s slug, t entry time, k secs left, a best asks [up, down] at entry, d favourite up|down, x avg fill for the stake (null = never hit lo, or f < x + fee + mg),
# q shares, f delphi fair P(d wins) at entry, b lowest best bid of d until close, c {stop: avg sell price for q at the first poll whose best bid < stop}
SNIPE = HOME / "snipe.jsonl"
STOPS = (0.8, 0.7, 0.5, 0.3)
GAMMA = "https://gamma-api.polymarket.com"
CLOB = "https://clob.polymarket.com"
PM_PRICE = "https://polymarket.com/api/crypto/crypto-price"
BIN = "https://api.binance.com/api/v3"
FAPI = "https://fapi.binance.com"
RTDS = "wss://ws-live-data.polymarket.com"
CB = "https://api.exchange.coinbase.com/products"
FEE_SRC = "https://docs.polymarket.com/trading/fees"  # fee = C x feeRate x p x (1-p); rate/exponent from market feeSchedule, takers only
MIN_EDGE = 0.02
MAX_SPREAD = 0.03
MAX_SPOT_AGE = 5
EVENT_PAD = 120
DECISION_MAX_AGE = 10
ARB_MAX = 0.99
CFG = Path(os.environ.get("DELPHI_CONFIG", Path.home() / ".config/delphi"))
GEO = "https://polymarket.com/api/geoblock"
CAL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
DIR = Path(__file__).resolve().parent
LEGS = {"BUY_UP": ["up"], "BUY_DOWN": ["down"], "BUY_BOTH": ["up", "down"]}
ASSETS = {
    "btc": {"sym": "BTCUSDT", "fut": "BTCUSDT", "cb": "BTC-USD", "pm": "BTC", "rt": "btc/usd"},
    "eth": {"sym": "ETHUSDT", "fut": "ETHUSDT", "cb": "ETH-USD", "pm": "ETH", "rt": "eth/usd"},
    "sol": {"sym": "SOLUSDT", "fut": "SOLUSDT", "cb": "SOL-USD", "pm": "SOL", "rt": "sol/usd"},
    "xrp": {"sym": "XRPUSDT", "fut": "XRPUSDT", "cb": "XRP-USD", "pm": "XRP", "rt": "xrp/usd"},
    "xau": {"sym": "PAXGUSDT", "fut": "XAUUSDT", "cb": None, "pm": "XAU", "rt": "xau/usd"},
}
WINDOWS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400}
TF_SETS = {
    "5m": ["1s", "1m", "3m", "5m", "15m", "1h"],
    "15m": ["1m", "3m", "5m", "15m", "1h", "4h"],
    "1h": ["1m", "5m", "15m", "1h", "4h", "1d"],
    "4h": ["5m", "15m", "1h", "4h", "1d", "1w"],
}
DUR = {"1s": 1, "1m": 60, "3m": 180, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400, "1w": 604800}
PM_VARIANT = {"5m": "fiveminute", "15m": "fifteen"}
FAMS = ["trend", "mom", "vol", "volat", "reg", "struct"]
RE_SLUG = re.compile(r"([a-z]+)-updown-(\d+[mh])-(\d+)")
SB_GRID = np.logspace(-5, -2, 300)
MU_GRID = np.linspace(-5e-4, 5e-4, 41)


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def jget(url, t=6):
    try:
        out = subprocess.run(["curl", "-sf", "-m", str(t), url], capture_output=True, text=True, timeout=t + 4).stdout
        return json.loads(out)
    except Exception:
        return None


def klines(asset, iv, start=None):
    q = f"symbol={ASSETS[asset]['sym']}&interval={iv}&limit=1000" + (f"&startTime={start}" if start else "")
    return jget(f"{BIN}/klines?{q}") or []


def twap(asset, end):
    r = jget(f"{BIN}/klines?symbol={ASSETS[asset]['sym']}&interval=1s&startTime={(end - 60) * 1000}&limit=60") or []
    return float(np.mean([float(x[4]) for x in r])) if len(r) == 60 else float("nan")


def pages(url, t0, t1):
    out, s = {}, t0 * 1000
    while s < t1 * 1000:
        r = jget(f"{url}&startTime={s}&limit=1000") or []
        if not r:
            break
        out.update({x[0] // 1000: (float(x[1]), float(x[4])) for x in r})
        s = r[-1][0] + 60000
    return out


def truths(asset, window, n):
    W = WINDOWS[window]
    base = int(time.time()) // W * W
    cand = [base - W * k for k in range(1, 3 * n + 1)]
    mks = list(ThreadPoolExecutor(16).map(lambda T: market(f"{asset}-updown-{window}-{T}"), cand))
    out = {}
    for T, mk in zip(cand, mks):
        op = json.loads(mk["outcomePrices"]) if mk and mk.get("closed") else []
        if op in (["1", "0"], ["0", "1"]):
            out[T] = op[0] == "1"
    return dict(list(out.items())[:n])


def bars(rows):
    a = np.array([r[:10] for r in rows], dtype=float).reshape(-1, 10)
    return {"T": a[:, 0] / 1000, "o": a[:, 1], "h": a[:, 2], "l": a[:, 3], "c": a[:, 4], "v": a[:, 5], "tb": a[:, 9]}


def closed(b, dur, now):
    k = b["T"] + dur <= now
    return {x: y[k] for x, y in b.items()}


def uniq(b):
    _, i = np.unique(b["T"], return_index=True)
    return {k: x[i] for k, x in b.items()}


def lag(x, k=1):
    return np.r_[np.full(k, x[0]), x[:-k]]


def rsum(x, w):
    out = np.full(len(x), np.nan)
    if len(x) < w:
        return out
    cs = np.cumsum(x)
    out[w - 1:] = cs[w - 1:] - np.r_[0.0, cs[:-w]]
    return out


def rmean(x, w):
    return rsum(x, w) / w


def rvar(x, w):
    m = rmean(x, w)
    return rmean(x * x, w) - m * m


def rstd(x, w):
    return np.sqrt(np.maximum(rvar(x, w), 0))


def tf_(f, x, *a):
    out = np.full(len(x), np.nan)
    i = int(np.argmax(np.isfinite(x)))
    out[i:] = f(x[i:], *a)
    return out


def vote(v, ce):
    if ce is None or not np.isfinite(v):
        return None
    return int(np.sign(v - ce))


def fmt(v):
    return "NA" if not np.isfinite(v) else f"{v:.4g}"


_erf = np.vectorize(math.erf, otypes=[float])
_erfc = np.vectorize(math.erfc, otypes=[float])


def Phi(z):
    return 0.5 * (1 + _erf(np.asarray(z, float) / math.sqrt(2)))


def feats(b):
    o, h, l, c, v, tb = b["o"], b["h"], b["l"], b["c"], b["v"], b["tb"]
    lc = np.log(c)
    r = np.diff(lc, prepend=lc[0])
    r4 = r * 1e4
    mid = (h + l) / 2
    tp = (h + l + c) / 3
    mv = rmean(v, 20)
    tr = talib.TRANGE(h, l, c)
    tr[0] = h[0] - l[0]
    e9, e13, e21 = talib.EMA(c, 9), talib.EMA(c, 13), talib.EMA(c, 21)
    bu, bm, bl = talib.BBANDS(c, 20, 2, 2)
    kcw = 4 * talib.ATR(h, l, c, 10)
    rsi14 = talib.RSI(c, 14)
    mac, macs, mach = talib.MACD(c, 12, 26, 9)
    sk, sd = talib.STOCH(h, l, c, 14, 3, 0, 3, 0)
    fk = talib.STOCHF(h, l, c, 14, 3, 0)[0]
    s = lambda p: (c / p - 1) * 100
    bp = lambda x: x * 1e4
    mama, fama = talib.MAMA(c)
    tk = (talib.MAX(h, 9) + talib.MIN(l, 9)) / 2
    kj = (talib.MAX(h, 26) + talib.MIN(l, 26)) / 2
    vwap = rsum(tp * v, 20) / rsum(v, 20)
    vp = np.abs(h - lag(l))
    vm = np.abs(l - lag(h))
    m_ = np.diff(c, prepend=c[0])
    tsi = 100 * tf_(talib.EMA, tf_(talib.EMA, m_, 25), 13) / tf_(talib.EMA, tf_(talib.EMA, np.abs(m_), 25), 13)
    kst = sum(w * tf_(talib.SMA, talib.ROCP(c, n) * 100, p) for w, n, p in [(1, 10, 10), (2, 15, 10), (3, 20, 10), (4, 30, 15)])
    ao = talib.SMA(mid, 5) - talib.SMA(mid, 34)
    obv = talib.OBV(c, v)
    ad = talib.AD(h, l, c, v)
    fi = np.diff(c, prepend=c[0]) * v
    hl = np.where(h > l, h - l, np.inf)
    mfm = ((c - l) - (h - c)) / hl
    emv = np.diff(mid, prepend=mid[0]) * (h - l) / np.maximum(v, 1e-9)
    tbr = np.where(v > 0, tb / np.maximum(v, 1e-9), 0.5)
    cvd = np.cumsum(2 * tb - v)
    pvt = np.cumsum(r * v)
    hl_log = np.log(h / l)
    rt5 = rstd(r4, 5)
    rv20 = rstd(r4, 20)
    lk = np.log([2.0, 4.0, 8.0, 16.0, 32.0])
    wk = (lk - lk.mean()) / ((lk - lk.mean()) ** 2).sum()

    def vk(k, w):
        out = np.full(len(lc), np.nan)
        out[k:] = rvar(lc[k:] - lc[:-k], w)
        return out

    hurst = sum(wi * np.log(vk(k, 128)) for wi, k in zip(wk, [2, 4, 8, 16, 32])) / 2
    vr5 = vk(5, 60) / (5 * rvar(r, 60))
    ac1 = rsum(r * lag(r), 50) / rsum(r * r, 50)
    m1_, m2_, m3_, m4_ = rmean(r4, 50), rmean(r4 ** 2, 50), rmean(r4 ** 3, 50), rmean(r4 ** 4, 50)
    var2 = m2_ - m1_ ** 2
    skew = (m3_ - 3 * m1_ * m2_ + 2 * m1_ ** 3) / var2 ** 1.5
    kurt = (m4_ - 4 * m1_ * m3_ + 6 * m1_ ** 2 * m2_ - 3 * m1_ ** 4) / var2 ** 2 - 3
    chop = 100 * np.log10(rsum(tr, 14) / (talib.MAX(h, 14) - talib.MIN(l, 14))) / np.log10(14)
    er = np.abs(c - lag(c, 20)) / rsum(np.abs(np.diff(c, prepend=c[0])), 20)
    gk = 0.5 * hl_log ** 2 - (2 * np.log(2) - 1) * np.log(c / o) ** 2
    rs = np.log(h / c) * np.log(h / o) + np.log(l / c) * np.log(l / o)
    pv = (lag(h) + lag(l) + lag(c)) / 3

    groups = {
        "trend": [
            ("sma9", s(talib.SMA(c, 9)), 0),
            ("sma21", s(talib.SMA(c, 21)), 0),
            ("sma50", s(talib.SMA(c, 50)), 0),
            ("sma200", s(talib.SMA(c, 200)), 0),
            ("ema9", s(e9), 0),
            ("ema21", s(e21), 0),
            ("dema20", s(talib.DEMA(c, 20)), 0),
            ("tema20", s(talib.TEMA(c, 20)), 0),
            ("kama10", s(talib.KAMA(c, 10)), 0),
            ("t3", s(talib.T3(c, 5, 0.7)), 0),
            ("hma16", s(tf_(talib.WMA, 2 * tf_(talib.WMA, c, 8) - tf_(talib.WMA, c, 16), 4)), 0),
            ("mama_fama", bp((mama - fama) / c), 0),
            ("ht_trend", s(talib.HT_TRENDLINE(c)), 0),
            ("sar", bp((c - talib.SAR(h, l, 0.02, 0.2)) / c), 0),
            ("ema9_21", bp((e9 - e21) / c), 0),
            ("tenkan_kijun", bp((tk - kj) / c), 0),
            ("linreg20_slope", bp(talib.LINEARREG_SLOPE(c, 20) / c), 0),
            ("donch20", (c - talib.MIN(l, 20)) / (talib.MAX(h, 20) - talib.MIN(l, 20)), 0.5),
            ("vwap20", (c / vwap - 1) * 100, 0),
            ("aroon25", talib.AROONOSC(h, l, 25), 0),
            ("dmi14", talib.PLUS_DI(h, l, c, 14) - talib.MINUS_DI(h, l, c, 14), 0),
            ("vortex20", (rsum(vp, 20) - rsum(vm, 20)) / rsum(tr, 20), 0),
        ],
        "mom": [
            ("rsi7", talib.RSI(c, 7), 50),
            ("rsi14", rsi14, 50),
            ("rsi21", talib.RSI(c, 21), 50),
            ("rsi3", talib.RSI(c, 3), 50),
            ("stochrsi14", talib.STOCHRSI(c, 14, 5, 3, 0)[0], 50),
            ("stoch_k", sk, 50),
            ("stochf_k", fk, 50),
            ("stoch_d", sd, 50),
            ("willr14", talib.WILLR(h, l, c, 14), -50),
            ("cci20", talib.CCI(h, l, c, 20), 0),
            ("cmo14", talib.CMO(c, 14), 0),
            ("mfi14", talib.MFI(h, l, c, v, 14), 50),
            ("roc10", talib.ROC(c, 10), 0),
            ("mom10", bp(talib.MOM(c, 10) / c), 0),
            ("macd", bp(mac / c), 0),
            ("macd_sig", bp(macs / c), 0),
            ("macd_hist", bp(mach / c), 0),
            ("ppo", talib.PPO(c, 12, 26, 0), 0),
            ("apo", bp(talib.APO(c, 12, 26, 0) / c), 0),
            ("trix15", talib.TRIX(c, 15), 0),
            ("ultosc", talib.ULTOSC(h, l, c, 7, 14, 28), 50),
            ("tsi", tsi, 0),
            ("kst", kst, 0),
            ("ao", bp(ao / c), 0),
            ("bop14", talib.SMA(talib.BOP(o, h, l, c), 14), 0),
            ("elder", bp(((h - e13) + (l - e13)) / 2 / c), 0),
            ("rsi14_slope5", rsi14 - lag(rsi14, 5), 0),
            ("ret1", r4, 0),
            ("ret5", bp(lc - lag(lc, 5)), 0),
            ("ret20", bp(lc - lag(lc, 20)), 0),
        ],
        "vol": [
            ("obv_slope20", talib.LINEARREG_SLOPE(obv, 20) / mv, 0),
            ("ad_slope20", talib.LINEARREG_SLOPE(ad, 20) / mv, 0),
            ("adosc3_10", talib.ADOSC(h, l, c, v, 3, 10) / mv, 0),
            ("cmf20", rsum(mfm * v, 20) / rsum(v, 20), 0),
            ("force13", talib.EMA(fi, 13) / mv, 0),
            ("eom14", talib.SMA(emv, 14), 0),
            ("vol_z50", (v - rmean(v, 50)) / rstd(v, 50), None),
            ("tb_ratio", tbr, 0.5),
            ("tb_ratio20", rsum(tb, 20) / rsum(v, 20), 0.5),
            ("cvd_slope20", talib.LINEARREG_SLOPE(cvd, 20) / mv, 0),
            ("pvt_slope20", talib.LINEARREG_SLOPE(pvt, 20) / mv, 0),
            ("tb_z50", (tbr - rmean(tbr, 50)) / rstd(tbr, 50), 0),
        ],
        "volat": [
            ("atr14_bps", bp(talib.ATR(h, l, c, 14) / c), None),
            ("atr5_20", talib.ATR(h, l, c, 5) / talib.ATR(h, l, c, 20), None),
            ("bbw20_pct", (bu - bl) / bm * 100, None),
            ("bb_pctb", (c - bl) / (bu - bl), 0.5),
            ("kc_width_bps", bp(kcw / c), None),
            ("squeeze", ((bu - bl) < kcw).astype(float), None),
            ("rv20_bps", rv20, None),
            ("parkinson20_bps", bp(np.sqrt(np.maximum(rmean(hl_log ** 2, 20) / (4 * np.log(2)), 0))), None),
            ("gk20_bps", bp(np.sqrt(np.maximum(rmean(gk, 20), 0))), None),
            ("rs20_bps", bp(np.sqrt(np.maximum(rmean(rs, 20), 0))), None),
            ("rv5_20", rt5 / rv20, None),
            ("range_bps", bp((h - l) / c), None),
        ],
        "reg": [
            ("hurst128", hurst, 0.5),
            ("vr5_60", vr5, 1),
            ("ac1_50", ac1, 0),
            ("skew50", skew, 0),
            ("kurt50", kurt, None),
            ("zscore20", (c - talib.SMA(c, 20)) / talib.STDDEV(c, 20, 1), 0),
            ("chop14", chop, 50),
            ("er20", er, None),
            ("ht_trendmode", talib.HT_TRENDMODE(c), None),
            ("ht_dcperiod", talib.HT_DCPERIOD(c), None),
        ],
        "struct": [
            ("swing_hi20_bps", bp((talib.MAX(h, 20) - c) / c), None),
            ("swing_lo20_bps", bp((c - talib.MIN(l, 20)) / c), None),
            ("pivot_bps", bp((c - pv) / c), 0),
            ("fib50", (c - talib.MIN(l, 50)) / (talib.MAX(h, 50) - talib.MIN(l, 50)), 0.5),
        ],
    }
    out = [(f, n, a, ce) for f in FAMS for n, a, ce in groups[f]]
    assert len(out) == 90, len(out)
    return out


CDL = talib.get_function_groups()["Pattern Recognition"]


def patterns(b):
    res = []
    for n in CDL:
        val = int(getattr(talib, n)(b["o"], b["h"], b["l"], b["c"])[-1])
        if val:
            res.append(f"{n}{val:+d}")
    return res


def market(slug):
    ev = jget(f"{GAMMA}/events?slug={slug}")
    return ev[0]["markets"][0] if ev else None


def rule(mk):
    cfg = mk.get("cryptoMarketConfig") or {}
    desc = mk.get("description", "")
    if cfg:
        twap = bool(cfg.get("twapEnabled"))
        L = (cfg.get("twapLookbackSeconds") or 60) if twap else 1
    else:
        twap = "time-weighted" in desc.lower()
        L = 60 if twap else 1
    return twap, L, desc.split(".")[0][:160]


def rule_for(asset, window, now):
    W = WINDOWS[window]
    base = int(now) // W * W
    for ts in (base, base + W):
        mk = market(f"{asset}-updown-{window}-{ts}")
        if mk:
            return rule(mk)[:2]
    return (asset != "xau"), (60 if asset != "xau" else 1)


def resolve(asset, window, target, now):
    m = RE_SLUG.search(target)
    if m:
        slug = m.group(0)
        return slug, market(slug)
    if target not in ("now", "next"):
        raise SystemExit(f"bad target {target}")
    W = WINDOWS[window]
    base = int(now) // W * W
    off = 1 if target == "next" else 0
    slugs = [f"{asset}-updown-{window}-{base + W * k}" for k in range(off, off + 3)]
    mks = list(ThreadPoolExecutor(8).map(market, slugs))
    for slug, mk in zip(slugs, mks):
        if mk:
            return slug, mk
    raise SystemExit(f"no open {asset} {window} window (market hours or not listed): {slugs}")


def book(tok):
    bk = jget(f"{CLOB}/book?token_id={tok}") or {}
    bids = sorted(((float(x["price"]), float(x["size"])) for x in bk.get("bids", [])), reverse=True)
    asks = sorted((float(x["price"]), float(x["size"])) for x in bk.get("asks", []))
    return bids, asks


def fee(p, fs):
    fs = fs or {}
    return round(fs.get("rate", 0) * p * (1 - p) ** fs.get("exponent", 1), 5)


def rtds(sym, sec):
    out = []

    async def run():
        try:
            async with websockets.connect(RTDS, open_timeout=sec, close_timeout=0.2) as ws:
                await ws.send(json.dumps({"action": "subscribe", "subscriptions": [
                    {"topic": "crypto_prices_chainlink", "type": "*", "filters": json.dumps({"symbol": sym})}]}))
                end = time.monotonic() + sec
                while time.monotonic() < end:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), end - time.monotonic())
                    except TimeoutError:
                        break
                    try:
                        p = json.loads(msg).get("payload") or {}
                    except ValueError:
                        continue
                    if isinstance(p.get("data"), list):
                        out.extend((d["timestamp"], d["value"]) for d in p["data"])
                    elif "value" in p:
                        out.append((p["timestamp"], p["value"]))
        except Exception:
            pass

    if os.environ.get("DELPHI_FAIL") != "rtds": asyncio.run(run())
    return sorted(out)


def peek(target, a):
    m = RE_SLUG.search(target)
    if m:
        return m.group(1), m.group(2)
    return a.asset or "btc", a.window or "5m"


def snap(a):
    t0 = time.time()
    now = t0
    asset, window = peek(a.target, a)
    cfg = ASSETS[asset]
    W = WINDOWS[window]
    ex = ThreadPoolExecutor(24)
    rt_f = ex.submit(rtds, cfg["rt"], 1.5)
    slug, mk = resolve(asset, window, a.target, now)
    t_res = time.time()
    T = int(slug.rsplit("-", 1)[1])
    E = T + W
    twap, L, rule_txt = rule(mk)
    tfs = TF_SETS[window]
    ivs = sorted(set(tfs) | {"1s", "1m"}, key=lambda x: DUR[x])
    kl = {iv: ex.submit(klines, asset, iv) for iv in ivs}
    px_f = ex.submit(jget, f"{PM_PRICE}?symbol={cfg['pm']}&eventStartTime={iso(T)}&variant={PM_VARIANT[window]}&endDate={iso(E)}") if window in PM_VARIANT and asset != "xau" else None
    fut = cfg["fut"]
    prem_f = ex.submit(jget, f"{FAPI}/fapi/v1/premiumIndex?symbol={fut}")
    ix_f = ex.submit(jget, f"{FAPI}/fapi/v1/indexPriceKlines?pair={fut}&interval=1m&startTime={T * 1000}&limit=1") if asset == "xau" and now >= T else None
    dep_f = ex.submit(jget, f"{BIN}/depth?symbol={cfg['sym']}&limit=100")
    cb_f = ex.submit(jget, f"{CB}/{cfg['cb']}/ticker") if cfg["cb"] else None
    fut_f = ex.submit(jget, f"{FAPI}/fapi/v1/klines?symbol={fut}&interval=1m&limit=3") if asset == "xau" else None
    der_f = {k: ex.submit(jget, f"{FAPI}/futures/data/{p}?symbol={fut}&period=5m&limit=30") for k, p in
             {"oih": "openInterestHist", "tls": "takerlongshortRatio", "gls": "globalLongShortAccountRatio", "tops": "topLongShortPositionRatio"}.items()}
    bks = [ex.submit(book, t) for t in json.loads(mk["clobTokenIds"])] if now < E else []
    bks = [x.result() for x in bks]
    t_books = time.time()

    B = {iv: closed(bars(kl[iv].result()), DUR[iv], now) for iv in ivs}
    px = (px_f.result() if px_f else None) or {}
    rt = rt_f.result()
    prem = prem_f.result() or {}
    dep = dep_f.result() or {}
    cbp = (cb_f.result() or {}).get("price") if cb_f else None
    fs = mk.get("feeSchedule") or {"rate": 0.07, "exponent": 1, "src": "default"}
    phase = "pre" if now < T else "live" if now < E else "closed"
    tau = max(E - now, 0.0)
    c1 = B["1s"]["c"]
    s_bin = c1[-1]
    K = px.get("openPrice")
    k_src = "polymarket crypto-price openPrice"
    k_fam = "chainlink"
    ix = ix_f.result() if ix_f and os.environ.get("DELPHI_FAIL") != "index" else None
    if ix:
        K, k_src, k_fam = float(ix[0][1]), "binance xau index open at window start (indexPriceKlines)", "binance-index"
    elif K is None and now >= T:
        K = c1[np.searchsorted(B["1s"]["T"], T - 1)]
        k_src = "proxy: spot 1s close at window start (no Polymarket/Chainlink reference)"
        k_fam = "binance-spot"
    ch = rt[-1] if rt else None
    if ch:
        S, s_src, s_fam = ch[1], "chainlink rtds", "chainlink"
    elif asset == "xau" and prem.get("indexPrice"):
        S, s_src, s_fam = float(prem["indexPrice"]), "binance xau index (premiumIndex indexPrice)", "binance-index"
    else:
        S, s_src, s_fam = s_bin, "proxy: spot", "binance-spot"
    r1 = np.diff(np.log(c1))
    s15 = np.sqrt(np.mean(r1[-900:] ** 2))
    s5 = np.sqrt(np.mean(r1[-300:] ** 2))
    w_ew = 0.995 ** np.arange(len(r1[-1800:]))[::-1]
    sew = np.sqrt(np.sum(w_ew * r1[-1800:] ** 2) / np.sum(w_ew))
    r1m = np.diff(np.log(B["1m"]["c"]))
    s1m = np.sqrt(np.mean(r1m[-60:] ** 2)) / math.sqrt(60)
    b1 = {k: x[-60:] for k, x in B["1m"].items()}
    gk1m = np.sqrt(np.mean(0.5 * np.log(b1["h"] / b1["l"]) ** 2 - (2 * np.log(2) - 1) * np.log(b1["c"] / b1["o"]) ** 2)) / math.sqrt(60)
    ef = HOME / f"edges-{asset}-{window}.json"
    ed = json.loads(ef.read_text()) if ef.exists() else {}
    mm, bb, mb = ed.get("m", 1.0), ed.get("b", 0.0), ed.get("o", 0.0)
    proxy = K is not None and phase == "live" and abs(math.log(S / K) - mb) < 2 * bb
    sd = mm * s1m * S
    obs =[v for t_, v in rt if E - L < t_ / 1000 <= now]
    obs_m = float(np.mean(obs)) if obs else S
    mixed = phase == "live" and (K is None or k_fam != s_fam or (tau < L and ("chainlink" if obs else None) != k_fam))
    pf = None
    p_g = p_t = z_tw = z_nv = None
    if phase == "live" and K is not None:
        rng = np.random.default_rng(7)
        if tau >= L:
            mean, var = S, sd * sd * (tau - 2 * L / 3)
        else:
            mean = ((L - tau) * obs_m + tau * S) / L
            var = sd * sd * tau ** 3 / (3 * L * L)
        var += (S * bb) ** 2
        Ke = K * math.exp(mb)
        z_tw = (mean - Ke) / math.sqrt(var)
        p_g = float(Phi(z_tw))
        n = int(tau)
        eps = rng.standard_t(4, size=(5000, n)) * math.sqrt(0.5)
        path = S + sd * np.cumsum(eps, axis=1)
        tw = path[:, n - L:].mean(1) if n >= L else ((L - n) * obs_m + path.sum(1)) / L
        tw = tw + S * bb * rng.standard_normal(5000)
        p_t = float(np.mean(tw >= Ke))
        pf = p_t
        z_nv = (math.log(S / K) - mb) / math.sqrt((mm * s1m) ** 2 * tau + bb * bb)
    elif phase == "pre":
        pf = 0.5

    basis = None
    if fut_f:
        fk_ = fut_f.result() or []
        if fk_:
            basis = (B["1m"]["c"][-1] - float(fk_[-1][4])) / float(fk_[-1][4]) * 1e4

    L_out = [
        f"slug {slug}",
        f"question {mk['question']}",
        f"rule {'TWAP' + str(L) + 's' if twap else 'point price'} (lookback {L}s): {rule_txt}",
        f"source {mk.get('resolutionSource')}",
        f"window_utc {iso(T)} -> {iso(E)}",
        f"now_utc {iso(now)}",
        f"elapsed {now - T:.1f}s remaining {tau:.1f}s phase {phase}",
        f"data_age_ms spot_1s {(now - B['1s']['T'][-1] - 1) * 1000:.0f} chainlink {(now - ch[0] / 1000) * 1000 if ch else float('nan'):.0f}",
        f"fee_src {FEE_SRC} schedule {fs}",
        "",
        f"K price_to_beat {K} src={k_src if K is not None else 'pending'}",
        f"S {S:.4f} src={s_src} spot_1s {s_bin:.4f} diff {S - s_bin:+.4f}",
        f"S-K {S - K:+.4f} ({(S / K - 1) * 1e4:+.1f} bps)" if K is not None else "S-K n/a",
        f"sigma_mult_m {mm:.4f} sigma_b_bps {bb * 1e4:.3f} mu_b_bps {mb * 1e4:+.3f}",
        "PROXY ZONE: market knows more, no bet" if proxy else "",
        f"MIXED SOURCES k={k_fam} s={s_fam}: no bet" if mixed else "",
        f"basis_xau_spot_vs_perp_bps {basis:+.2f} (PAXGUSDT spot vs XAUUSDT perp, 1m close; no Chainlink/Polymarket XAU reference)" if basis is not None else "",
        f"sigma_per_sqrt_s 1s15m={s15:.3e} 1s5m={s5:.3e} ewma1s={sew:.3e} 1m1h={s1m:.3e} gk1m1h={gk1m:.3e} primary=1s15m",
        f"realized_partial_{'twap' if L > 1 else 'price'} {obs_m:.4f} dist_to_K {obs_m - K:+.4f}" if K is not None and phase == "live" and tau < L else "realized_partial n/a",
        f"z_naive {z_nv:.3f}" if z_nv is not None else "z_naive n/a",
        f"z_model {z_tw:.3f}" if z_tw is not None else "z_model n/a",
        f"fair P_up gaussian={p_g:.4f} t4_mc={p_t:.4f} used=t4_mc" if p_t is not None else f"fair P_up {pf} ({'pre-window baseline' if phase == 'pre' else 'n/a'})",
    ]
    L_out = [x for x in L_out if x]
    if phase == "closed":
        op = json.loads(mk["outcomePrices"])
        L_out.append(f"resolved {'Up' if float(op[0]) > 0.5 else 'Down'} crypto_open {px.get('openPrice')} crypto_close {px.get('closePrice')}")
    if phase != "closed" and len(bks) == 2:
        (ub, ua), (db, da) = bks
        if not (ub and ua and db and da):
            L_out.append("market no two-sided book (closed, paused, or thin)")
        else:
            for lab, bd, ad_ in (("UP", ub, ua), ("DOWN", db, da)):
                L_out.append(f"{lab} bid={bd[0][0]} ask={ad_[0][0]} mid={(bd[0][0] + ad_[0][0]) / 2:.4f} spread={ad_[0][0] - bd[0][0]:.4f} "
                             f"bids3={bd[:3]} asks3={ad_[:3]} fee@ask={fee(ad_[0][0], fs)}")
            up_b, up_a, dn_b, dn_a = ub[0][0], ua[0][0], db[0][0], da[0][0]
            L_out.append(f"implied_P_up {(up_b + up_a) / (up_b + up_a + dn_b + dn_a):.4f} top_gap_up {ub[0][0] - ub[1][0] if len(ub) > 1 else 'n/a'}")
            if pf is not None:
                a_up = up_a + fee(up_a, fs)
                a_dn = dn_a + fee(dn_a, fs)
                e_up = pf - a_up
                e_dn = (1 - pf) - a_dn
                L_out.append(f"edge_UP fair={pf:.4f} ask={up_a} fee={fee(up_a, fs)} breakeven={a_up:.4f} edge={e_up:+.4f}")
                L_out.append(f"edge_DOWN fair={1 - pf:.4f} ask={dn_a} fee={fee(dn_a, fs)} breakeven={a_dn:.4f} edge={e_dn:+.4f}")
                e_best, act, p_best, a_best = max([(e_up, "BUY UP", pf, a_up), (e_dn, "BUY DOWN", 1 - pf, a_dn)])
                kel = 0.25 * max(0.0, (p_best - a_best) / (1 - a_best))
                action = "NO BET" if mixed or proxy or e_best <= MIN_EDGE else act
                L_out.append(f"action {action} best_edge={e_best:+.4f} quarter_kelly={kel:.4f} min_edge={MIN_EDGE}")

    bids = [(float(p_), float(q)) for p_, q in dep.get("bids", [])]
    asks = [(float(p_), float(q)) for p_, q in dep.get("asks", [])]
    imb = lambda n: (sum(q for _, q in bids[:n]) - sum(q for _, q in asks[:n])) / (sum(q for _, q in bids[:n]) + sum(q for _, q in asks[:n]))
    micro = ((asks[0][0] * bids[0][1] + bids[0][0] * asks[0][1]) / (bids[0][1] + asks[0][1]) - (asks[0][0] + bids[0][0]) / 2) / ((asks[0][0] + bids[0][0]) / 2) * 1e4
    oih = (der_f["oih"].result() or [])
    tls = (der_f["tls"].result() or [])
    gls = (der_f["gls"].result() or [])
    tops = (der_f["tops"].result() or [])
    oi = [float(x["sumOpenInterest"]) for x in oih]

    F = {iv: feats(B[iv]) for iv in tfs}
    LV = {iv: {nm: (arr[-1], ce) for _, nm, arr, ce in F[iv]} for iv in tfs}
    b5, b1h, b1m = B["5m"], B["1h"], B["1m"]
    align = []
    L_out += ["", "SUMMARY"]
    for iv in tfs:
        cnt = {fa: [0, 0] for fa in FAMS}
        for fa, nm, arr, ce in F[iv]:
            vt = vote(arr[-1], ce)
            if vt == 1:
                cnt[fa][0] += 1
            elif vt == -1:
                cnt[fa][1] += 1
        tn = cnt["trend"]
        align.append((tn[0] - tn[1]) / max(tn[0] + tn[1], 1))
        adx = talib.ADX(B[iv]["h"], B[iv]["l"], B[iv]["c"], 14)[-1]
        ch_ = LV[iv]["chop14"][0]
        reg = "trend" if adx > 25 and ch_ < 50 else "range" if adx < 20 or ch_ > 61.8 else "mixed"
        L_out.append(f"regime {iv} {reg} adx={adx:.1f} chop={fmt(ch_)} er={fmt(LV[iv]['er20'][0])} "
                     f"hurst={fmt(LV[iv]['hurst128'][0])} vr5={fmt(LV[iv]['vr5_60'][0])}")
        L_out.append(f"votes {iv} " + " ".join(f"{fa} +{cnt[fa][0]}/-{cnt[fa][1]}" for fa in FAMS))
    L_out.append(f"alignment {np.mean(align):+.3f} (mean trend net over {len(tfs)} TFs, -1..+1)")

    tpv = (b1m["h"] + b1m["l"] + b1m["c"]) / 3
    vwap1m = rsum(tpv * b1m["v"], 20)[-1] / rsum(b1m["v"], 20)[-1]
    bu5, _, bl5 = talib.BBANDS(b5["c"], 20, 2, 2)
    P1h = (b1h["h"][-1] + b1h["l"][-1] + b1h["c"][-1]) / 3
    step = 500 if asset in ("btc", "eth") else 10 if asset == "xau" else 0.5
    rlo = math.floor(S / step) * step
    levels = [("swing_hi_5m20", talib.MAX(b5["h"], 20)[-1]), ("swing_lo_5m20", talib.MIN(b5["l"], 20)[-1]),
              ("pivot_1h", P1h), ("prior1h_hi", b1h["h"][-1]), ("prior1h_lo", b1h["l"][-1]),
              ("vwap20_1m", vwap1m), ("bb5m_up", bu5[-1]), ("bb5m_lo", bl5[-1]),
              ("round_below", rlo), ("round_above", rlo + step)]
    for n_, x in levels:
        su = (x - S) / (sd * math.sqrt(tau)) if tau > 0 else float("nan")
        L_out.append(f"level {n_} {x:.4f} {(x / S - 1) * 1e4:+.1f}bp {su:+.2f}su")

    tbr = lambda n: b1m["tb"][-n:].sum() / b1m["v"][-n:].sum()
    L_out.append(f"orderflow taker_buy 1m={tbr(1):.3f} 5m={tbr(5):.3f} 15m={tbr(15):.3f} "
                 f"cvd_slope20_1m={fmt(LV['1m']['cvd_slope20'][0])} book_imb10={imb(10):+.3f} "
                 f"book_imb50={imb(50):+.3f} microprice_minus_mid_bps={micro:+.2f}")
    pv_ = lambda k: float(prem[k]) if k in prem else float("nan")
    L_out.append(f"derivs({fut}) funding_pct={pv_('lastFundingRate') * 100:.4f} "
                 f"basis_bps={(pv_('markPrice') / pv_('indexPrice') - 1) * 1e4:+.2f} "
                 f"oi_5m={(oi[-1] / oi[-2] - 1) * 100 if len(oi) > 1 else float('nan'):+.3f}% "
                 f"oi_1h={(oi[-1] / oi[-13] - 1) * 100 if len(oi) > 12 else float('nan'):+.3f}% "
                 f"global_LS={gls[-1]['longShortRatio'] if gls else 'NA'} top_pos_LS={tops[-1]['longShortRatio'] if tops else 'NA'} "
                 f"taker_BS_5m={tls[-1]['buySellRatio'] if tls else 'NA'} coinbase={cbp}")

    sigs = ed.get("s", [])
    L_out.append("edge_signals (top 5 by OOS z)" if sigs else f"edge_signals none (run: delphi edge --asset {asset} --window {window})")
    for sg in sigs[:5]:
        iv, nm = sg["k"].split(":", 1)
        if iv not in LV:
            continue
        v_, ce = LV[iv][nm]
        vt = vote(v_, ce)
        agr = "n/a" if vt is None else "agree" if vt * sg["d"] > 0 else "disagree" if vt * sg["d"] < 0 else "flat"
        L_out.append(f"  {sg['k']} d={sg['d']:+d} oos={sg['h']:.3f} n={sg['n']} z={sg['z']:.2f} live={fmt(v_)} vote={vt} {agr}")

    L_out += ["", "INDICATORS"]
    tot = 0
    for iv in tfs:
        L_out.append(f"== {iv} ==")
        for fa in FAMS:
            L_out.append(f"-- {fa}")
            for f_, nm, arr, ce in F[iv]:
                if f_ != fa:
                    continue
                vt = vote(arr[-1], ce)
                sym = "." if ce is None else {1: "+", -1: "-", 0: "0"}.get(vt, "NA")
                L_out.append(f"{nm} {fmt(arr[-1])} {sym}")
                tot += 1
        L_out.append(f"patterns {iv}: " + (" ".join(patterns(B[iv])) or "none"))
    L_out.append(f"indicator_values {tot} ({tot // len(tfs)} per TF x {len(tfs)})")
    t_end = time.time()
    L_out.append(f"timing_ms resolve={(t_res - t0) * 1000:.0f} books={(t_books - t_res) * 1000:.0f} total={(t_end - t0) * 1000:.0f}")
    vals = {iv: {f"{f_}.{nm}": (None if not np.isfinite(arr[-1]) else float(arr[-1])) for f_, nm, arr, ce in F[iv]} for iv in tfs}
    return {"lines": L_out, "values": vals, "mixed": mixed, "asset": asset, "window": window,
            "rule": f"twap{L}s" if twap else "point", "slug": slug, "T": T, "E": E, "now": now, "phase": phase,
            "tau": tau, "K": K, "k_src": k_src, "S": S, "s_src": s_src, "pf": pf, "proxy": proxy,
            "spot_age": now - B["1s"]["T"][-1] - 1, "books": bks, "fs": fs}


def cmd_snap(a):
    r = snap(a)
    if a.json:
        print(json.dumps({"lines": r["lines"], "values": r["values"], "mixed": r["mixed"]}))
    else:
        print("\n".join(r["lines"]))


def limits():
    f = CFG / "limits.json"
    d = json.loads(f.read_text()) if f.exists() else {}
    return {"shares": max(5, d.get("shares", 5)), "daily_loss_usd": d.get("daily_loss_usd", 5),
            "max_trade_usd": d.get("max_trade_usd", 3), "min_secs_left": d.get("min_secs_left", 20)}


def calendar():
    f = HOME / f"calendar-{dt.datetime.now(dt.UTC):%Y-%m-%d}.json"
    if not f.exists():
        ev = jget(CAL, 10)
        if ev is None:
            return None
        HOME.mkdir(parents=True, exist_ok=True)
        for old in HOME.glob("calendar-*.json"):
            old.unlink()
        f.write_text(json.dumps(ev))
    return json.loads(f.read_text())


def event_near(T, E):
    ev = calendar()
    if ev is None:
        return True
    return any(x.get("country") == "USD" and x.get("impact") == "High"
               and T - EVENT_PAD <= dt.datetime.fromisoformat(x["date"]).timestamp() <= E + EVENT_PAD for x in ev)


def leg(bd, ad, p, fs):
    ask = ad[0][0]
    fe = fee(ask, fs)
    return {"bid": bd[0][0], "ask": ask, "fee": fe, "edge": None if p is None else round(p - ask - fe, 5)}


def verdict(r):
    lim = limits()
    fs, pf, bks = r["fs"], r["pf"], r["books"]
    two = len(bks) == 2 and all(b and s for b, s in bks)
    L = {"up": None, "down": None}
    if two:
        (ub, ua), (db, da) = bks
        L["up"] = leg(ub, ua, pf, fs)
        L["down"] = leg(db, da, None if pf is None else 1 - pf, fs)
    up, dn = L["up"], L["down"]
    thin = not two or max(up["ask"] - up["bid"], dn["ask"] - dn["bid"]) > MAX_SPREAD
    stale = r["spot_age"] >= MAX_SPOT_AGE
    late = r["tau"] < lim["min_secs_left"]
    ev = event_near(r["T"], r["E"])
    checks = [("not_live", r["phase"] != "live"), ("stale", stale), ("thin_book", thin), ("mixed", r["mixed"]),
              ("proxy", r["proxy"]), ("event", ev), ("late", late)]
    reasons = [c for c, bad in checks if bad]
    arb = two and up["ask"] + dn["ask"] + up["fee"] + dn["fee"] <= ARB_MAX
    action = "NO_BET"
    if not reasons:
        if arb:
            action = "BUY_BOTH"
        elif max(up["edge"], dn["edge"]) >= MIN_EDGE:
            action = "BUY_UP" if up["edge"] >= dn["edge"] else "BUY_DOWN"
        else:
            reasons = ["no_edge"]
    legs = LEGS.get(action, [])
    shares = lim["shares"] if legs else 0
    cost = round(sum((shares * (L[s]["ask"] + L[s]["fee"]) for s in legs), 0.0), 4)
    lp = L[legs[0]]["ask"] if len(legs) == 1 else None
    return {"slug": r["slug"], "asset": r["asset"], "window": r["window"], "phase": r["phase"],
            "secs_left": round(r["tau"], 1), "rule": r["rule"],
            "k": None if r["K"] is None else float(r["K"]), "k_src": r["k_src"],
            "s": float(r["S"]), "s_src": r["s_src"],
            "p_fair": pf if r["phase"] == "live" else None, "up": up, "down": dn,
            "action": action, "limit_price": lp, "shares": shares, "cost_usd": cost, "reasons": reasons,
            "flags": {"proxy_zone": bool(r["proxy"]), "mixed": bool(r["mixed"]), "stale": bool(stale),
                      "event": bool(ev), "thin_book": bool(thin), "late": bool(late), "arb": bool(arb)},
            "ts": r["now"]}


def nobet(a, why):
    return {"slug": None, "asset": a.asset, "window": a.window, "phase": None, "secs_left": None, "rule": None,
            "k": None, "k_src": None, "s": None, "s_src": None, "p_fair": None, "up": None, "down": None,
            "action": "NO_BET", "limit_price": None, "shares": 0, "cost_usd": 0.0, "reasons": [why],
            "flags": {}, "ts": time.time()}


def cmd_decide(a):
    try:
        out = verdict(snap(a))
    except SystemExit as e:
        print(e, file=sys.stderr)
        out = nobet(a, "no_window")
    except Exception as e:
        print(repr(e), file=sys.stderr)
        out = nobet(a, "engine_error")
    print(json.dumps(out))


def same_call(g, d):
    try:
        if g["action"] != d["action"] or g["slug"] != d["slug"]:
            return False
        if (g["limit_price"] is None) != (d["limit_price"] is None):
            return False
        if d["limit_price"] is not None and abs(float(g["limit_price"]) - d["limit_price"]) > 1e-9:
            return False
        return abs(float(g["shares"]) - d["shares"]) <= 1e-9
    except (KeyError, TypeError, ValueError):
        return False


def llm_reasons(d, path):
    p = Path(path) if path else None
    raw = p.read_text().strip() if p and p.is_file() else ""
    if not raw:
        return [] if os.environ.get("DELPHI_LLM_OPTIONAL") == "1" else ["llm_unavailable"]
    lines = [x for x in raw.splitlines() if x.strip().startswith("{")]
    try:
        g = json.loads(lines[-1])
    except (ValueError, IndexError):
        return ["llm_bad"]
    return [] if same_call(g, d) else ["llm_mismatch"]


def fresh_ok(d1, d2):
    if d2["action"] != d1["action"] or d2["slug"] != d1["slug"]:
        return False
    return all(d2[s]["ask"] <= d1[s]["ask"] + 1e-9 for s in LEGS[d1["action"]])


def cmd_judge(a):
    d = json.loads(Path(a.decision).read_text())
    if d["action"] != "NO_BET":
        why = llm_reasons(d, a.llm)
        f = None
        if not why:
            try:
                f = json.loads(Path(a.fresh).read_text())
            except (OSError, ValueError):
                f = None
            if f is None or not fresh_ok(d, f):
                why = ["moved"]
        if why:
            d = {**d, "action": "NO_BET", "limit_price": None, "shares": 0, "cost_usd": 0.0,
                 "reasons": d["reasons"] + why}
        else:
            d = f
    print(json.dumps(d))


def rows():
    return [json.loads(x) for x in JOURNAL.read_text().splitlines() if x.strip()] if JOURNAL.exists() else []


def write(recs, path=JOURNAL):
    HOME.mkdir(parents=True, exist_ok=True)
    with path.open("a") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")


def traded(slug):
    return any("v" in r and r["s"] == slug for r in rows())


def leg_pnl(r, m):
    op = [float(x) for x in json.loads(m["outcomePrices"])]
    if not m.get("closed") or op[0] not in (0.0, 1.0):
        return None, None
    win = (op[0] == 1.0) == (r["d"] == "up")
    x, q = r["x"], r.get("q", 1)
    return q * ((1 - x) if win else -x) - q * fee(x, m.get("feeSchedule")), win


def day_loss(now):
    loss = 0.0
    for r in rows():
        if r.get("v") != "l" or r["t"] < now - now % 86400:
            continue
        m = market(r["s"]) or {}
        pnl = leg_pnl(r, m)[0] if m else None
        if pnl is None:
            loss += r["q"] * (r["x"] + fee(r["x"], m.get("feeSchedule")))
        else:
            loss += max(0.0, -pnl)
    return loss


def live_env():
    f = CFG / "live.env"
    if not f.exists() or stat.S_IMODE(f.stat().st_mode) != 0o600:
        return None
    env = dict(x.split("=", 1) for x in f.read_text().splitlines() if "=" in x)
    keys = ["POLYMARKET_PRIVATE_KEY", "POLYMARKET_WALLET", "POLYMARKET_RELAYER_KEY", "POLYMARKET_RELAYER_ADDRESS"]
    return env if all(env.get(k) for k in keys) else None


def geo_blocked():
    t = os.environ.get("DELPHI_GEOBLOCK_TEST")
    if t:
        return t != "open"
    g = jget(GEO)
    return g is None or g.get("blocked") is not False


def emit(status, msg, **kw):
    print(json.dumps({"status": status, "msg": msg, **kw}))


def refuse(msg):
    emit("refused", msg)
    raise SystemExit(2)


def record(d, v, s, x, o, u):
    return {"t": int(time.time()), "s": d["slug"], "v": v, "p": d["p_fair"], "d": s, "a": d["action"],
            "x": x, "q": d["shares"], "o": o, "u": u}


def paper(d):
    recs = [record(d, "p", s, d[s]["ask"], None, "paper") for s in LEGS[d["action"]]]
    write(recs)
    emit("paper", d["action"], legs=len(recs))


def live(d, env):
    tok = json.loads(market(d["slug"])["clobTokenIds"])
    legs = [{"d": s, "tok": tok[0 if s == "up" else 1], "x": d[s]["ask"], "q": d["shares"]} for s in LEGS[d["action"]]]
    end = int(d["slug"].rsplit("-", 1)[1]) + WINDOWS[d["window"]]
    p = subprocess.run(["uv", "run", "--script", str(DIR / "trade_live.py")],
                       input=json.dumps({"end": end, "legs": legs}), capture_output=True, text=True,
                       env={**os.environ, **env}, timeout=60)
    try:
        res = json.loads(p.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        res = [{"d": g["d"], "o": None, "u": "error"} for g in legs]
    write([record(d, "l", g["d"], g["x"], o["o"], o["u"]) for g, o in zip(legs, res)])
    emit("live", d["action"], orders=res)


def day_loss_gate(lim):
    loss = day_loss(time.time())
    if loss >= lim["daily_loss_usd"]:
        refuse(f"daily loss {loss:.2f} >= DAILY_LOSS_USD {lim['daily_loss_usd']}")


def cmd_trade(a):
    d = json.loads(sys.stdin.read() if a.decision == "-" else Path(a.decision).read_text())
    if d["action"] == "NO_BET":
        return emit("no_trade", "NO_BET")
    if traded(d["slug"]):
        refuse("slug already traded")
    if not a.live:
        return paper(d)
    lim = limits()
    if os.environ.get("DELPHI_LIVE") != "1":
        refuse("DELPHI_LIVE=1 not set")
    if (CFG / "KILL").exists():
        refuse("KILL file present")
    env = live_env()
    if env is None:
        refuse("live.env missing, not mode 600, or missing keys")
    if d["action"] == "BUY_BOTH":
        refuse("both_legs_paper_only")
    if time.time() - d["ts"] >= DECISION_MAX_AGE:
        refuse("decision older than 10 s")
    if geo_blocked():
        refuse("geoblock: blocked or unknown")
    day_loss_gate(lim)
    if d["cost_usd"] > lim["max_trade_usd"]:
        refuse(f"cost {d['cost_usd']} > MAX_TRADE_USD {lim['max_trade_usd']}")
    live(d, env)


def history(ex, asset, iv, days, t_run):
    span = 2 * 86400 if iv == "1s" else days * 86400 if DUR[iv] <= 900 else 400 * 86400
    step = 1000 * DUR[iv]
    start = int(t_run - span)
    starts = [(start + i * step) * 1000 for i in range(math.ceil(span / step))]
    rows = sum(ex.map(partial(klines, asset, iv), starts), [])
    return closed(uniq(bars(rows)), DUR[iv], t_run)


def edge(a):
    t_run = time.time()
    ex = ThreadPoolExecutor(24)
    twap_, L = rule_for(a.asset, a.window, t_run)
    W = WINDOWS[a.window]
    tfs = TF_SETS[a.window]
    H = {iv: history(ex, a.asset, iv, a.days, t_run) for iv in sorted(set(tfs) | {"1s", "1m"}, key=lambda x: DUR[x])}
    m1, s1b = H["1m"], H["1s"]
    F = {iv: feats(H[iv]) for iv in tfs}

    T1 = m1["T"]
    t0s = np.arange(math.ceil(T1[0] / W) * W, T1[-1] - W + 60 + 1, W)
    i0 = np.minimum(np.searchsorted(T1, t0s), len(T1) - 1)
    ie = np.minimum(np.searchsorted(T1, t0s + W - 60), len(T1) - 1)
    ok = (T1[i0] == t0s) & (T1[ie] == t0s + W - 60)
    t0s, i0, ie = t0s[ok], i0[ok], ie[ok]
    W_n = len(t0s)
    Kp = m1["o"][i0]
    if L == 1:
        Yp = m1["c"][ie] >= Kp
    else:
        Yp = (m1["o"][ie] + m1["h"][ie] + m1["l"][ie] + m1["c"][ie]) / 4 >= Kp

    T1s, c1s = s1b["T"], s1b["c"]
    rm60 = rmean(c1s, 60)
    jk = np.minimum(np.searchsorted(T1s, t0s - 1), len(T1s) - 1)
    je = np.minimum(np.searchsorted(T1s, t0s + W - 1), len(T1s) - 1)
    endv = rm60[je] if L > 1 else c1s[je]
    mx = (T1s[jk] == t0s - 1) & (T1s[je] == t0s + W - 1) & np.isfinite(endv)
    Yx = endv >= c1s[jk]

    Xs, Cs, names = [], [], []
    for iv in tfs:
        j = np.searchsorted(H[iv]["T"] + DUR[iv], t0s, side="right") - 1
        for _, nm, arr, ce in F[iv]:
            Xs.append(np.where(j >= 0, arr[np.maximum(j, 0)], np.nan))
            Cs.append(np.nan if ce is None else ce)
            names.append(f"{iv}:{nm}")
    X = np.column_stack(Xs)
    C = np.array(Cs, float)

    Cb = np.broadcast_to(C, X.shape)
    V = np.where(np.isfinite(X) & np.isfinite(Cb), np.sign(X - Cb), 0).astype(np.int8)
    Yc = Yp[:, None]
    corr = ((V > 0) & Yc) | ((V < 0) & ~Yc)
    nz = V != 0
    tr_ = np.arange(W_n) < int(W_n * 2 / 3)
    te_ = ~tr_
    n_tr = nz[tr_].sum(0)
    h_tr = corr[tr_].sum(0)
    d = np.where(2 * h_tr >= n_tr, 1, -1).astype(np.int8)
    Vd = V * d
    cd = ((Vd > 0) & Yc) | ((Vd < 0) & ~Yc)
    n_te = nz[te_].sum(0)
    h_te = cd[te_].sum(0)
    z_te = (h_te - n_te / 2) / np.sqrt(n_te / 4)
    hit_te = h_te / np.maximum(n_te, 1)
    n_all = nz.sum(0)
    elig = np.isfinite(C) & (n_te >= 100)
    nt = int((np.isfinite(C) & (n_all >= 100)).sum())
    p_te = _erfc(np.abs(z_te) / math.sqrt(2))
    surv = elig & (z_te >= 1.96)
    bonf = elig & (p_te < 0.05 / max(nt, 1))

    mu = np.nanmean(X[tr_], 0)
    sdv = np.nanstd(X[tr_], 0)
    mu = np.where(np.isfinite(mu), mu, 0)
    sdv = np.where(np.isfinite(sdv) & (sdv > 0), sdv, 1)
    Zb = np.c_[np.nan_to_num((X - mu) / sdv), np.ones(W_n)]
    Ztr = Zb[tr_]
    ytr = Yp[tr_].astype(float)
    Lip = 0.25 * np.linalg.norm(Ztr, 2) ** 2 / len(ytr)
    w = np.zeros(Zb.shape[1])
    for _ in range(500):
        pr = 1 / (1 + np.exp(-(Ztr @ w)))
        w -= (Ztr.T @ (pr - ytr) / len(ytr) + 1e-3 * np.r_[w[:-1], 0]) / Lip
    pte = 1 / (1 + np.exp(-(Zb[te_] @ w)))
    yte = Yp[te_]
    ens_acc = float(np.mean((pte >= 0.5) == yte))
    ens_br = float(np.mean((pte - yte) ** 2))

    m1c = m1["c"]
    r1m_ = np.diff(np.log(m1c), prepend=np.log(m1c[0]))
    rs60 = rstd(r1m_, 60) / math.sqrt(60)
    ins, U, SD, Yi, Wi = {}, [], [], [], []
    for e in [max(60, round(W * f / 60) * 60) for f in (0.2, 0.4, 0.6, 0.8)]:
        ti = t0s + e - 60
        k = np.minimum(np.searchsorted(T1, ti), len(T1) - 1)
        St = m1c[k]
        sds = rs60[k] * np.sqrt(W - e - 2 * L / 3)
        okk = (T1[k] == ti) & (k >= 60) & np.isfinite(sds) & (sds > 0)
        ins[e] = float(np.mean(((St >= Kp) == Yp)[okk]))
        U.append(((St - Kp) / St)[okk])
        SD.append(sds[okk])
        Yi.append(Yp[okk].astype(float))
        Wi.append(np.arange(W_n)[okk])
    U, SD, Ya, WI = (np.concatenate(x) for x in (U, SD, Yi, Wi))
    tr_s = WI < int(W_n * 2 / 3)
    te_s = ~tr_s

    def logloss(P, y):
        P = np.clip(P, 1e-9, 1 - 1e-9)
        return -np.mean(y * np.log(P) + (1 - y) * np.log(1 - P))

    def ece_of(P, y):
        qs = np.quantile(P, np.linspace(0, 1, 11))
        bi = np.clip(np.digitize(P, qs[1:-1]), 0, 9)
        return float(sum((bi == b).mean() * abs(P[bi == b].mean() - y[bi == b].mean()) for b in range(10) if (bi == b).any()))

    GM = np.exp(np.linspace(np.log(0.3), np.log(5), 80))
    m_hat = float(GM[np.argmin([logloss(Phi(U[tr_s] / (g * SD[tr_s])), Ya[tr_s]) for g in GM])])
    ece_before = ece_of(Phi(U[te_s] / SD[te_s]), Ya[te_s])
    ece = ece_of(Phi(U[te_s] / (m_hat * SD[te_s])), Ya[te_s])

    tr_w = truths(a.asset, a.window, 250)
    Tr = sorted(tr_w)
    ref_url = f"{FAPI}/fapi/v1/indexPriceKlines?pair=XAUUSDT&interval=1m" if a.asset == "xau" else f"{BIN}/klines?symbol={ASSETS[a.asset]['sym']}&interval=1m"
    ref = pages(ref_url, Tr[0], Tr[-1] + W)
    Ks = np.array([ref.get(t, (np.nan, np.nan))[0] for t in Tr])
    Se = list(ThreadPoolExecutor(16).map(lambda t: twap(a.asset, t + W), Tr)) if L > 1 else [ref.get(t + W - 60, (np.nan, np.nan))[1] for t in Tr]
    dr = np.log(np.array(Se) / Ks)
    yr = np.array([tr_w[t] for t in Tr], float)
    ok_r = np.isfinite(dr)
    dr, yr = dr[ok_r], yr[ok_r]

    def ll(m_, s_):
        p_ = np.clip(Phi((dr - m_) / s_), 1e-12, 1 - 1e-12)
        return np.sum(yr * np.log(p_) + (1 - yr) * np.log(1 - p_))
    mb, sb = max(((m_, s_) for m_ in MU_GRID for s_ in SB_GRID), key=lambda g: ll(*g))
    agree = float(np.mean(Yp[mx] == Yx[mx])) if mx.any() else float("nan")

    # g=generated, w=windows, d=days, e=ensemble+calibration, s=signals (k=tf:indicator, d=trained sign, h=OOS hit, n=OOS n, z=OOS z), m=sigma multiplier, b=sigma_b log units vs real resolutions, o=mu_b log offset: P(Up)=Phi((d-o)/b)
    idx = np.argsort(-np.where(surv, z_te, -np.inf))[:30]
    sigs = [{"k": names[i], "d": int(d[i]), "h": round(float(hit_te[i]), 4), "n": int(n_te[i]), "z": round(float(z_te[i]), 3)} for i in idx if surv[i]]
    out = {"g": iso(t_run), "w": W_n, "d": a.days,
           "e": {"acc": round(ens_acc, 4), "br": round(ens_br, 4), "ece": round(float(ece), 4), "ins": ins},
           "s": sigs, "m": round(m_hat, 4), "b": sb, "o": mb}
    HOME.mkdir(parents=True, exist_ok=True)
    ef = HOME / f"edges-{a.asset}-{a.window}.json"
    ef.write_text(json.dumps(out))

    top = np.argsort(-np.where(elig, hit_te, -1))[:10]
    L_out = [
        f"market {a.asset} {a.window} rule {'TWAP' + str(L) + 's' if twap_ else 'point'} outcome proxy from 1m bars; windows {W_n} days {a.days} exact_1s_windows {int(mx.sum())} proxy_vs_exact_agree {agree:.3f}",
        f"tests {nt} directional; luck_expected_p05 {0.05 * nt:.0f}; oos_z>=1.96 survivors {int(surv.sum())}; bonferroni survivors {int(bonf.sum())}",
        "top10 OOS (name sign oos_hit n_oos z):",
    ]
    for i in top:
        L_out.append(f"  {names[i]} {int(d[i]):+d} {hit_te[i]:.3f} n={int(n_te[i])} z={z_te[i]:.2f}")
    L_out.append(f"ensemble_L2 oos_acc {ens_acc:.4f} oos_brier {ens_br:.4f} (baseline 0.25)")
    L_out.append("in-window acc by elapsed: " + " ".join(f"{e}s={ins[e]:.3f}" for e in ins))
    L_out.append(f"phi_calibration test_third ECE m=1 {ece_before:.4f} m={m_hat:.3f} {ece:.4f}")
    L_out.append(f"sigma_b_bps {sb * 1e4:.3f} mu_b_bps {mb * 1e4:+.3f} from {len(dr)} real resolutions (ref {ref_url.split('?')[1].split('&')[0]} {'1s twap60' if L > 1 else '1m close'})")
    L_out.append(f"wrote {ef}")
    L_out.append(f"runtime_s {time.time() - t_run:.1f}")
    print("\n".join(L_out))


def markets(a):
    now = time.time()
    ex = ThreadPoolExecutor(32)
    jobs = []
    for asset in ASSETS:
        for w, W in WINDOWS.items():
            base = int(now) // W * W
            for ts in (base, base + W):
                jobs.append((asset, w, ts, W))
    found = list(ex.map(lambda j: (j, market(f"{j[0]}-updown-{j[1]}-{j[2]}")), jobs))
    live = [(j, mk) for j, mk in found if mk and now < j[2] + j[3]]
    bk = [(j, mk, ex.submit(book, json.loads(mk["clobTokenIds"])[0]), ex.submit(book, json.loads(mk["clobTokenIds"])[1])) for j, mk in live]
    L_out = ["slug | phase | left_s | up bid/ask | down bid/ask | spread_up | top_up_ask | fee@ask_up"]
    for j, mk, bu_f, bd_f in bk:
        asset, w, ts, W = j
        bu, au = bu_f.result()
        bd, ad = bd_f.result()
        phase = "open" if now >= ts else "next"
        fs = mk.get("feeSchedule")
        if au and bu:
            top = f"{au[0][1]:.0f}@{au[0][0]}"
            ask = au[0][0]
            info = f"{bu[0][0]}/{ask} {bd[0][0] if bd else 'NA'}/{ad[0][0] if ad else 'NA'} spread={ask - bu[0][0]:.3f} top_up_ask={top} fee@ask_up={fee(ask, fs)}"
        else:
            info = "no two-sided book (market paused, closed or thin)"
        L_out.append(f"{mk['slug']} | {phase} | {ts + W - now:.0f} | {info}")
    if len(L_out) == 1:
        L_out.append("no open or next windows right now (check market hours)")
    print("\n".join(L_out))


def log(a):
    m = market(a.slug)
    mid = None
    if m:
        bids, asks = book(json.loads(m["clobTokenIds"])[0])
        if bids and asks:
            mid = (bids[0][0] + asks[0][0]) / 2
    # t=unix time, s=slug, p=agent P(up), d=side, x=price per share, m=market P(up) mid, n=note
    rec = {"t": int(time.time()), "s": a.slug, "p": a.p, "d": a.side, "x": a.price, "m": mid, "n": a.note}
    HOME.mkdir(parents=True, exist_ok=True)
    with JOURNAL.open("a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(json.dumps(rec))


def score(a):
    rs = rows()
    slugs = sorted({r["s"] for r in rs})
    mk = dict(zip(slugs, ThreadPoolExecutor(12).map(market, slugs)))
    n = nm = 0
    ba = bm = ll = 0.0
    modes = {}
    for r in rs:
        m = mk.get(r["s"])
        if not m or not m.get("closed"):
            continue
        op = [float(x) for x in json.loads(m["outcomePrices"])]
        if op[0] not in (0.0, 1.0):
            continue
        y = int(op[0] == 1.0)
        if "v" not in r:
            n += 1
            p = min(max(r["p"], 1e-6), 1 - 1e-6)
            ba += (r["p"] - y) ** 2
            ll += -(y * math.log(p) + (1 - y) * math.log(1 - p))
            if r.get("m") is not None:
                nm += 1
                bm += (r["m"] - y) ** 2
        if r["d"] in ("up", "down") and r.get("x") is not None:
            pnl, win = leg_pnl(r, m)
            s = modes.setdefault(r.get("v", "log"), [0, 0, 0.0, 0.0])
            s[0] += 1
            s[1] += win
            s[2] += pnl
            s[3] += r["x"] * r.get("q", 1)
    if n:
        print(f"resolved_log {n} brier_agent {ba / n:.4f} brier_mkt {bm / nm if nm else float('nan'):.4f} "
              f"(n_mkt={nm}) logloss_agent {ll / n:.4f}")
    names = {"p": "paper", "l": "live", "log": "log"}
    for k, (legs, hits, pnl, staked) in sorted(modes.items()):
        print(f"{names[k]} legs {legs} hit_rate {hits / legs:.3f} staked_usd {staked:.2f} "
              f"pnl_usd {pnl:+.4f} pnl_per_leg {pnl / legs:+.4f}")
    if not n and not modes:
        print("resolved 0")


def walk(levels, q=None, usd=None):
    got = paid = 0.0
    for p, sz in levels:
        take = min(sz, q - got if q else (usd - paid) / p)
        got += take
        paid += take * p
        if got >= (q or math.inf) - 1e-9 or paid >= (usd or math.inf) - 1e-9:
            return paid / got, got
    return None, got


def p_fav(sym, T, i):
    k = jget(f"{BIN}/klines?symbol={sym}&interval=1s&startTime={(int(time.time()) - 660) * 1000}&limit=1000") or []
    lp = {r[0] // 1000: math.log(float(r[4])) for r in k}
    now = max(lp, default=0)
    if T not in lp or now - T > 300:
        return None
    r = [lp[s + 1] - lp[s] for s in range(now - 600, now) if s in lp and s + 1 in lp]
    sg, tau, yt = math.sqrt(sum(v * v for v in r) / max(len(r), 1)), T + 300 - now, lp[now] - lp[T]
    if tau >= 60:
        mean, var = yt, sg * sg * (tau - 60 + 20.3)
    else:
        real = [lp[s] - lp[T] for s in range(T + 241, now + 1) if s in lp]
        mean = (sum(real) * (60 - tau) / max(len(real), 1) + tau * yt) / 60
        var = sg * sg * tau * (tau + 1) * (2 * tau + 1) / (6 * 3600)
    pu = float(Phi(mean / math.sqrt(var))) if var > 0 else float(mean >= 0)
    return round(pu if i == 0 else 1 - pu, 4)


def snipe(a):
    W = WINDOWS[a.window]
    T = int(time.time()) // W * W
    end = T + W
    time.sleep(max(0.0, end - a.tau - time.time()))
    k = end - time.time()
    if k < a.tau - 5:
        return emit("late", f"{k:.0f}s left")
    slug = f"{a.asset}-updown-{a.window}-{T}"
    mk = market(slug)
    if not mk:
        return emit("no_market", slug)
    tok = json.loads(mk["clobTokenIds"])
    while True:
        bk = list(ThreadPoolExecutor(2).map(book, tok))
        asks = [b[1][0][0] if b[1] else 0.0 for b in bk]
        i = int((bk[1][0] or [(0,)])[0][0] > (bk[0][0] or [(0,)])[0][0])
        if a.lo <= asks[i] < a.hi or time.time() > end - 3:
            break
        time.sleep(1)
    x, q = walk(bk[i][1], usd=a.usd) if a.lo <= asks[i] < a.hi else (None, 0.0)
    r = {"s": slug, "t": int(time.time()), "k": round(end - time.time(), 1), "a": asks, "d": ("up", "down")[i],
         "x": x and round(x, 4), "q": round(q, 4), "f": x and p_fav(ASSETS[a.asset]["sym"], T, i)}
    if x and (r["f"] or 0) < x + fee(x, mk.get("feeSchedule")) + a.mg:
        r["x"] = None
    if r["x"] and q >= float(mk.get("orderMinSize") or 0):
        lo, c = None, {}
        while time.time() < end - 1:
            time.sleep(2)
            bids = book(tok[i])[0]
            if not bids:
                continue
            lo = min(lo or 1.0, bids[0][0])
            for s in STOPS:
                if str(s) not in c and bids[0][0] < s:
                    c[str(s)] = round(walk(bids, q=q)[0] or 0.0, 4)
        r |= {"b": lo, "c": c}
    write([r], SNIPE)
    emit("paper", slug, **r)


def snipe_score(a):
    rs = [json.loads(x) for x in SNIPE.read_text().splitlines() if x.strip()] if SNIPE.exists() else []
    rs = [r for r in rs if r.get("x") and "c" in r and a.lo <= r["a"][r["d"] == "down"] < a.hi]
    mk = dict(zip([r["s"] for r in rs], ThreadPoolExecutor(12).map(market, [r["s"] for r in rs])))
    done = []
    for r in rs:
        m = mk.get(r["s"]) or {}
        op = json.loads(m.get("outcomePrices") or "[]")
        if m.get("closed") and op in (["1", "0"], ["0", "1"]):
            done.append((r, (op[0] == "1") == (r["d"] == "up"), m.get("feeSchedule")))
    if not done:
        return print(f"resolved 0 of {len(rs)} paper trades in [{a.lo}, {a.hi})")
    show("all", done)
    show(f"delphi filter (fair >= price + fee + {a.mg})",
         [z for z in done if z[0].get("f") is not None and z[0]["f"] >= z[0]["x"] + fee(z[0]["x"], z[2]) + a.mg])


def show(tag, done):
    if not done:
        return print(f"{tag}: 0 trades")
    n, wins = len(done), sum(w for _, w, _ in done)
    cost = [r["q"] * (r["x"] + fee(r["x"], fs)) for r, _, fs in done]
    hold = [r["q"] * w - c for (r, w, _), c in zip(done, cost)]
    days = max((done[-1][0]["t"] - done[0][0]["t"]) / 86400, 1 / 288)
    be = sum(r["x"] + fee(r["x"], fs) for r, _, fs in done) / n
    print(f"{tag}: paper trades {n} ({n / days:.0f}/day) wins {wins} ({100 * wins / n:.2f}%) breakeven {100 * be:.2f}% "
          f"staked ${sum(cost):.2f} pnl ${sum(hold):+.2f} (${sum(hold) / n:+.3f}/trade, ${sum(hold) / days:+.2f}/day)")
    for s in STOPS:
        k = str(s)
        v = [r["q"] * (r["c"][k] - fee(r["c"][k], fs)) - c if k in r["c"] else h
             for (r, _, fs), c, h in zip(done, cost, hold)]
        fired = [(r, w) for r, w, _ in done if k in r["c"]]
        print(f"  cash out below {s}: fired {len(fired)} (would have won {sum(w for _, w in fired)}) "
              f"pnl ${sum(v):+.2f} vs hold ${sum(hold):+.2f}")


def main():
    p = argparse.ArgumentParser(prog="delphi")
    sub = p.add_subparsers(dest="cmd", required=True)
    s_ = sub.add_parser("snap")
    s_.add_argument("target", nargs="?", default="now")
    s_.add_argument("--asset", choices=list(ASSETS))
    s_.add_argument("--window", choices=list(WINDOWS))
    s_.add_argument("--json", action="store_true")
    e_ = sub.add_parser("edge")
    e_.add_argument("--asset", default="btc", choices=list(ASSETS))
    e_.add_argument("--window", default="5m", choices=list(WINDOWS))
    e_.add_argument("--days", type=int, default=30)
    sub.add_parser("markets")
    l_ = sub.add_parser("log")
    l_.add_argument("--slug", required=True)
    l_.add_argument("--p", type=float, required=True)
    l_.add_argument("--side", choices=["up", "down", "none"], required=True)
    l_.add_argument("--price", type=float)
    l_.add_argument("--note", default="")
    sub.add_parser("score")
    d_ = sub.add_parser("decide")
    d_.add_argument("target", nargs="?", default="now")
    d_.add_argument("--asset", required=True, choices=list(ASSETS))
    d_.add_argument("--window", required=True, choices=list(WINDOWS))
    j_ = sub.add_parser("judge")
    j_.add_argument("--decision", required=True)
    j_.add_argument("--llm", default="")
    j_.add_argument("--fresh", default="")
    t_ = sub.add_parser("trade")
    t_.add_argument("--decision", required=True)
    t_.add_argument("--live", action="store_true")
    n_ = sub.add_parser("snipe")
    n_.add_argument("--asset", default="btc", choices=list(ASSETS))
    n_.add_argument("--window", default="5m", choices=list(WINDOWS))
    n_.add_argument("--tau", type=float, default=90)
    n_.add_argument("--lo", type=float, default=0.81)
    n_.add_argument("--hi", type=float, default=0.99)
    n_.add_argument("--usd", type=float, default=5)
    n_.add_argument("--mg", type=float, default=0.02)
    m_ = sub.add_parser("snipe-score")
    m_.add_argument("--lo", type=float, default=0.81)
    m_.add_argument("--mg", type=float, default=0.02)
    m_.add_argument("--hi", type=float, default=0.99)
    a = p.parse_args()
    {"snap": cmd_snap, "decide": cmd_decide, "judge": cmd_judge, "trade": cmd_trade, "edge": edge,
     "markets": markets, "log": log, "score": score, "snipe": snipe, "snipe-score": snipe_score}[a.cmd](a)


if __name__ == "__main__":
    main()
