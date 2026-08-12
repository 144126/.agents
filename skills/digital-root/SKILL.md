---
name: digital-root
description: Compute the numeric sum and digital root of a string by mapping each alphabetic character to its position in the alphabet (a=1, b=2, ... z=26) and adding any explicit digits. Use when the user types "ndr" or asks for the digit sum, letter-value sum, or digital root of a word or phrase. Trigger on "ndr", "digital root", "letter position sum", "alphabet value sum", or requests to add up letter positions.
---

# Digital Root (ndr)

Given a string, add up the alphabetic position of every letter (a=1 ... z=26,
case-insensitive) plus any explicit numeric digits found in the input, then print
the total sum and the digital root of that sum.

## Output format

Print two integers separated by a space: `<sum> <digital_root>`.

The digital root is the single-digit value obtained by repeatedly summing the
digits of the total until one digit remains. (Mathematically it is
`1 + (sum - 1) % 9`, with digital root 0 only when the total is 0.)

## How to compute

1. For each character in the input:
   - If it's a letter, add its 1-based alphabet position (A/a=1 ... Z/z=26).
   - If it's a digit, add its numeric value as-is.
   - Ignore spaces, punctuation, and other non-alphanumeric characters.
2. Total the contributions.
3. Reduce the total to its digital root.
4. Print `<total> <digital_root>`.

## Example

`ndr i love i 9`
- Letters: i=9, l=12, o=15, v=22, e=5, i=9 → sum = 72
- Digit: 9 → total = 81
- Digital root: 8+1 = 9
- Output: `81 9`

(Note: the total here is 81, not 45 — the worked example in the request had a
slip; trust the rule, not the illustrative arithmetic.)

## Script

Use the bundled script for deterministic results across repeated invocations:

```bash
python <skill_dir>/scripts/ndr.py "i love i 9"
```

It accepts the input string as a single argument and prints `<sum> <digital_root>`.
