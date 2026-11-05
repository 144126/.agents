import json, subprocess, sys, gzip, time
from concurrent.futures import ThreadPoolExecutor
asset, win, t0, t1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
W = {"5m": 300, "15m": 900}[win]
def curl(u):
    for _ in range(4):
        o = subprocess.run(["curl","-s","-m","30","-A","Mozilla/5.0",u],capture_output=True,text=True).stdout
        try: return json.loads(o)
        except Exception: time.sleep(1)
    return None
def one(T):
    ev = curl(f"https://gamma-api.polymarket.com/events?slug={asset}-updown-{win}-{T}")
    if not ev: return None
    m = ev[0]["markets"][0]; tr, cur = [], None
    for _ in range(8):
        j = curl(f"https://data-api.polymarket.com/v2/trades?condition={m['conditionId']}&limit=1000" + (f"&cursor={cur}" if cur else "")) or {}
        tr += [(r["timestamp"], r["outcome_index"], r["price"], r["size"]) for r in j.get("data") or [] if r["side"] == "BUY"]
        cur = (j.get("pagination") or {}).get("next_cursor")
        if not cur: break
    return json.dumps({"T": T, "op": m.get("outcomePrices"), "c": m.get("closed"), "tr": sorted(tr)})
n = 0
with gzip.open(f"tape_{asset}_{win}_{t0}.jsonl.gz", "wt") as f, ThreadPoolExecutor(14) as ex:
    for s in ex.map(one, range(t0, t1, W)):
        if s: f.write(s + "\n"); n += 1
        if n % 500 == 0: print(n, flush=True)
print("done", n, flush=True)
