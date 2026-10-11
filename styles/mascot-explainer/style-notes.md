# mascot-explainer

An illustrated explainer: a hand drawn mascot acts out a how-to on a plain
white background while one narrator talks nonstop and the captions show one
word at a time. There is no camera footage.

**Learned from one reference** (an Instagram finance reel narrated by a
chihuahua called "Doggy"). With one video I can't tell a deliberate habit from
a one-off choice, so anything marked *single source* should be re-checked when
more references are added.

## Look

| Element | Choice | Evidence |
|---|---|---|
| Background | Flat white `#FFFFFF`, every scene | corner pixel samples in every scene |
| Captions | One word, upper case, yellow `#EDFA00`, black outline 0.31% of height, no shadow | median of caption pixels; row scan through "TOGETHER" |
| Caption font | Luckiest Guy (by eye) | rounded heavy comic capitals; not confirmed |
| Caption position | Centred at 77.8% down the frame, never wider than 56% | bounding box of all 182 caption words |
| Caption timing | Hard cut word to word, no pop; 0.27s per word (median) | caption width constant across each word's first 4 frames |
| Labels | Handwritten marker text, red `#E5481F` for costs, green `#039F19` for money, black for statements | pixel medians at 19s, 24s, 32s, 38s |
| Mascot | Thick black ink outline, flat fills, no shading | contact sheets |

## Motion

The most surprising finding: **almost nothing animates.** Every element
appears on a single frame and leaves the same way. There are no slides,
scales or fades. The video feels busy because something new lands about
every 1.1 seconds (every 3 to 4 spoken words), timed to the frame of its
keyword, usually 0 to 3 frames before that word's caption.

The only real motion:

1. The mascot scales in on the title card over 2.4s, stepped at 10fps.
2. One "operation" per video: two piles of bones slide together for "add both
   paychecks".
3. Boiling idle loops: the bone doodles around text cards and the close up
   mascot's arms flip between two drawings about every 0.2s, so held shots
   never look frozen.

There are no zooms or pans. To change scale, the video cuts to a different
mascot drawing. Props such as the doghouse appear already cut off by the frame
edge.

## Mascot poses and when to use them

| Pose | Beat |
|---|---|
| Standing, side on | default narration, intro |
| Two characters | relationship or partner beats |
| Front close up, arms out | listing examples within a step, with one card swapped above the head per example |
| At a laptop | list / track / plan |
| Hand on chin | the payoff line |
| Costume (top hat and suit) | a joke beat |
| Paw raised | CTA |

## Layout (percent down the frame)

Cards and stickers 14 to 44, labels 27 to 52, text cards 40 to 61, full body
mascot 39 to 71, close up mascot 43 to 100 (off the bottom), props 50 to 74,
captions 75.5 to 80. Below the captions stays empty.

## Script and voice

1. **Hook:** a "How to ...?" question on a handwritten title card, then
   "Explained by Doggy".
2. **Setup:** in the third person: "Doggy and partner just moved in together.
   Two paychecks, one home. And suddenly Doggy has way more bones to pay for."
3. **Steps:** signposted First / Now / Next / Then / Finally. Each has 3 to 4
   concrete examples and a one-line moral ("Give those bones a job before they
   disappear").
4. **One metaphor, never broken:** money = bones, household = the pack, home =
   doghouse.
5. **CTA:** a comment keyword that uses the metaphor word ("comment bones"),
   then a pun sign-off ("without eating all the bones").
6. **Pace:** about 200 wpm, wall to wall, breaths cut out. Loudness −14 LUFS
   with very little variation; probably no music bed.

## What was left out, and why

1. **The budgeting app cards, app icon and "download from link in bio" end
   card.** These are almost certainly the creator's own product. Only the
   *slot* is kept: one realistic data card at the top of the frame, swapped
   per example.
2. **The caption freeze at 20.8 to 24s** (stuck on "YOU'RE" while the voice
   continues). This looks like an editing slip, not a style.
3. **Platform UI:** none was visible; the file was a clean download.

## Still uncertain

1. The exact caption and handwriting typefaces (closest guesses: Luckiest Guy;
   a casual marker hand like Gochi Hand or Patrick Hand).
2. Whether the voice is text to speech or human, and whether sound effects
   play on each element. Both need listening.
3. Two short stretches of voiceover were never captioned, so they are missing
   from the transcript (whisper was not installed during analysis).
