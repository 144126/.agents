---
name: delphi
description: Call Polymarket up/down markets (btc/eth/sol/xrp 5m-4h, gold xau 15m/1h) as UP, DOWN or NO BET. Produces a live report with 540 indicators on 6 timeframes, the Chainlink price to beat, TWAP or point fair value, the order book, taker fees, edge and quarter-kelly, plus a journal that scores every call. Use for any polymarket.com/event/*-updown-* link, or "call the next btc 5m / gold 15m window".
---

# delphi

The engine and playbook for Polymarket up/down windows. The `delphi` agent (`~/.claude/agents/delphi.md`, opus 5.5, max effort) runs on it.

## run
```
uv run --script ~/.agents/skills/delphi/delphi.py markets          # open windows to choose from
uv run --script ~/.agents/skills/delphi/delphi.py snap <url|slug> [--json]
uv run --script ~/.agents/skills/delphi/delphi.py snap now|next --asset btc|eth|sol|xrp|xau --window 5m|15m|1h|4h
uv run --script ~/.agents/skills/delphi/delphi.py edge --asset btc --window 5m --days 30
uv run --script ~/.agents/skills/delphi/delphi.py log --slug <slug> --p 0.55 --side up|down|none --price 0.50 --note "..."
uv run --script ~/.agents/skills/delphi/delphi.py score
uv run --script ~/.agents/skills/delphi/delphi.py snipe [--legs btc/5m/30/0.85/0.95/-1/l,eth/5m/30/0.85/0.95/-1/l,btc/15m/90/0.85/0.95/-1/p --usd 1 --frac 0.05]   # each leg = asset/window/tau/lo/hi/mg/l|p: first time the favourite ask is in [lo, hi) with <= tau s left; mg -1 = no filter; p = paper only; live needs ~/.config/delphi/LIVE
uv run --script ~/.agents/skills/delphi/delphi.py snipe-score   # per rule tag (tau/lo/hi/mg) and live fills
```
- `edge` is the validation run and writes `edges-<asset>-<window>.json`. Re-run it daily for each market you trade; `snap` reads it.
- `score` grades the journal against the market.
- data lives in `~/.local/share/delphi/` (journal.jsonl, edges-*.json); `DELPHI_HOME` overrides it.
- agent: `claude --agent delphi "next btc 5m"`, or in any session: "use delphi on <url>".
- speed: `snap` and `markets` take ~2.5 s. `edge` takes ~65 s, because it pulls ~750 real resolutions from gamma.

## unattended loop (pi + deepseek v4.1 flash)
- `decide --asset A --window W` prints one JSON decision and is the only source of truth.
  - gates, in order: window live, fresh data with a two-sided book (spread <= 0.03), no mixed sources, not in the proxy zone, no high-impact usd event within the window +-2 min (fails closed if the calendar is down), >= 20 s left.
  - then BUY_BOTH if both asks + fees <= 0.99 (paper only), else the best side with edge >= 0.02 after fee, else NO_BET. 5 shares.
- `run_window.sh A W`, from cron (`cron.txt`; gold 15m every minute at :20, btc lines commented out):
  1. `decide`;
  2. on a buy, pi runs with no tools and `pi/operator.md`, and must copy the decision exactly;
  3. `decide` runs again and `judge` requires the same action and slug at an ask no worse;
  4. `trade` executes.
  - one line per run goes to `~/.local/share/delphi/runs.log`.
- `trade` is paper by default: one trade per slug, filled at the ask, journal mode `p`.
- live needs every gate to pass:
  - the live switch is on: `DELPHI_LIVE=1` placed before the script path in the cron line (cron doesn't inherit the shell's env);
  - `~/.config/delphi/live.env` exists with mode 600 and holds POLYMARKET_PRIVATE_KEY, POLYMARKET_WALLET, POLYMARKET_RELAYER_KEY, POLYMARKET_RELAYER_ADDRESS;
  - there is no `~/.config/delphi/KILL`;
  - geoblock says not blocked (this laptop: NG, ok);
  - the decision is < 10 s old;
  - the slug hasn't traded yet;
  - `limits.json` allows it (Ed: $3 a trade, $5/day loss stop, 5 shares).
- snipe real money: `touch ~/.config/delphi/LIVE` (paper: `rm` it). Needs live.env (private key + wallet; relayer optional), no KILL, geoblock open, stake <= max_trade_usd, today's live snipe loss < daily_loss_usd. Orders are FAK BUY by dollar amount (`--usd`, default $1) up to best ask + 2c; rows get v l, o, u, g shares, y usd. Market orders go down to $1 (the 5-share minimum is for limit orders); winners auto-redeem about a minute after close (auto-redeem operator approved).
- snipe evidence (28-day tape 2026-10-08..11-05, 8,039 windows, first touch in time order, A/B = halves): 90s/81-99c is breakeven (A -0.23%, B +0.37% roi); <=30s/85-95c no filter A +1.69%, B +1.59% (lag 0), +5.9/+4.6% with 2s lag + 1c slip; >=95c ~0%; the fair-value filter and the late 35-81c rule were not stable across halves (dropped). Model vs market log loss: market wins at every tau, model coef ~0. Trap: sort prints by time within a window before taking the first touch (a side-then-time sort picked Up first and faked +5% roi).
- other markets, same 30s/85-95c rule (14-day tapes to 2026-11-05, halves A/B, lag 0): eth 5m +1.74/+1.97% (replicates btc), sol 5m +1.94/-1.21% (skip), xrp 5m -3.10/-1.84% (skip); btc 15m best at 90s/85-95c +3.54/+3.54% (found by scanning, so paper only). Depth: median $199 bought within 1c in the 5 s after a btc entry. Order helper start (uv + sign-in) takes ~10.7 s, so it is armed at job start.
- BUY_BOTH never goes live.
- kill switch: `touch ~/.config/delphi/KILL`. grade results with `delphi.py score` (paper and live are scored separately).
- `trade_live.py` (polymarket-client 0.16.0): probe place+cancel verified 2026-11-05; urllib needs a User-Agent (403 otherwise). Magic export: Settings > Account > Start Export (reveal.magic.link). Wallet = Settings > Profile "Address" (proxy), signer differs.
  - unverified: the GTD expiration units and the response fields.
  - the first live order must be supervised by hand before cron goes live.

## market rules (verified 2026-11-03)
- the slug is `<asset>-updown-<window>-<start_unix>`, and the number is the window start.
  - windows are not contiguous in Gamma, so probe; never assume the next one exists.
  - each market's rule is read from Gamma (`cryptoMarketConfig.twapEnabled`/`twapLookbackSeconds`, with the description as fallback).
- btc 5m: Up iff the Chainlink BTC/USD TWAP60 at window end >= the price at start; ties go to Up.
  - K = Polymarket crypto-price `openPrice`, S = RTDS chainlink. Both are exact.
- xau 15m: Up iff the Chainlink XAU/USD forex-stream price at end >= the price at start (point price, no TWAP).
  - Chainlink gold isn't readable (rtds xau/usd is empty, crypto-price XAU returns "no report", and the page has no price to beat).
  - so K = the open of Binance's XAUUSDT index-price 1m bar at window start, and S = the live `premiumIndex` indexPrice.
  - against 250 real resolutions this agrees 98.8% of the time. sigma_b = 1.9 bps.
  - flip rate by |end distance|: 8% at 0-1 bps, <= 2% beyond 1 bps.
  - other proxies: perp 97.6%, paxg 94.8%.
  - gold has market hours: windows go missing around the weekend and the daily break.
- calibration: the fitted sigma multiplier m is 0.905 for btc (ece 0.032 -> 0.023) and 0.938 for xau (0.040 -> 0.035). `sigma_b` is added to the fair-value variance.
- `PROXY ZONE` (|ln S/K| < 2 sigma_b: btc < 7.9 bps, xau < 3.8 bps) forces NO BET.
- open issue (btc):
  - the best proxy (binance 1s TWAP60) agrees with resolutions only 89.5% of the time (sigma_b 3.9 bps).
  - the start reference is unverified: is K the crypto-price openPrice, or the TWAP60 at window start? polymarket's own open/close agree only 85.3%.
  - in the last 60 s, the realized part of the TWAP uses only the few rtds ticks from a 1.5 s connection.
  - until this is fixed, treat btc in-window edges under ~10 bps as noise.
- fees (`crypto_fees_v2`): taker fee = shares x 0.07 x p x (1-p), rounded to 5 dp, so at most 1.75c/share at p = 0.50.
  - makers pay 0 and get a 20% rebate.
  - book tick 0.01, minimum 5 shares.

## what the numbers say (`edge`, 30 days, 2026-11-03)
- btc 5m, pre-window:
  - 432 tests gave 37 walk-forward survivors, vs ~22 expected by luck, and 0 after bonferroni.
  - best out-of-sample ~0.53. the l2 ensemble scores acc 0.506 and brier 0.2565, worse than the 0.25 coin.
  - no robust pre-window edge.
- btc 5m, in-window: sign(S-K) is right 0.67 at 60 s, 0.75 at 120 s, 0.83 at 180 s, 0.93 at 240 s.
- xau 15m: ensemble brier 0.250 (no edge). in-window sign is right 0.67 at 180 s and 0.87 at 720 s.
- so the only real edge is in-window fair value against a mispriced book, after fees. NO BET is the default.

## facts kept from the other skills
- polymarket-api: ids run slug -> event -> market (condition_id) -> clobTokenIds (Up, Down); the book is CLOB `/book?token_id=`. its old "zero taker fees" line was wrong for crypto and is fixed.
- prediction-market-strategy: fee-aware selection; quarter-kelly with a hard cap; the favourite-longshot bias (cheap tails overpriced) is the durable catalogued edge.
- prediction-market-live-ops: a backtest's EV on passive fills is only an upper bound; maker strategies validate only on fill-conditioned live results. pre-declare a kill rule, e.g. stop after 100 logged calls if the agent's brier >= the market's.
- walk-forward-validation: never k-fold a time series; purge or embargo overlapping windows; judge out of sample only.
- market-microstructure-traditional: spread = adverse selection + inventory + costs. resting orders fill most often when they're wrong.
- dropped as irrelevant here:
  - kalshi-*
  - llmquant-* (they need LLMQuant Data)
  - wind-find (china a-shares)
  - market-microstructure (solana dex)
  - vectorbt, ta-lib, ohlcv-processing, strategy-framework (the engine covers them)

## book
`murphy.md`: John Murphy, *Technical Analysis of the Financial Markets*, read in full and distilled. The applied section comes first, then chapter notes with pdf page numbers for pulling the source text.

## traps
- polymarket hosts need curl (python urllib gets blocked); data.chain.link is behind a vercel wall for curl.
- rtds sends an empty first frame; skip it or the stream aborts.
- gamma `orderPriceMinTickSize` says 0.001, but the live book steps by 0.01.
- gamma `fee` can be null (xau); use `feeSchedule`.
- binance usd-m has no 1s klines; gold 1s comes from paxg spot. `openInterestHist` can be empty for the gold perp, which prints NA.
- a thin book reads 0.01/0.99 (spread 0.98). that is no market.
- a failed feed used to mix the strike's source with the live price's source. in the fault tests this produced fake +30-point edges.
  - snap now tags each price's source family and prints `MIXED SOURCES ...: no bet` on any mismatch.
  - test it with `DELPHI_FAIL=rtds|index`.
  - if rtds ever starts returning xau ticks, K must move to chainlink too, or every gold call will read MIXED.
- ta-lib 0.8.3 has a cp314 wheel; the first run adds ~100 MB to the uv cache.
