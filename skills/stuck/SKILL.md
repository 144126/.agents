---
name: stuck
effort: max
description: Use when something fails and you do not know why - a plan gate goes red, a test breaks for an unclear reason, a build fails after a change that looked correct, or you are about to run `plan <name> <step> --block`. Raises reasoning to max for the diagnosis, then hands the work back. Not for a failure whose cause you already know.
---

# stuck

You are running at `max` effort for this turn only. You bought that with real
money, so spend it on the diagnosis, not on the size of the fix.

Two rules frame everything here. Max effort is the level where this model starts
to widen scope and rewrite code nobody asked about. And a red gate is a fact
about the code, never a fact about the gate.

## Find the cause

1. **Read the real output.** Open the actual failure text: the gate output, the
   stack trace, the compiler error, `.log` if the repo has one. Never work from
   your memory of what it probably said.
2. **State the surprise in one line.** "I expected X, the code does Y." If you
   cannot write that line, you have not read enough yet.
3. **Shrink it.** Find the smallest command that still fails. One test, one
   request, one function call.
4. **Trace every caller.** Grep for every use of the function you are about to
   touch. The cause usually sits where all the callers route through, not in the
   one path the failure named.
5. **One hypothesis at a time.** Write it down, then run the one command that
   proves it wrong. Two changes at once tell you nothing.
6. **Search the net after one failed attempt.** A version trap, a platform cap,
   or a breaking change in a dependency will not yield to more thinking.

## Fix it

Fix the cause, once, where every caller passes through. A guard in the shared
function beats the same guard in five callers.

**Do not widen the job.** No refactor, no rename, no cleanup, no "while I am
here", no second bug you noticed on the way. If you found something else, say so
in one line and leave it.

**Never weaken the proof.** Do not edit a test, loosen an assertion, relax a
gate, or delete a case to get to green. If you are inside a plan, the staged
tests are byte-compared and it will fail anyway. Making the check agree with
broken code is the one outcome worse than staying stuck.

## Hand it back

- Record it: `plan <name> --note "<the cause in one line>"`. A version trap or a
  real API shape saves the next step the same hour you just spent.
- The plan's premise is wrong, not the code — the file moved, the step is really
  two steps, the work is already done another way: run
  `plan <name> <step> --block "what you hit"`. Do not improvise around a plan
  that is out of date.
- Otherwise finish the step and mark it. The fix belonged to this step.

When you are done, stop. The next turn drops back to the session effort level,
which is where the rest of the work belongs.
