# murphy, distilled

source: John J. Murphy, *Technical Analysis of the Financial Markets* (NYIF 1999), read in full.
pdf: `~/Downloads/Technical-Analysis-of-the-Futures-Markets-John-J.-Murphy.pdf` (586 pages; `pN` below = pdf page).
pull exact pages when a call needs depth: `pdftotext -f N -l M <pdf> - | grep -v -i fxborssa`
grep a topic: `pdftotext <pdf> - | grep -n -i -C3 'failure swing'`

## applying murphy to short up/down binaries: btc 5m, gold 15m (read first)

the market is a binary on a 5-60 minute move (exact rule per market in SKILL.md and the snap header). murphy's tools give a tilt, not a forecast. weigh them in this order:

1. **regime first** (ch4, ch9, ch15, app b). markets trend ~30% of the time (wilder) and range 1/3-1/2 of it.
   - trend mode: adx rising/>25, high efficiency ratio, aligned ma ribbon, ht_trendmode=1. lean with the trend and ignore "overbought".
   - range mode: adx falling/<20, high choppiness. fade extremes (bands, levels), but only with a reversal sign (rsi failure swing, divergence, a morris-filtered candle), and target the mean (vwap, bb mid, poc).
2. **top-down** (ch8, ch10, ch14, ch16). 1h/15m set the bias, 5m/1m the setup, 1s plus order flow the trigger. take a lower-timeframe signal only when the higher one agrees. conflicting frames = no bet.
3. **levels** (ch4, app b). the nearest swing high/low, round numbers (1000s, then 500s, 100s), vwap, poc and value-area edges, bollinger/keltner bands.
   - measure distance in sigma-of-the-remaining-window units. a level inside the 1-sigma range tends to cap the move.
   - a decisive break through a level on volume tends to run to the next one.
4. **flow confirms price** (ch2, ch7).
   - breakouts need a taker-buy/cvd burst. price up with cvd/obv falling = suspect.
   - perp oi rising with price = fresh positioning (fuel). price up with oi falling = short covering (runs out).
   - oi built up during a range makes the break violent; liquidations of the trapped side feed on themselves.
5. **momentum leads** (ch10). roc, macd histogram and rsi turn before price. divergence at an extreme is the best oscillator signal, but it never justifies fighting a fresh breakout.
6. **sentiment only at extremes** (ch7, ch10). funding, basis and long/short ratios are contrarian only at extremes, and only after oi stops rising.
7. **intermarket, for gold** (ch17).
   - the dollar moves against gold; real yields and bond futures matter; gold usually leads other commodities.
   - us data (12:30/13:30 utc) and the london/ny opens set the session's direction. check the clock before the chart.
   - btc follows nasdaq futures during us hours.
8. **keep it simple** (ch15; rule 20, p448). 540 indicators are about 10 independent ideas measured 50 ways. count families, not indicators, and trust the out-of-sample table from `edge` over any single reading.

what murphy can't give you here:
- he concedes randomness lives at short horizons (p213-214). expect classical ta to hit ~50-53% out of sample at 5-15 minutes. treat any pre-window signal above ~55% as luck or leakage until `edge` confirms it out of sample.
- his patterns need time (e.g. double-top peaks well apart on dailies). on 1m/5m bars the shapes form constantly and mostly mean nothing; act on them only when volume and regime agree.
- his stops don't exist here: a binary loses the whole stake, so the stake is the stop. his rule "risk <= 5% per trade" (p435) becomes a cap on the stake.
- in-window, the strike is known and fair p(up) is mostly arithmetic (distance to the strike vs the remaining variance). ta only nudges that number.
- taker fees (up to 1.75 points at p=0.50) plus the spread must be beaten. no edge after costs = no bet, and no bet is the default.
- small bankrolls can't respect 5% when the venue minimum is 5 shares. paper-call (log only) until `score` shows an edge over n >= 100.

## chapter notes

### 1 philosophy (p32-53)
- three premises: price discounts everything; prices trend (a trend in motion persists until it reverses); history repeats because crowd psychology repeats.
- price moves before the known news; the technician acts before the reason is public. analysis (direction) and timing (entry) are different jobs; timing is purely technical (p37-38).
- leverage makes timing everything: right direction, wrong timing still loses (p44-45). shorter horizons need shorter tools (futures used 4-9-18 day mas instead of 50/200).
- same principles at every time scale, intraday included (p40). markets rotate between trending and dormant phases: put attention where the trend is (p38-39).
- self-fulfilling prophecy is weak and self-correcting; crowded trend-following systems can distort short-term action (p47-49).
- random walk: murphy rejects pure randomness but concedes noise exists in all markets (p50-52). quant read: at 5 minutes noise dominates; his evidence is daily-and-up trends.

### 2 dow theory (p54-64)
- six tenets: averages discount everything; three trends (primary >1y, secondary 3wk-3mo, minor <3wk: tide, waves, ripples); primary trends have three phases (accumulation, public participation, distribution); averages must confirm each other; volume must confirm the trend; a trend stands until a definite reversal signal.
- secondary corrections retrace 1/3 to 2/3 of the prior move, most often about 1/2 (p57).
- uptrend = higher peaks and higher troughs. failure swing: lower high, then break of the prior low = sell. nonfailure swing: higher high, then break of the low; strict dow theorists wait for a lower high too (p60-62).
- signals on closes only; intraday penetrations don't count (p61). "lines" = sideways ranges (rectangles).
- costs: misses 20-25% of the move; trend followers buy the middle. divergence between the two averages = assume the old trend still holds (p58).
- for short-term traders the minor trend matters for timing: in an intermediate uptrend buy minor dips; in a downtrend sell minor bounces (p63).

### 3 chart construction (p65-77)
- bar, line (close-only; many see the close as the key price), point and figure, candlestick (open vs close relationship is the key). log scale for long-range trends, equal % = equal distance (p69-70).
- volume under each bar; futures open interest = contracts outstanding (one side). intraday bars down to 5 minutes; weekly/monthly for perspective (p75).

### 4 basic concepts of trend (p78-127)
- trend = direction of successive peaks and troughs; three directions. markets move sideways at least 1/3 of the time; trend tools fail there; the wise third choice is to stand aside (p80-81).
- three degrees, each part of the next larger. use the intermediate trend for direction and the near-term trend for timing: buy short-term setbacks in an intermediate uptrend (p82-83).
- support = prior reaction lows; resistance = prior peaks. failure to exceed the previous peak in an uptrend (or holding the previous low in a downtrend) is the first warning of a trend change (p84-86).
- role reversal: a level broken by a significant margin flips (support -> resistance). its strength grows with time spent there, volume traded there, and recency (p86-90).
- "significant" penetration: ~3% for major levels, ~1% for short-term; it must move far enough that trapped traders admit the mistake (p90-93).
- round numbers act as support/resistance (10, 25, 50, 100, multiples of 1000). buy limits just above them, sell limits just below; stops beyond them, not at them (p93-94). btc: thousands, then 500s, then 100s intraday.
- trendline: two rising lows draw it, a third touch validates it. dips to the line are buy zones; a break is one of the best early warnings of trend change. significance = length + number of touches. draw through full ranges, not closes (p94-99).
- valid break = close beyond the line, plus a filter: price (1-3%) or time (two closes beyond, "two-day rule"). filters trade whipsaw against lateness (p100-101).
- broken trendlines flip roles. measuring rule: after the break price tends to travel past the line as far as it had moved on the other side (p101-103).
- fan principle: the third broken trendline signals the reversal (p103-105).
- slope ~45 degrees is sustainable; a too-steep line's break is often just a shift to a slower slope; a too-flat line means a weak trend. an accelerating trend is better tracked by a moving average than ever-steeper lines (p105-108).
- channel: a parallel line through the first peak; confirmed when a rally backs off it and price returns to the base line. base line = entries, channel line = profit-taking (fading the trend at the channel line is dangerous). a break of the channel line in the trend direction = acceleration. failure to reach one side = weakening trend, the other side is likely to break. a channel breakout tends to travel the channel's width. the base trendline matters more than the channel line (p110-114).
- retracements: ~50% is the most common; minimum ~1/3, maximum ~2/3; fibonacci 38/62. murphy's zones: shallow 33-38%, deep 62-66%. past ~66% the odds favour a full 100% retracement (reversal), not a correction. gann eighths 3/8, 4/8, 5/8 (p114-116).
- speedlines (gould): split the trend's height into thirds. corrections tend to hold the 2/3 line, then the 1/3 line, and past that the whole trend retraces. broken speedlines flip roles. gann and fibonacci fans work the same way, but you can't know in advance which line will hold. internal trendlines are subjective (p116-119).
- reversal day: a new extreme, then a close beyond the prior close in the other direction. a wider range and heavier volume make it stronger; an outside bar adds weight. selling climax = bottom reversal on huge volume, usually marks a significant low. weekly and monthly reversals matter more (p119-122). on 1m/5m bars: a bar that runs stops to a new extreme and closes back through the prior close on a volume spike.
- gaps: breakaway (completes a pattern, heavy volume, often unfilled), runaway/measuring (mid-move; double the distance travelled for a target), exhaustion (end of a move; a close back through it is the giveaway). island reversal = exhaustion gap, then a breakaway gap the other way. a close below an up-gap in an uptrend = weakness. "gaps always fill" is a myth (p123-126). btc spot trades 24/7, so true gaps are rare; on 1s/1m bars a jump through a thin book plays the same role.

### 5 major reversal patterns (p128-157)
- rules for all reversals: there must be a prior trend to reverse. the first sign is usually a break of an important trendline, which signals a change (often to sideways), not yet a reversal. a bigger pattern (height = volatility, width = time) means a bigger move. tops are shorter and more violent; bottoms are wider in time and narrower in range. volume matters most on upside breaks; markets can fall of their own weight (p130-132).
- head and shoulders top: left shoulder on heavy volume; head higher on lighter volume; the decline cuts below the left-shoulder peak; the right shoulder on clearly lighter volume fails to reach the head (often retraces 1/2-2/3 of the head's decline). neckline under the two troughs. complete only on a decisive close through the neckline (1-3% or two closes). a return move to the neckline is common (less so when the break comes on very heavy volume). target = head-to-neckline height projected from the break (or double the first decline). targets are minimums; the maximum is a full retracement of the prior move; snap targets to nearby support, retracements and gaps (p132-139).
- inverse h&s: mirror image, but volume is essential: a heavier rally off the head and a burst of volume through the neckline. return moves are more common at bottoms. a down-sloping top neckline = weaker market, later signal (p139-141).
- symmetry: a double left shoulder suggests a double right. aggressive entries come inside the right shoulder: a 1/2-2/3 pullback of the rally off the head, a match of the left shoulder's level, or a break of the short down-trendline. add on the neckline break or the return move (p142-143).
- failed h&s: a decisive close back across the neckline means the signal was bad and the old trend resumes. patterns fail; the edge of charts is that they tell you fast when you're wrong, so cut losers fast (p143-144).
- triple top/bottom: three peaks at the same level, lighter volume on each; complete when both intervening lows break (aggressive: the nearest one). target = height (p144-146).
- double top (m) / bottom (w): second peak on lighter volume; complete only on a close below the middle trough, on heavier volume. a second peak slightly above the first can be a bull trap; filter with closes, 1-3%, two closes, breakout volume. "double top" is overused: backing off a prior peak is normal and the odds favour the trend, so wait for the middle trough to break. valid ones need real time between peaks (p146-154).
- saucers are slow; v/spike reversals come with almost no warning, often only an extreme reversal bar on huge volume after overextension (p154-156).

### 6 continuation patterns (p158-187)
- pauses in the prevailing trend, shorter than reversals. triangles are usually continuations but sometimes reversals; the broadening (inverted) triangle often marks a top (p158-159).
- triangles: symmetrical (coil), ascending (flat top, rising lows: bullish), descending (flat bottom, falling highs: bearish). they need at least 4 reversal points, often 6 (five waves). the breakout should come between 2/3 and 3/4 of the way from base to apex; past 3/4 the pattern loses force and drifts to the apex. the signal is a close through a line; a return move to the broken line is common; the apex becomes support/resistance (p159-162).
- volume contracts inside every consolidation and expands on the break; upside breaks need it. inside the pattern, the swings in the trend direction should carry slightly heavier volume: that's the tell for which way it resolves (p163-164).
- symmetrical triangle target: base height projected from the breakout (murphy's pick), or a parallel line from the top of the base (p164). ascending triangle is bullish wherever it appears (even as a bottom); descending is bearish (even as a top); symmetrical is neutral, so assume the prior trend continues. target = height at the widest point (p165-168).
- broadening (megaphone): diverging lines, volume swelling with the swings, an emotional market out of control; usually at major tops, bearish (p169-170).
- flags and pennants: they follow a sharp, almost vertical move (the pole) on heavy volume, then pause on very light volume and break on a volume burst. a flag slopes against the trend; a pennant is a small flat triangle. they "fly at half-mast": the move after the break tends to repeat the pole. faster in downtrends. among the most reliable continuation patterns (p170-174).
- wedge: converging lines slanted against the trend. falling wedge = bullish, rising wedge = bearish, wherever it appears (a rising wedge at the end of an uptrend is a top) (p175-176).
- rectangle (range, congestion, dow's "line"): usually a continuation. watch which swings carry volume: heavier rallies = continuation up; heavier selloffs = reversal warning. you can trade the range (buy the floor, sell the ceiling, small defined risk) until it breaks, then exit and flip. oscillators shine in ranges. target = range height from the break; the broken edge flips to support/resistance (p176-180).
- measured move: after a 1/3-1/2 correction the second leg tends to equal the first (p180-182). continuation h&s: an upside-down h&s inside the trend (p182-184).
- confirmation = most signals agree. divergence = they don't, and it is one of the best early warnings of reversal (p184-185).

### 7 volume and open interest (p186-209)
- price is primary; volume and open interest confirm. volume matters more than oi (p187). oi rises when both sides open, falls when both close, unchanged when one opens and one closes (p188-189).
- rising volume and oi = the trend probably continues; falling = it may be ending (p190).
- volume = urgency. it should expand in the trend's direction. warning: a new high on falling volume, or volume picking up on dips. pattern breakouts need heavier volume (p191-193). volume precedes price: lost pressure shows in volume before price turns (p193-194).
- obv: cumulative volume signed by the close; its trend matters, not its level; divergence from price warns of reversal. better variants weight by the size of the move; "money flow" = volume on every up-tick vs down-tick, today's cvd / taker-buy ratio (p194-198).
- oi rules: rising oi + uptrend = bullish (new buying). falling oi + uptrend = bearish (short-covering rally, runs out of fuel). rising oi + downtrend = bearish (aggressive new shorts). falling oi + downtrend = bullish (longs liquidating, near done) (p198-200).
- oi flattening late in a long trend = early warning. very high oi at a top is dangerous on a sudden drop: every recent long is underwater and forced selling feeds on itself. oi built up during a range makes the breakout violent (the trapped side scrambles). rising oi at pattern completion confirms. oi can dip at the very start of a trend as losers exit, so don't over-read very short-term oi (p201-203). crypto: binance perp oi, liquidation cascades are exactly this mechanism.
- blowoff top: a sharp rally on a volume jump, often with oi falling in the final run. selling climax: a sharp drop on heavy volume and a quick rebound (p204).
- sentiment: cot (commercials usually right, speculators wrong at extremes); put/call ratio is contrarian (very high = oversold, very low = overbought). sentiment works best combined with trend, support and resistance (p204-208). crypto: funding rate, long/short ratios, and basis are the sentiment gauges.

### 8 long-term charts (p210-223)
- daily charts hide the long trend. analyse top-down: the long-term chart first, then the shorter one. long-range charts obey the same tools (trend, support/resistance, trendlines, retracements, patterns) (p210-212). futures need continuation charts (nearest contract, perpetual weighted series) (p212-213).
- murphy concedes that "whatever randomness does exist in price action is probably a phenomenon of the very short term" (p213-214). this is the key caveat for 5-minute calls.
- weekly/monthly reversal bars near major support or resistance mark turning points (p214). order of study: long range first, then shorter, down to intraday. starting short-term forces constant revision (p214-215). long-term charts give direction and objectives, not timing (p217). log-scale trendlines break sooner (p223).

### 9 moving averages (p224-257)
- the ma is a smoothing, trend-following device with lag. it follows, it never anticipates. shorter = earlier signals and more whipsaws; longer = fewer whipsaws but gives back more at the turn. longer works better while the trend holds, shorter works better as it reverses (p226-232).
- inputs: close mostly; also midpoint, hlc/3, or separate high/low averages as a volatility band (p227). sma, wma, ema (alpha 0.10 ~ 20-period, 0.05 ~ 40-period). there's no real evidence the ema beats the sma (p228-229, p254).
- one ma: a close across it = signal; stronger when the ma itself turns the same way (p230). double crossover: 5/20, 10/50 (p232). triple 4-9-18: the 4 crossing both = alert; the 9 crossing the 18 = confirmation; intermingling during corrections (p233-236).
- envelopes: 3% around a 21-period ma flags short-term overextension (p236).
- bollinger bands: 20-period ma +- 2 sd. a touch of the upper band = overbought, lower = oversold. as targets: a bounce off the lower band that crosses the ma targets the upper band. in a strong uptrend price rides between the upper band and the ma, and a close below the ma warns of reversal. band width = volatility: very wide = the trend may be ending; very narrow (squeeze) = a new trend is about to start. bands work best combined with oscillators (p240-242).
- ma lengths fit cycles and their harmonics (x2): 5, 10, 20, 40; fibonacci lengths 13, 21, 34, 55 (p243-244).
- mas work only in trends, and markets are sideways 1/3 to 1/2 of the time. adx says which regime you're in, and so whether to use mas or oscillators (p245). mas can smooth volume, obv, or any indicator (p248).
- channel breakout (donchian 4-week rule): buy above the prior 4 weeks' high, sell below the 4 weeks' low; exit on a 1-2 week counter-break. in tests, channel breakouts and dual-ma systems came out on top (lukac). harmonics 1, 2, 4, 8 (p248-252). intraday: a 20-bar high/low break.
- optimization: choose parameters on one slice of data, test on another (out of sample); it is no holy grail (p253-254).
- kaufman adaptive ma: the efficiency ratio (net direction / total path) speeds the average up in trends and slows it in chop. er is itself a clean regime gauge (p255).

### 10 oscillators and contrary opinion (p258-299)
- oscillators are secondary, always subordinate to the trend. they shine in ranges; in trends they flag short-term extremes and loss of momentum. near the start of big moves they mislead (they read overbought early); near the end they are very valuable (p258-259).
- three uses: (1) extreme readings = overbought/oversold, the move is vulnerable; (2) divergence while at an extreme = important warning; (3) zero/midline crossings, taken only in the trend's direction (p260).
- momentum = close - close n bars ago: velocity. it leads price, flattening while the trend is still going; trendlines on momentum break before those on price. zero-line crosses: buy only in an uptrend, sell only in a downtrend. set extreme bands by eye from its own history (p261-266). roc = 100 * close / close n (p267).
- ma-difference histogram (short ma minus long ma): spots divergences and overextension, and its zero cross = the crossover. in an uptrend, the short ma dipping back to the long ma and bouncing is the ideal buy area, like a trendline test; a cross through means reversal (p267-269).
- cci (lambert): price vs its 20-period ma, scaled by mean deviation, with +-100 bands. originally a breakout tool (buy above +100, sell below -100); most use it as overbought/oversold (p270-272).
- rsi (wilder): smoothed, bounded 0-100, default 14. shorter (5/7/9) = wider swings for short-term trading; longer (21/28) = smoother. 70/30 extremes, but they shift with regime: 80 is overbought in bull markets, 20 oversold in bear markets. failure swing: a top above 70 that fails to beat the prior rsi peak, then breaks the prior rsi trough (mirror at 30). divergence at the extremes is wilder's "single most indicative characteristic", and murphy's best use. trendlines and mas work on the rsi line itself. strong trends hit extremes early and stay there: the first entry into the zone is only a warning; the second entry that fails to confirm a new price extreme is the divergence. 50 acts as support/resistance; a cross back above 30 (or below 70) is the trigger (p272-279).
- stochastics (lane): where the close sits in the n-bar range. %k, %d = 3-sma of %k, slow = another 3-sma. extremes 80/20. setup = %d diverging from price inside an extreme zone (two falling %d peaks above 80 while price rises); trigger = %k crossing %d. higher timeframe gives direction, lower gives timing. the best signals come when rsi and stochastics are both at extremes (p279-282). williams %r = upside-down stochastics, read the same way (p282-283).
- oscillator length ~ half the dominant cycle (14 ~ half of a 28-day cycle) (p283).
- the trend rules: divergence is the oscillator's greatest value, but never use it as an excuse to trade against the major trend. buy oversold in uptrends, sell overbought in downtrends, take zero-line crosses only with the trend (p284).
- in ranges oscillators mirror price. at a real breakout they are already extreme, so ignore them early in a new trend (they go extreme fast and stay). weight them more as the trend matures (fifth-wave divergences) (p284-285).
- macd (appel): ema12 - ema26, signal ema9. crossovers = signals; far from zero = overbought/oversold; the best buys come well below zero, the best sells well above; zero crosses; divergences when far from zero; trendlines work on it (p285-287). histogram: turns toward zero precede the crossover. best used for early exits; dangerous for counter-trend entries (p288-289).
- multi-timeframe filter: take a lower-timeframe signal only when the higher timeframe agrees (weekly direction, daily timing; here 15m/1h direction, 1m/5m timing) (p289).
- contrary opinion: when the vast majority agree they're usually wrong, because nobody is left to buy (or sell), and the crowd is weak hands against a well-financed minority. consensus >75% = overbought, <25% = oversold; act at 90/20 extremes, and only after the sentiment trend turns. contrarian bets need oi flattening or falling (not still rising), with speculators, not hedgers, holding the oi. tell: a market at an overbought extreme that won't rally on bullish news is about to turn (mirror at bottoms). trade with the sentiment trend until it hits an extreme; confirm the turn with broken support/resistance, trendlines, mas, oscillator divergence (p289-294).
- breadth-style sentiment: % above a moving average >70% = overbought, <30% = oversold; the signal is the cross back inside (p294-296).

### 11-12 point and figure (p298-335)
- pure price, no time. volume is implicit (more boxes = more activity), so p&f locates the levels where trading concentrated, i.e. support/resistance (p299-300).
- precise signals: an x column rising one box above the prior x column = buy; an o column one box below the prior o = sell (p300-301). box size and reversal size set the sensitivity: 1-box for very short term, 3-box intermediate, 5-box long term (p301-306).
- horizontal count: the width of a congestion area projects the move. 1-box: count the columns across the most-filled row = target in boxes. 3-box: columns x box x 3. vertical count: the first column of the new trend x 3 (p307-308, p319).
- 3-box signals: simple buy, buy with rising bottoms, triple-top breakout, ascending/spread triple tops, triangle breakout. fast markets (futures) rely on the simple signals (p313-315). trendlines run at 45 degrees from the lowest o column or the highest x column (p315).
- tactics: use the trendline as a filter; trail the stop under the last o column in an uptrend; enter on the breakout, on the 3-box pullback after it, or on a second breakout (p319-320).
- after a "pole" (10+ boxes with no 3-box correction), put the stop where a 3-box reversal would print; re-enter on the next 3-box reversal in the trend's direction (p322). modern variants: percentage (log) box sizes set from volatility, and 10/20-column moving averages on p&f (p328-332).

### 12 japanese candlesticks (p333-356, by greg morris)
- the body (open to close) is the point; white = close above open. long vs short bodies; spinning tops = indecision. doji (open ~ close): long-legged = indecision, gravestone (long upper shadow) = bearish, dragonfly (long lower shadow) = bullish (p334-338).
- a reversal pattern needs a trend to reverse: a bullish reversal can't exist in an uptrend. set the short-term trend first (a ~10-period ma works) (p338-339).
- dark cloud cover (bearish): a long white candle, then an open above its high and a close below the midpoint of its body. piercing line = bullish mirror (p339-340).
- evening/morning star: a long body, then a small-bodied star gapping away, then a candle closing beyond the first body's midpoint. "work exceptionally well" (p340-341).
- rising/falling three methods (continuation): a long candle, three small counter-trend candles inside its range, then a long candle to a new extreme (p341-342).
- morris filtering, directly usable: only act on reversal candles while an oscillator (stochastic %d, rsi, cci, %r) sits in its pre-signal zone (>80 or <20); ignore patterns at mid-range readings (p343-344). filtered candles usually signal before other price-based indicators (p345). the full library is ~40 reversal and ~16 continuation patterns (p346).

### 13 elliott wave (p358-382)
- three aspects, in order of importance: pattern, ratio, time (p359). five waves with the trend (1, 3, 5 impulse; 2, 4 corrective), then three against (a-b-c). degrees run from multi-century down to hours, and every wave subdivides (p359-362).
- moves in the larger trend's direction come in fives; corrections are never fives (triangles aside). a five-wave decline in a bull market is probably only wave a, so more downside is coming; a five-wave rally in a bear market warns of a bigger turn (p362).
- zig-zag 5-3-5 (c runs well past a's end). flat 3-3-5 (b returns to a's top, c ends near a's low; a sign of strength). irregular flats exist (p363-368).
- triangles are usually wave 4 (or b) and precede the final wave. the thrust out of them is about the triangle's height; the apex often times the end of wave 5; the last leg inside can false-break (p368-370).
- alternation: if wave 2 was simple, expect wave 4 complex, and vice versa (p370-371). channel: a line along the lows of 2 and 4, a parallel above; wave 5 should approach the upper line (p371-373). a new bear market usually holds the prior fourth wave of one lesser degree (p373).
- fibonacci: 0.618, 1.618, 0.382, 2.618; 1/2 and 2/3 are also fibonacci ratios (p373-377). one impulse wave extends and the other two tend to equal each other. wave 3 >= 1.618 x wave 1; c = a in zig-zags; c ~ 1.618 a in flats; triangle legs shrink by ~0.618 each. retracements: ~38% minimum in strong trends, ~62% maximum in weaker ones (p374-375).
- fibonacci time counts (13, 21, 34, 55, 89 bars from turns) are easy to find after the fact and hard to choose beforehand (p377-379). wave theory works best where mass participation is large (gold then; btc now) (p379-380). never force a count; use it with the other tools (p381).

### 14 time cycles (p382-417)
- time is the other axis of every chart: pattern duration, trendline age, ma length and oscillator length are all time choices. cycle analysts treat time as the dominant factor and use "time windows" to filter price signals around expected cycle tops and bottoms (p382-383).
- measure cycles trough to trough (troughs are more reliable than crests). a cycle has amplitude, period, phase (p387-389).
- principles: summation (price = the sum of active cycles; patterns such as double tops fall out of the sum); harmonicity (neighbouring cycles relate by ~x2); synchronicity (cycles of different lengths tend to bottom together, and similar cycles in different markets turn together); proportionality (longer period, bigger amplitude); variation (all of these are tendencies); nominality (a common harmonic ladder ... 40, 20, 10, 5 bars) (p390-394).
- a channel is a cycle riding a trend line. a v top/bottom happens when a cycle turns at the same moment as its longer and shorter neighbours (p394-397).
- use only dominant cycles (ones that are consistent and identifiable). work long -> intermediate -> very short (hours to days) for timing (p397-398). ladder: long term (2y+), seasonal (1y), primary (9-26 weeks), trading (4 weeks), alpha/beta (~2 weeks) (p398).
- a cycle's trend is set by its next longer cycle. when the longer trend is up, buy the troughs of the shorter cycle; when it is down, sell its crests (p400). the 28-calendar-day (20-bar) trading cycle explains the 5/10/20/40 lengths and the 4-week rule (p401).
- translation, the most useful cycle idea: if the crest comes after the cycle's midpoint (right translation) the larger trend is up; if it comes before the midpoint (left translation) it is down. in a bull trend price spends more time rising than falling (p401-403).
- cycle lengths drift. ehlers' mesa measures them adaptively and also separates "cycle mode" (use oscillators) from "trend mode" (use mas); ta-lib's ht_* functions (ht_dcperiod, ht_trendmode, ht_sine) are this family (p413-414).
- seasonality and calendar effects exist (stocks: nov-jan strong, september weak; presidential cycle) (p408-412). crypto intraday analogs: hour of day, the us cash open (13:30 utc), funding times (00/08/16 utc), weekends.
- set oscillator length to about half the dominant cycle; ma pairs at 1/2 and 1/4 of the cycle (p413).

### 15 computers and trading systems (p416-431)
- a computer makes a good technician better and a poor one no better. too many studies (80 back then) overwhelm: use the basics first (price, volume, trendlines, retracements, mas, one or two oscillators); cycles and fibonacci are secondary inputs (p416-420). **this is murphy's own warning against weighing hundreds of indicators equally.**
- parabolic sar: a stop-and-reverse trailing stop that accelerates with the trend; great in trends, whipsaws in ranges (p420-422). wilder: strong trends exist only ~30% of the time, so trend systems fail ~70% of the time (p423).
- adx: rising = trending, favour mas/trend systems; falling = ranging, favour oscillators. adx turning down from above 40 = the trend is weakening (range ahead); adx rising up through 20 = a new trend is starting. +di/-di crosses are signals; use the di lines as a filter, ignoring sensitive signals (sar) that go against them (p423-425).
- a system's real weakness: it can't tell when the market isn't trending and switch itself off; nor does it anticipate reversals at support/resistance, divergences or fifth waves. use system signals as a discipline filter (no shorts while the trend signal is up) and as alerts (p426-428).

### 16 money management and trading tactics (p432-451)
- three parts of any trade: forecasting (what), timing (when), money management (how much). a wrong forecast sinks everything else (p432-433). money management is survival: any good trader wins in the long run, and money management gets you to the long run (p434).
- guidelines: commit at most 50% of capital; at most 10-15% in any one market; **risk at most 5% of equity on any one trade**; at most 20-25% in one correlated group (p434-435). correlated positions are not diversification (p435-436).
- stops are an art: wider in volatile markets; too tight gets stopped by noise (p436).
- the best futures traders win only ~40% of trades; they survive on reward/risk (~3:1 minimum) and by letting profits run and cutting losses short (p436-437). split positions into trend units (loose stops) and trading units (take profits at the first target) (p437).
- after streaks: the worst time to size up is right after a winning streak (like buying an overbought market); size up after equity dips instead (p438).
- tactics: at a breakout you can anticipate (better price, more failures), take the break (better odds, worse price), or wait for the pullback (a compromise that strong markets often deny). splitting units handles the dilemma (p439-440).
- a break of a tight trendline is one of the best early action signals; buying against a rising trendline (or selling against a falling one) is good timing (p440).
- support and resistance are the most effective entry, exit and stop tools: stop under the nearest support, or just under the broken resistance (p440). 40-60% retracements are entry zones, intraday too (p441). gaps work as support (p441). best entry = confluence (retracement zone + support + gap + trendline); exit fast if that support breaks (p441).
- sizing: the max risk (5%) and the stop distance set the size; the stop must sit beyond a valid support/resistance level, not at an arbitrary dollar amount (p442).
- orders: market (sure fill, may chase), limit (better price, may miss), stop, stop-limit, market-if-touched (p442-444). polymarket: taking pays the fee; resting limit orders pay none and earn a rebate, but fills are adversely selected.
- intraday charts fine-tune timing after the longer charts decide direction; stochastic signals on 5-minute bars as an example (p444-446). pivot logic: prior high/low/close and today's open/high/low/close; ignore the first 30 minutes; later signals are stronger (p446-447).
- murphy's 20 rules (p447-448): trade with the intermediate trend; buy dips in uptrends and sell bounces in downtrends; let profits run and cut losses; use stops; have a plan and work it; use money management; diversify without overdoing it; at least 3:1 reward/risk; pyramid only into winners, each layer smaller, stop to breakeven, never add to losers; never meet a margin call; close losers before winners; decide away from the market (except very short term); work long-term to short-term; use intraday charts to fine-tune; **master interday trading before trying intraday**; ignore the media; be comfortable in the minority; keep learning; **keep it simple**.

### 17 intermarket analysis (p452-475)
- all markets link: dollar -> commodities -> bonds -> stocks. futures often move first (p453-459).
- program trading: when futures drift from fair value against cash, arbitrage drags cash along (p454-455). crypto analog: perp premium/basis vs spot, and the spot-perp arbitrage that ties them.
- weight a relationship by its current correlation; near-zero correlation deserves little weight; relationships shift (deflation decoupled bonds and stocks) (p470-472).
- relative strength = a ratio of two prices; trendlines and mas on the ratio show rotation. top-down: market, then sector, then issue (p464-470). crypto: eth/btc for risk appetite; coinbase premium for us spot demand; nasdaq futures during us hours.

### 18 stock market indicators (p476-499)
- breadth checks whether the "troops" follow the "generals": the advance-decline line should confirm the averages; ad divergence tends to peak ahead of the averages (p476-483). mcclellan oscillator (19/39 ema of net advances, +-100) and summation index (p483-485). new highs vs new lows; elder calls the nh-nl index "probably the best leading indicator" (p485-488). upside vs downside volume (p488). crypto analog: % of major coins up over the window, and taker buy vs sell volume.
- arms index (trin) = (advancers/decliners) / (adv volume/decl volume). below 1 = volume in rising issues (positive), above 1 = negative. it's contrary: spikes mark bottoms; 10-period average >1.20 = oversold, <0.70 = overbought. tick = upticks minus downticks, minute by minute; rising tick with falling trin = positive (p488-491). crypto: signed trade counts and taker volume.
- equivolume/candlepower: bar width = volume. breakouts should print wide bars; in uptrends up-bars are wide and down-bars narrow (p492-493). the more averages trend together, the better the odds the trend continues (p496-497).

### 19 pulling it all together: the checklist (p498-505)
- ta is a jigsaw: combine many tools, and the skill is knowing which to emphasise in the current situation (trend vs range). the deciding clue is often a minor factor others missed (p498-499).
- murphy's 23 questions (p499-500): overall market direction; sector direction; weekly/monthly charts; major/intermediate/minor trends; support/resistance; trendlines/channels; volume and oi confirming?; 33/50/66% retracements; gaps and their type; reversal patterns; continuation patterns; pattern targets; ma direction; oscillators overbought/oversold; oscillator divergences; contrary-opinion extremes; elliott pattern; obvious 3 or 5 wave counts; fibonacci retracements/projections; cycle tops/bottoms due; right/left translation; computer trend signal; p&f and candlesticks.
- then decide: which way it trends over your horizon; buy or sell; how many units; how much you risk if wrong; profit objective; entry; order type; stop (p500). keys: knowledge, discipline, patience, a written plan (p500).
- technicals lead the known fundamentals, but big moves need real causes; watch how price reacts to news (p500-501). fed studies (ny fed 1995, st louis fed 1997) found technical rules profitable in daily fx (p504-505). quant note: later work found those fx profits faded after the 1990s; edges decay once published.

### appendix a: advanced indicators (p508-518, by tom aspray)
- demand index (sibbet): buying vs selling pressure from price and volume; the zero line and divergences matter; trendlines drawn on an indicator often break before trendlines on price (p508-511, formula p518).
- herrick payoff index: money flow from price, volume and oi; zero crosses and divergences; weekly data gives fewer false signals (p511-513).
- starc bands: 6-period ma +- 2 x atr(15). near the upper band = high-risk buy / low-risk sell; near the lower band the reverse. they work down to 5-10 minute bars and stop you chasing (p514-515).
- keltner channels (raschke): ema20 +- 2 x atr(10). a close above the upper band = an upside volatility breakout (bullish); below the lower = bearish. it's a channel breakout, and the ema20 is support in an uptrend (p515-517). note the opposite readings: starc fades the band, keltner follows the break. regime decides which applies.

### appendix b: market profile (p520-539, by dennis hynes)
- a price histogram on its side: the time (or volume) spent at each price. mode = the fairest price (poc). value area = the ~70% of activity around the poc (~1 sd) (p520-523, p533). it's a decision-support tool, not a system (p523).
- dual auction: price rises to shut off buying, advertising for sellers (and the reverse). each move sets an unfair high and an unfair low, then trade rotates between them to build value (p525-526). markets cycle balance -> imbalance -> balance on every timeframe (p526).
- short-term traders seek a fair price and set the initial balance early in the session; longer-term traders seek an advantageous price and are the ones who move the market directionally (range extension) (p526-527).
- accepted prices (time spent) vs rejected prices (little time = excess at an unfair high or low) (p527). responsive activity fades moves away from value; initiating activity buys above value or sells below it, and is the sign of confidence (p528).
- day types: normal (range set early, rotation); normal variation (range extends up to ~2x the initial balance; the most common); trend day (>2x, closes near the extreme); neutral (extends both ways = uncertainty) (p529-530).
- extremes: two or more single prints at a high or low = strong longer-term rejection; one print = a weak local top or bottom (p531). range extension up = longer-term buying (p533). tpo imbalance: count activity above vs below the poc; the thinner side holds the longer-term imbalance (p533-534).
- value migration: today's value area above yesterday's = uptrend. combine several sessions to see the larger balance; after balance, the next imbalance often starts after a final test of the fairest price (p534-535). btc 5m: build the profile from 1m volume over the last few hours (poc, vah, val). price accepted above value = initiating buying; quick rejection at a value edge = responsive.

### appendix c: building a trading system (p538-549, by fred schutzman)
- aim for a sound concept that worked reasonably and should keep working, not the best backtest. mechanical = objective: 100 people following the rules get the same trades (p538-539).
- five steps: concept -> objective rules -> eyeball it on charts -> formal test -> evaluate (p539).
- a concept should make sense (otherwise it's coincidence), fit your temperament, and have positive expectation. exits are harder and more important than entries. optimize as little as possible, with few parameters (p540-541).
- types: trend following; counter-trend (buy support, sell resistance; buy retracements in bull markets; oscillator extremes, best with divergence, and wait for a price reversal sign); pattern recognition (p541-542).
- robustness tests: neighbouring parameters must also work (5/20 -> 4/21, 6/18); other periods; other markets. fewer than 5% of ideas test profitable, and most of those aren't tradable (p543-545).
- evaluate: profit factor (>= 2 long-term, a bit lower short-term), average trade must exceed costs, max drawdown. money management matters as much as the system (p545-546). quant note: he skips out-of-sample and adds costs at the end; at 5 minutes, costs are the whole game, so include them and hold data out.

### appendix d, glossary (p550-566)
- continuous futures (nearest, next, gann, constant-forward weighted). btc perps never roll, so none of this is needed. the glossary repeats the chapter definitions (trend: major >1y, intermediate 1-6 months, minor <1 month).
