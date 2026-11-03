# /// script
# requires-python = ">=3.14,<3.15"
# dependencies = ["polymarket-client==0.16.0"]
# ///
import json
import os
import sys

from polymarket import RelayerApiKey, SecureClient


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


main()
