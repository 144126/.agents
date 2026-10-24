---
name: mt5
description: Backtest an Expert Advisor in MetaTrader 5 on this machine. Use when the user says backtest, MT5 tester, run the EA, or names a .mq5 / .ex5 to test.
---

# mt5

Wine install: `/home/ed/.wine/drive_c/Program Files/MetaTrader 5`

Account: **293212**, server `EGlobalTrade-Demo` (= Markets4you, E-Global Trade & Finance). Tester ignores `Leverage=`: always 1:4000 (checked 2026-10-24). Only demo on this box. `Config/common.ini` already has that login.

Gold costs: contract 100 oz, 0.01 lot = $1 per $1 move. Commission $7 per lot, charged on entry. Spread median $0.09, p90 $0.14 (real ticks).
BTCUSD: 1 lot = 1 BTC, point 0.01, margin rate 0.5% (= 1:200, fixed by symbol), spread median $27 p90 $43, commission 0.
Stored M1 bars have spread ~0, so Model=0/1 understate spread. Use Model=4; the tester downloads real ticks from the server (2025+ available).

## Compile

Copy the `.mq5` to `MQL5/Experts/`. Write `C:\windows\temp\compile-<name>.bat`:

```
@echo off
cd /d "C:\Program Files\MetaTrader 5"
MetaEditor64.exe /compile:"C:\Program Files\MetaTrader 5\MQL5\Experts\<Name>.mq5" /log
```

`WINEPREFIX=/home/ed/.wine wine cmd /c 'C:\windows\temp\compile-<name>.bat'`

Log is utf-16 next to the source. Gate is `0 errors`. Copy `.ex5` back to the repo.

## Tester ini

`Leverage=4000`, `Deposit=10000`, `Model=4` (real ticks), `Visual=0`, `ShutdownTerminal=1`.

**No `Login=` line.** Adding it on a portable copy made the tester print 1:100.

Tick idea: only months that have `Bases/EGlobalTrade-Demo/ticks/<SYM>/*.tkc`. Model=0 invents ticks from bars. That is a lie for tick ideas.

Gold here: 3 digits. 1 point = $0.001. $0.30 = 300 points. $0.90 = 900 points.

## Run

```bash
cp tester.ini "/home/ed/.wine/drive_c/windows/temp/<name>.ini"
cd "/home/ed/.wine/drive_c/Program Files/MetaTrader 5"
xvfb-run -a -s "-screen 0 1024x768x24" \
  env WINEPREFIX=/home/ed/.wine \
  wine terminal64.exe /config:"C:\windows\temp\<name>.ini"
```

Fake screen. Not on the user's display. MT5 has no true headless tester; this is the hide.

If `terminal64.exe` is already open, still use xvfb. Do not launch a second copy on `:0`. Two terminals sharing Bases can lock tick files (error 32).

Do not use a portable `mt5p` copy unless it has its own Bases. That printed 1:100.

## Report

Before you quote money, the tester log must show `'293212': authorized`. The tester prints leverage 1:4000 even with `Leverage=1000`; margin only matters for big lots.

Do not attach over Ind9 / Kronos / JevObi. Do not invent ticks. Do not retune SL/TP to go green. Do not write an HTML report.
