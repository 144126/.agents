---
name: forecast
description: Make, log and score probability forecasts the superforecaster way. Starts from a base rate, adjusts for the case, averages several independent estimates, logs the number with a resolve date, then scores resolved forecasts with the Brier score. Use when the user asks "will X happen", "what are the odds", "how likely", wants a prediction, or says /forecast, /resolve or "score my forecasts".
---

# forecast

Mellers et al. 2014 (Psychological Science): training that "encouraged forecasters to use reference classes" and averaging "when multiple estimates were available" improved accuracy. Feedback on scored forecasts is what lets judgment learn (Kahneman and Klein 2009).

Log: `~/forecasts.tsv` (create it with the header if missing). Columns, tab-separated, header on line 1:
`id	made	resolve_by	question	p	outcome	notes`
`p` is a probability 0-1 that the event happens. `outcome` is blank, 1 or 0.

## Make a forecast

1. **Sharpen the question** until a stranger can settle it: exact event, exact date, a source that will report it. "Will Bitcoin crash?" becomes "Will BTC close below $60k on Coinbase on any day before 2027-03-01?"
2. **Base rate (outside view).** Pick 1-3 reference classes: "how often do things like this happen?" Search for real counts. Write each as `k of n`. Pick classes close to the case but with n of 20 or more when possible.
3. **Adjust (inside view).** List at most 3 facts that make this case differ from the class. Move the number only by what each fact is worth, usually under 20 points total. Big moves need big evidence.
4. **Average.** Get 3 or more independent estimates: each reference class, the adjusted number, prediction markets or expert forecasts if they exist. Average them in log-odds (works better than a plain mean near 0 or 1):
   `logit(p) = ln(p/(1-p))`, average the logits, convert back with `1/(1+e^-x)`.
   Never fully trust one source. Never report 0 or 1: clamp to 0.02-0.98.
5. **Log it.** Append a row. id = next integer. One line of notes: the base rate and the main adjustment.
6. **Reply:** line 1 is the probability as a percent. Then base rate, adjustment, sources. 4 lines max.

## Resolve and score

On `/resolve <id> <1|0>`, set the outcome. On "score my forecasts", for all resolved rows:

- **Brier** = mean of `(p - outcome)^2`. 0 is perfect. Always guessing 50% scores 0.25. Lower is better.
- **Calibration:** bucket by p (0-20, 20-40, 40-60, 60-80, 80-100). For each, the mean p against the share that happened. If the 80s happen only 60% of the time, you are overconfident.
- List open rows past `resolve_by` and ask for their outcomes.

Compute with a one-off `awk` or `python3 -c` over the tsv. Write no other files.

Reply: line 1 is Brier and n (`brier 0.18 over 27`). Then the worst-calibrated bucket in one line.
