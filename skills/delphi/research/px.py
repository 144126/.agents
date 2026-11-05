import json, subprocess, sys, array, math, time
from concurrent.futures import ThreadPoolExecutor
sym, t0, t1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
def get(s):
    for _ in range(5):
        o = subprocess.run(["curl","-s","-m","20",f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1s&startTime={s*1000}&limit=1000"],capture_output=True,text=True).stdout
        try: return [(r[0] // 1000, float(r[4])) for r in json.loads(o)]
        except Exception: time.sleep(1)
    return []
a = array.array("d", [math.nan]) * (t1 - t0)
with ThreadPoolExecutor(10) as ex:
    for rows in ex.map(get, range(t0, t1, 1000)):
        for s, c in rows:
            if 0 <= s - t0 < t1 - t0: a[s - t0] = c
open(f"px_{sym}_{t0}.bin", "wb").write(a.tobytes()); print("done", flush=True)
