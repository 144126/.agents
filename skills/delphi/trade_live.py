# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["polymarket-client==0.16.0"]
# ///
import argparse
import json
import os
import stat
import sys
import time
import urllib.request

from polymarket import RelayerApiKey, SecureClient
from polymarket.models.clob.order_response import AcceptedOrder

ENV = os.path.expanduser("~/.config/delphi/live.env")
KEYS = ("POLYMARKET_PRIVATE_KEY", "POLYMARKET_WALLET")
GAMMA = "https://gamma-api.polymarket.com"
WINDOWS = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400}


def main():
    job = json.load(sys.stdin)
    c = SecureClient.create(
        private_key=os.environ["POLYMARKET_PRIVATE_KEY"],
        wallet=os.environ["POLYMARKET_WALLET"],
        api_key=RelayerApiKey(key=os.environ["POLYMARKET_RELAYER_KEY"], address=os.environ["POLYMARKET_RELAYER_ADDRESS"]),
    )
    out = []
    for g in job["legs"]:
        r = c.place_limit_order(asset_id=g["tok"], side="BUY", price=str(g["x"]), size=str(g["q"]), expiration=job["end"])
        ok = type(r).__name__ == "AcceptedOrder"
        out.append({"d": g["d"], "o": getattr(r, "order_id", None), "u": "accepted" if ok else "rejected"})
    print(json.dumps(out))


def load_env():
    if not os.path.isfile(ENV):
        raise SystemExit(f"Missing {ENV}: create it with the four POLYMARKET_ keys and run chmod 600 on it.")
    if stat.S_IMODE(os.stat(ENV).st_mode) != 0o600:
        raise SystemExit(f"{ENV} must be mode 600: run chmod 600 {ENV}")
    env = {}
    with open(ENV) as f:
        for line in f:
            k, sep, v = line.strip().partition("=")
            if sep:
                env[k] = v.strip().strip("'\"")
    empty = [k for k in KEYS if not env.get(k)]
    if empty:
        raise SystemExit(f"Fill these in {ENV}: {', '.join(empty)}")
    return env


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=10) as r:
        return json.load(r)


def live_token(asset, window):
    W = WINDOWS[window]
    slug = f"{asset}-updown-{window}-{int(time.time()) // W * W}"
    evs = get_json(f"{GAMMA}/events?slug={slug}")
    if not evs:
        raise SystemExit(f"No live {asset} {window} window right now ({slug} not listed). Retry during market hours.")
    mk = evs[0]["markets"][0]
    return slug, json.loads(mk["clobTokenIds"])[json.loads(mk["outcomes"]).index("Up")]


def fix_hint(e):
    msg = str(e).lower()
    if any(s in msg for s in ("signature", "private", "api key", "unauthorized", "401")):
        return "Bad key: check POLYMARKET_PRIVATE_KEY and the relayer key/address in live.env."
    if "wallet" in msg:
        return "Wrong wallet type: check POLYMARKET_WALLET matches the private key's wallet."
    if "allowance" in msg or "approv" in msg:
        return "Missing approval: run setup_trading_approvals for this wallet."
    if "balance" in msg or "insufficient" in msg:
        return "No balance: deposit pUSD to POLYMARKET_WALLET."
    return f"Probe failed ({type(e).__name__}): {str(e)[:200]}"


def probe(asset, window):
    env = load_env()
    try:
        blocked = get_json("https://polymarket.com/api/geoblock").get("blocked") is not False
    except Exception:
        raise SystemExit("Geoblock check failed: cannot reach polymarket.com. Check the network and retry.")
    if blocked:
        raise SystemExit("Polymarket blocks this location. Do not trade from here.")
    try:
        slug, tok = live_token(asset, window)
        print(f"window {slug}")
        rk = env.get("POLYMARKET_RELAYER_KEY") and RelayerApiKey(key=env["POLYMARKET_RELAYER_KEY"], address=env["POLYMARKET_RELAYER_ADDRESS"])
        c = SecureClient.create(private_key=env["POLYMARKET_PRIVATE_KEY"], wallet=env["POLYMARKET_WALLET"], api_key=rk or None)
        r = c.place_limit_order(asset_id=tok, side="BUY", price="0.01", size="5", post_only=True)
        if not isinstance(r, AcceptedOrder):
            raise SystemExit(f"Order rejected by Polymarket: {r}. Fix the reason shown, then retry.")
        print(f"placed {r.order_id} status {r.status}")
        x = c.cancel_order(order_id=r.order_id)
        print(f"cancel canceled={x.canceled} not_canceled={x.not_canceled}")
        print(f"collateral balance (raw): {c.get_balance_allowance(asset_type='COLLATERAL').balance}")
    except Exception as e:
        raise SystemExit(fix_hint(e))


def fak():
    e = os.environ
    rk = e.get("POLYMARKET_RELAYER_KEY") and RelayerApiKey(key=e["POLYMARKET_RELAYER_KEY"], address=e["POLYMARKET_RELAYER_ADDRESS"])
    c = SecureClient.create(private_key=e["POLYMARKET_PRIVATE_KEY"], wallet=e["POLYMARKET_WALLET"], api_key=rk or None)
    line = sys.stdin.readline()
    if not line.strip():
        return
    j = json.loads(line)
    try:
        r = c.place_market_order(asset_id=j["tok"], side="BUY", amount=str(j["usd"]), max_price=str(j["m"]), order_type="FAK")
    except Exception as x:
        return print(json.dumps({"o": None, "u": f"error: {type(x).__name__}: {str(x)[:160]}", "g": 0.0, "y": 0.0}))
    ok = isinstance(r, AcceptedOrder)
    print(json.dumps({"o": getattr(r, "order_id", None), "u": getattr(r, "status", None) if ok else f"rejected: {r}"[:200],
                      "g": float(r.taking_amount or 0) if ok else 0.0, "y": float(r.making_amount or 0) if ok else 0.0}))


if sys.argv[1:2] == ["fak"]:
    fak()
elif sys.argv[1:2] == ["probe"]:
    ap = argparse.ArgumentParser(prog="trade_live.py probe")
    ap.add_argument("--asset", required=True)
    ap.add_argument("--window", required=True, choices=WINDOWS)
    a = ap.parse_args(sys.argv[2:])
    probe(a.asset, a.window)
else:
    main()
