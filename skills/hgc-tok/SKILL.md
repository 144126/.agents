---
name: hgc-tok
description: Make a Hogan and Crown Law episode - a carved-text fact video or photo carousel for the firm's TikTok and X accounts. Wraps the still-tok format with this firm's facts, brand, palette, emotional mode, and the legal guardrails that apply because a real attorney's name is on it. Use for any hgc social post, when the user says "hgc video", "new episode", "things we wish you knew", or names a fact from the firm's site or LinkedIn.
---

# hgc-tok

An episode for Hogan and Crown Law. Read `still-tok` first — it owns the format, the two-pass
generation, the carving rules, and the assembly. This skill only holds what is specific to this
firm.

## The firm

- **Hogan and Crown Law**, Dallas. Queenette Hogan Esq., founder and principal attorney.
- Business and immigration law. US federal immigration, so she can represent clients in any state.
- Site: `hoganandcrownlaw.com`. Rebuild in progress at `hoganandcrown.apexlinks.org`.
- Logo: gold `HOGAN & CROWN` wordmark over a pale scales device, at
  `hoganandcrownlaw.com/wp-content/uploads/2020/06/HCLogo@512.png`. Composite the real file as an
  engraving. Never let a model draw the mark.

## Guardrails, because a real attorney is liable for this

- **Never invent a legal claim, number, deadline, or eligibility rule.** Every fact comes from the
  firm's own published answers page, its posts, or a government source.
- **Do not overstate a rule into a falsehood.** "A US citizen child cannot petition until 21" is
  true of *petitions*. That same child is directly relevant to cancellation of removal in
  immigration court. State the narrow claim, never the broad one.
- **Aim at the process, never at a party, an agency, or an administration.** She practises in front
  of these officers. "The system is built this way" is safe. Anything nameable is not.
- **No guarantees, no outcomes, no urgency about money.** Her own posts carry a scam warning; never
  produce anything that pattern-matches to the scam.
- Attorney advertising disclaimer belongs in the post description, not burned into the pictures.

## Emotional mode

**Indignation, on the viewer's behalf.** Not sadness.

Sadness is low-arousal and suppresses sharing. Indignation is high-arousal and carries. It also
puts the viewer on the right side of what happened rather than at fault for not knowing.

The move is to give the sentence an antagonist:

| flat or sad | indignant |
| --- | --- |
| nobody told you | they never told you |
| that is twenty one years of waiting | twenty one years. that was always the design. |
| leaving triggers the ban | you did the right thing. that is what cost you. |

Awe is the untested alternative and is strongest where a fact carries huge disproportion — *one
flight, ten years*. Worth building an episode on when the fact allows it.

Never close on a scold. The last card exonerates and points forward. Blaming the viewer's family,
their community, or their WhatsApp group kills the share, because shame does not travel.

## Fact bank

All published at `hoganandcrown.apexlinks.org/answers` unless noted. Do not add to this list from
memory.

| # | Fact | Status |
| --- | --- | --- |
| 1 | the bar activates on departure, not while you are inside | used, episode one |
| 2 | a US citizen child cannot petition until they are 21 | used, episode two |
| 3 | a notary is not a lawyer; ask anyone for their bar number | open |
| 4 | the government never phones demanding payment, and never takes gift cards | open |
| 5 | the diversity visa lottery is free on the one official site | open |
| 6 | you need not open the door without a warrant signed by a judge | open |
| 7 | leaving with a pending adjustment and no advance parole abandons it | open |
| 8 | you must report a change of address, or notices go to the old one | open |
| 9 | a 214(b) refusal is about ties, not bank balance, and is not permanent | open |
| 10 | a dismissed charge does not automatically bar naturalisation | open |

Her LinkedIn is a second source: `linkedin.com/in/queenettehoganprofile`. Reach it with
`agent-browser --profile "$(chrome-profile-clone Default)"`.

## House constants

- Style reference: `~/i/hgc/marketing/still/ref/style-ref.png`, passed on every generation.
- Specs and pipeline: `~/i/hgc/marketing/still/`. Style block: `../video/style.json`.
- Sound: *Benson Boone, In The Stars, slowed and reverb, TikTok version*. Start at **2.30s**, the
  first piano strike. Cuts at 3.54, 7.07, 10.61, 14.12, 16.02.
- End card: the carved stone slab with the real logo embossed into it. No light sweeps, no effects.
- Silent file for upload, sound-muxed copy for review only.

## Posting

Description carries the search-shaped sentence, the disclaimer, and the call to action she already
uses: `Comment "CALL" to book a consultation`. Hashtags follow her own set from the matching post.

Add the trending sound in the TikTok app at upload, never muxed into the file, or the video loses
the sound page and the reach that comes with it.

## The daily agent

`~/i/hgc/agent` runs this on a schedule and queues each episode for approval. It never posts
unreviewed. See its README for the credential gates.
