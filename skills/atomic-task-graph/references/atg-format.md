# The `.atg` format

Plain text. Diffable, committable, readable by a human without the CLI. One file
per revision under `graphs/`, plus `tools.atg` for the tool registry.

## Grammar

```
file        := header task_line? (blank | comment | block)*
header      := '# atg/1' (WS key '=' value)*
               keys: rev, parent, refined, kind, created, note
task_line   := 'task:' TEXT
block       := node_block | exports_block | tool_block
node_block  := 'node' ID EOL (INDENT field EOL)+
exports_blk := 'exports' ID EOL (INDENT FIELD '=' ref EOL)+
tool_block  := 'tool' NAME EOL (INDENT tfield EOL)+          # tools.atg only
field       := 'goal:' TEXT
             | 'tool:' NAME
             | 'in:'   binding (',' binding)*
             | 'out:'  NAME (',' NAME)*
             | 'after:' ID (',' ID)*
             | 'run:'  SHELL
             | 'timeout:' INT
             | 'from:' ID
             | 'note:' TEXT
tfield      := 'desc:' TEXT | 'in:' param (',' param)* | 'out:' param (',' param)*
param       := NAME [':' TYPE] ['!']                          # ! = required
binding     := NAME '=' value
value       := STRING | NUMBER | ref | BARE | heredoc
ref         := '$' (ID | 'task' | 'env') '.' FIELD
ID          := 'N' INT ('.' INT)*
heredoc     := '<<<' EOL raw-lines EOL '>>>'
comment     := '#' TEXT                                       # whole-line or trailing
```

Indentation is spaces only — a tab is `E_DSL_TAB`. A field's value continues onto
the next line if that line is indented strictly deeper than the field itself.
Strings are `"…"` with `\"`, `\\`, `\n`. `BARE` is `[A-Za-z0-9_./:@+-]+`. A `#`
starts a comment unless it is inside a string or a heredoc.

## What the pieces mean

**No `tool:` means non-atomic.** The node is a goal awaiting refinement. `atg open`
lists exactly these, and an empty list is the paper's termination condition — the
recursion stops when every node is a single atomic tool-use unit.

**Edges are inferred, never declared.** Every `$Nj.f` in `Nk`'s `in:` creates the
edge `Nj → Nk` labelled `f`. There is no edge syntax, so a graph cannot claim a
dependency it does not actually have, and a reference nothing produces is
automatically a dependency error rather than something a validator must be told to
look for.

`after: Nj` adds a control-only edge — ordering with no data. Use it for
environment-state preconditions ("go to the kitchen" before "open the fridge")
that pure data flow cannot express. Do not fake a data dependency to get ordering.

**Ids are hierarchical.** Refining `N3` yields `N3.1, N3.2, …`; the depth of an id
is its refinement depth. The lowest common ancestor of a set of failed nodes is
therefore the longest common dotted prefix. The root is `N0`, and refining it is
the one special case: it emits `N1 … Nk` rather than `N0.1 … N0.k`, so ordinary
ids stay short. Failed nodes with no common prefix land on `N0` — the correct
answer, with no special case in `blame`.

**`exports` preserves the interface.** An `exports N3` block maps each declared
output of `N3` onto a ref inside `N3`'s subgraph:

```
exports N3
  advice = $N3.2.advice
```

Outside nodes go on writing `$N3.advice` forever; resolution walks the export map,
following chains when a refinement is later refined again. This is what confines a
refinement's textual diff to its own block, so the surrounding graph is
structurally stable as a property of the file rather than a claim about behaviour.

**Local ids inside a fragment.** When you write a fragment for `atg refine N3`,
`node 1` means `N3.1` and `$1.field` means the sibling `N3.1`. Careful: `$2.1.x`
means the *child* `N3.2.1`, not the sibling `N3.2`. `atg fmt fragment.atg --parent N3`
expands everything so you can check before submitting.

**`from: N3.1`** marks a repaired node as the successor of an old one. If the tool
and every resolved input match, the new node inherits the old node's verified
output instead of re-running.

**`run:`** is a shell command executed by `atg exec`. Refs inside it are
substituted with resolved values (`$N1.forecast`), as is `${name}` for a binding
name. Large values become file paths.

## Canonical form

Every write, and `atg fmt`, emit: header, blank, `task:`, blank, node blocks in
(topological rank, id) order with 2-space indent and one space around `=`, `in:`
bindings wrapped at 88 columns with continuation indent 8, then `exports` blocks in
id order. Parse → serialize → parse is a fixed point, fuzz-tested.

## Example — the paper's Figure 3, third revision

```
# atg/1 rev=G003 parent=G002 refined=N3
task: check tomorrow's weather in beijing, give travel advice

node N1
  goal: fetch tomorrow's forecast for beijing
  tool: weather_api
  in:   city = "beijing", date = $task.date
  out:  forecast

node N2
  goal: confirm the city name resolves to exactly one place
  tool: geocode
  in:   q = "beijing"
  out:  place_id

node N3.1
  goal: pull the fields that drive advice out of the forecast
  tool: json_extract
  in:   src = $N1.forecast, place = $N2.place_id
  out:  temp_c, precip_mm, wind_kph

node N3.2
  goal: decide umbrella and clothing from the extracted conditions
  tool: llm_judge
  in:   t = $N3.1.temp_c, p = $N3.1.precip_mm, w = $N3.1.wind_kph
  out:  advice

node N4
  goal: write the final travel advice for the user
  tool: compose
  in:   advice = $N3.advice, forecast = $N1.forecast
  out:  answer

exports N3
  advice = $N3.2.advice
```

`N4` still reads `$N3.advice` even though `N3` no longer exists as a node. That is
the whole mechanism in one line.

## Parse errors

`E_DSL_SYNTAX`, `E_DSL_TAB`, `E_DSL_DUP_NODE`, `E_DSL_DUP_FIELD`, `E_DSL_BAD_ID`,
`E_DSL_BAD_REF`, `E_DSL_UNTERMINATED`, `E_DSL_UNKNOWN_FIELD`. Every one carries
`file:line:col`, the offending text, and a hint.
