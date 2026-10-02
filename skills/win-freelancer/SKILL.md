---
name: win-freelancer
description: Use when entering, picking, reviewing, or closing any freelancer.com contest or project bid. Wins every one entered by controlling every input to the holder's decision, and skips any where that is not possible.
---

# Win freelancer contests and project bids

Research first: contests `~/search/win-freelancer-contests-first-principles.md`. Projects `~/search/win-freelancer-projects-first-principles.md`.

Read contest and project details through the Freelancer API. Never scrape the website for them. If the API fails, fix the request or report the error; do not fall back to the website.

Post everything only with agent-browser (`ab-1440fl`, logged in as ed5454): entries, bids, questions, messages, profile edits. Never post through the API.

`FREELANCER_TOKEN` is set in the environment. Check that it is non-empty before API requests; never print its value.

Work in `~/work/fl-<id>`.

Ed's field (bid and enter only these):

- video: speaker cuts, product films, launch/promo films, intros, motion
- graphic design: posters, thumbnails, logos, cards, flyers
- illustration
- web
- blender

Skip typing, OCR, data entry, open thesis-with-no-files, and anything else.

Live main headline (50-char cap): `video | graphic design | illustration | launch`. Specialised profile `31430740` "video and design" has the same copy. Bid with that profile.

## Pick (contests)

Enter only when all of these hold:

- Guaranteed prize (the money exists and must be awarded).
- Holder is live: past awards, replies within a day, brief written like a real business.
- Brief is specific. A vague brief means an unpredictable judge. Skip.
- Field is beatable: low entry count now, or a niche you already own work for.
- Prize is worth the field. Skip the rest. Skipping is how you win the ones you enter.

## Pick (projects)

Enter only when all of these hold:

- Live employer: past awards, replies, spend. Owner hidden + no files + no hire history = skip.
- Brief is specific. Vague brief = hire-nobody. Skip.
- Field is one of Ed's fields above, and he already has a public outcome he can name in the first lines.
- Budget: bid inside their posted min–max, at a price Ed would actually accept. Never under min. Too low = lemon. Too high = off their world. Do not bid then reject.
- Field is beatable: close match, or low enough bid count that a human will look.
- Skip the rest.

## Decode

- Turn the brief into a hard checklist. Every line is a pass/fail gate. Miss one gate and you are out at elimination.
- Elimination is fast and emotional. Survive the one-second look first, win the small final pool second.

## Enter (contests)

- Post every entry with agent-browser (see Post an entry). Title ≤50 chars, desc ≤1000 chars. Image files only: PNG, JPG or GIF.
- Simple design, category-typical, exactly one twist. Fits the client's existing look if they have one.
- Enter early and enter all allowed slots. One strong concept with variation, not three unrelated shots.
- Highlight the lead entry. Withdraw and resubmit to stay near the top of the list.
- No AI where the brief bans it. Declare AI where the platform requires it. Original work only.

## Post an entry (agent-browser)

1. `ab-1440fl set viewport 1440 1000`. At the default 1280×633 the chat widget covers Submit.
2. `ab-1440fl open https://www.freelancer.com/<seo_url_new>`, click button "Submit entry". URL ends `/submit-entry`.
3. `upload @<"Choose Files" ref> <absolute path>`. Done when image "Remove File" shows; the input still says "No file chosen".
4. AI declaration: click the true label. "AI assisted" = "I led the creative process, using AI tools". "AI generated" = "AI produced this entry from my prompts, with little or no manual work". Wrong labels may be disqualified. Brief bans AI: Ed picks.
5. Licensed content: keep "This entry is entirely my own" unless stock items are used.
6. `fill` title and description, then in each field `press End`, `press Space`, `press Backspace`. Without a real key press Angular drops the text (counter stays "1000 characters left").
7. Sealed is free while the form shows seal upgrades left: click the "Sealed Free" row, not its checkbox. Highlight costs $0.50: ask Ed. Total must read $0.00.
8. Click the bottom "Submit entry" (the top one only opens the form). Lands on `/entries`.
9. Check: `GET /api/contests/0.1/entries/?contests[]=<id>&limit=200&file_details=true`, `owner_id` `93275816` → number, status, sealed, title, file. The API shows line breaks as literal `\n`; the page shows real line breaks.

## Enter (projects)

- First sentence: unique fact from the post + a diagnosis. Then one similar outcome with a number. Then one diagnostic question the brief did not already answer. No "I am a skilled X."
- Title ≤50 chars, desc ≤1000 chars. Amount in the project's currency. Period in days.
- Post the bid with agent-browser, from the "video and design" profile.
- Bid early. Sponsor only if you would not land on page one and you already convert in that exact category. Do not highlight page two.

## Engage

- Post one sharp public question on the clarification board (contests). On projects, reply in minutes.
- Answer every holder message within minutes. Send a revision before it is asked for. Familiarity and speed tilt the final gut call.

## Close

- Sign the IP transfer the hour you win a contest. Upload every file format in one pass.
- On projects: accept, talk, first milestone in escrow before real hours. Do not reject after bidding unless it is a scam.
- Fee is 10% of the prize or $5, whichever is greater. Handover done = money real.
- Holder stalls: handover dispute exists. Use it.

## Check

Can you name the controllable input for every risk? If any risk has no input you control, do not enter.
