# DRAFTS, NOT SENT. Emails to labs whose data could unblock NEMATICA (18 Nov 2026, third version, after independent check)

Sent by the project owner personally, from their own address. Nothing here is sent by Claude.

**Before sending:**
- Fill in [affiliation]. A university address helps.
- Check each address. Kato, Yemini, Häusser and Flavell addresses are the correspondence addresses in
  their papers or dataset pages; Leifer, Kimura and Bellec are marked "as published" and need looking up.
- Bracketed optional lines are your call (co-authorship offers, the Creamer note to Leifer).
- Every email links the one-page summary: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md
- Send the top four first. Keep each email to one lab; cc a second author only where noted.

Suggested order of value: 1 Leifer, 2 Kato, 3 Flavell, 4 Häusser, then 5 to 7.

---

## 1. Leifer lab (Princeton)

**To:** Andrew Leifer (address as published in Randi et al. 2023)
**Subject:** Held-out test of a whole-brain worm model on the signal-propagation atlas: are there more stimulated worms?

Dear Dr Leifer,

I am [your role, e.g. a student at X] and have been building a benchmark for whole-brain models of C. elegans,
where every test is scored in units of worm-to-worm variation (pre-registered since early November). Your signal-propagation
atlas is the core of it, and it produced the project's clearest result: on your 113 wild-type worms, a
model fitted to ongoing activity passes 3 to 5 of 6 activity tests, yet its response pattern to
single-neuron stimulation agrees with real worms at 0.004 to 0.014, against 0.087 to 0.121 between real worms. A model
that also learns from stimulation reaches 0.088 to 0.113.

Building on that, a model with four ingredients (slow interacting brain-wide states, individuality,
causal links learned from stimulation, and neuron-level observation) now passes both ongoing activity and stimulation
on your worms, with knife-edge margins on some levels. But it was built on all of them, so I cannot confirm it on unseen animals. On your
unc-31 worms it narrowly fails its pre-set threshold (3 of 5 noise draws, against 4).

**My request:** are there stimulated whole-brain recordings beyond the 113 wild-type and 18 unc-31 worms
in the OSF archive, such as newer wild-type worms or recordings that were set aside? Even 15 to 20 unseen
worms in the same format would allow a clean held-out test, frozen and registered before I open them. I
would keep the data local, credit it in any write-up, and send you the result before posting it.
[Optional: I would be glad to discuss co-authorship if the result is useful to you.]

One exploratory finding you may want: a neuron stimulated again 0.6 to 2 minutes later responds at about half its
previous response (56 pairs, 37 worms, gap-matched controls), about two thirds at 2 to 5 minutes, and not
detectably less after 5 to 10 minutes, and a decline is also seen in unc-31 worms. About 9% of the atlas's identified
stimulations are repeats within 5 minutes. I could not tell whether this is GUR-3/PRDX-2 or the neuron;
do you know?

[Optional, your call: "I also recomputed the held-out measure for the connectome-constrained model
from the published Creamer et al. models and maps and got 0.81 of the train-to-test ceiling rather than 92%. This may well be my error; I would be
glad to send the calculation."]

A one-page summary: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md
(code, pre-registrations and logs are in the same repository; I work with the help of an AI research
assistant). A preprint draft is available on request.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 2. Kato lab (UCSF)

**To:** Saul Kato (saul.kato@ucsf.edu); cc Raymond Dunn
**Subject:** Stimulation times for the whole-brain recordings in DANDI 000565, for a second-lab test of worm brain models

Dear Dr Kato,

I am [your role, e.g. a student at X] and have been building a benchmark (pre-registered since early November) for whole-brain models of
C. elegans, scored in units of worm-to-worm variation. Its clearest result, on the Leifer lab's
signal-propagation atlas, is that a model fitted to ongoing activity passes 3 to 5 of 6 activity tests
but responds to single-neuron stimulation almost nothing like a real worm (agreement 0.004 to 0.014,
against 0.087 to 0.121 between real worms), while a model that learns from stimulation matches the
response pattern. A four-ingredient model now
passes both on the atlas worms, but every result so far comes from one lab's preparation, and I have used
all of its worms.

Your DANDI set 000565 is the only public dataset I found that may contain stimulation during
whole-brain imaging with neuron identities. It describes its sessions as "NeuroPAL and calcium imaging of immobilized
worm with optogenetic stimulus", and one file I checked holds about 24 minutes of dF/F for 118 ROIs, some
with neuron names, but the `stimulus` groups in the two files I checked are empty, so I cannot tell when or where light
was delivered. I may well be looking in the wrong place.

**My request:** for those sessions, or any similar recordings you could share, the stimulation onset
times, the targeted neuron (or ROI), and the light parameters. Even a plain table per session would do.
With 12 or more worms I would run the same kind of test as on the atlas: the model recipe frozen,
refitted on some of your worms, scored on the others, with the adjustment for your frame rate (about
1 Hz against the atlas's 2 Hz) registered before I open the activity. The response-pattern comparison
needs no such adjustment. I would keep the data local, credit it, and send
you the results before posting anything. [Optional: co-authorship on a resulting paper, if you would
like it.]

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md (code,
pre-registrations and logs in the same repository; I work with the help of an AI research assistant).

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 3. Flavell lab (MIT)

**To:** Steven Flavell (flavell@mit.edu)
**Subject:** Your freely moving recordings in a benchmark of worm brain models, and one request

Dear Dr Flavell,

I am [your role, e.g. a student at X] and have been building a benchmark for whole-brain models of C. elegans,
scored in units of worm-to-worm variation (pre-registered since early November; the first two results
below are earlier and exploratory). Your lab's data carries much of it, and you may find the results
useful:

- On the copper-boundary recordings (Baskoylu et al. 2026), the model that forecasts best is too typical;
  letting each worm keep more of its own dynamics costs 0.009 R² and brings it onto the real-worm line.
- A closed-loop brain model driving a body in each held-out worm's own copper arena, with copper entering
  only through ASH, passes 9 of 10 pairwise levels and all three arena levels, though model worms still
  spend about four times as long near copper as real worms.
- A model built on the Leifer lab's immobilised, stimulated worms, which passes rest and stimulation
  there, fails on the ongoing activity of your freely moving Atanas et al. worms (1 of 6 activity levels),
  even refitted from scratch. Exploratory diagnosis: in moving worms, coupling between neuron types matters and activity
  is skewed (median skewness 0.83), neither of which the immobilised recipe needs.

So what an artificial worm brain needs may depend on whether the worm is moving, or on the atlas lab's
conditions; I could not yet separate the two. The deciding test needs data that does not seem to be
public: **whole-brain recordings of freely moving worms in which
identified neurons were stimulated optogenetically.** Does your lab have any that could be shared, now or
when published? If not, any further freely moving recordings in the Atanas format beyond DANDI 000776, the
copper set and the 2026 directed-turning recordings on Dryad would still help. I would keep the data local, credit it,
and send you results before posting. [Optional: co-authorship, if you would like it.]

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md (code,
pre-registrations and logs in the same repository; I work with the help of an AI research assistant).

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 4. Häusser lab (UCL)

**To:** Michael Häusser (m.hausser@ucl.ac.uk)
**Subject:** Dalgleish et al. 2020 data: mapping the 200 stimulation targets onto the imaged cells

Dear Professor Häusser,

I am [your role, e.g. a student at X] and have been testing, with pre-registered rules, whether models fitted to
ongoing activity predict responses to targeted stimulation. In C. elegans they do not (agreement with real
worms 0.004 to 0.014, against 0.087 to 0.121 between worms), and I tried the same test in mouse cortex on
the public data of Dalgleish et al. (eLife 2020; figshare 13128950).

One step failed. I could not map the 200 target coordinates onto the imaged cells: under every shift, flip
and scaling I tried, the best alignment put about 20% of targets within 2.5 pixels of a cell, against about
7.5% by chance. Identifying targets from their own responses instead left 7 of 11 sessions usable with 13
to 41 targets each. With that, ongoing co-activity predicted responses better than distance by the
pre-registered rule, but part of what it predicted was trial-locked co-activity also present on catch
trials, and the stimulation-specific part was too weak for a clear test.

**My request:** is there a target-to-cell mapping per session, or a coordinate convention I have missed
(for example, targets in a different image space or plane order)? With it, the test could be run as
intended on your data. I would credit it and send you the results before posting.

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md (code,
pre-registrations and logs in the same repository; I work with the help of an AI research assistant).

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 5. Kimura lab (Nagoya City University), lower priority

**To:** Koutarou D. Kimura (address as published); cc Chentao Wen
**Subject:** More recordings like DANDI 000692, for testing worm brain models across labs

Dear Dr Kimura,

I am [your role, e.g. a student at X] and have been building a benchmark (pre-registered since early November) for whole-brain models of
C. elegans, scored in units of worm-to-worm variation. A model built on the Leifer lab's immobilised worms
passes there but fails on freely moving worms, and I want to know whether it holds in other labs' restrained
worms. Your DANDI set 000692 (spontaneous whole-brain activity of semi-restricted worms with NeuroPAL
identities, about 1.7 Hz) fits the test well, but with 9 recordings from 7 worms it is below the 12 worms
my pre-registered rule requires.

**My request:** do you have further recordings of the same kind that could be shared or deposited? I would
keep them local, credit them, and send you results before posting.

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 6. Yemini lab (UMass Chan), lower priority

**To:** Eviatar Yemini (eviatar.yemini@umassmed.edu)
**Subject:** Longer unstimulated NeuroPAL whole-brain recordings, for testing worm brain models across labs

Dear Dr Yemini,

I am [your role, e.g. a student at X] and have been building a benchmark (pre-registered since early November) for whole-brain models of
C. elegans, scored in units of worm-to-worm variation, and testing whether a model built on one lab's worms
holds in others. The recordings in DANDI 000541 are about 4 minutes each, and my pre-registered test needs
at least about 8 minutes without stimulation per worm, in at least 12 worms.

**My request:** do you have longer unstimulated whole-brain recordings with NeuroPAL identities that could
be shared? I would keep them local, credit them, and send you results before posting.

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 7. Bellec lab (TU Wien), optional

**To:** Guillaume Bellec (address and affiliation as published in Sourmpis et al., eLife 2026)
**Subject:** A worm counterpart to your perturbation result, and comparing on the same data

Dear Dr Bellec,

Your eLife paper with Sourmpis, Petersen and Gerstner shows that generic fitted RNNs predict optogenetic
perturbations poorly in mouse cortex, and that some biological constraints help. I have a related result in
C. elegans, scored animal by animal against worm-to-worm variation: a model fitted to ongoing activity
agrees with real worms' stimulation responses at 0.004 to 0.014 (against 0.087 to 0.121 between worms),
while one that learns from stimulation matches the response pattern. One contrast: a different kind of
constraint, the worm's wiring diagram, did not help the learned causal links.

I am now preparing the same calibrated test in mouse on the optogenetic blocks of the public Allen
Neuropixels sessions. **My request:** is the in vivo dataset from your paper public (I may have missed it on
the Petersen lab's Zenodo page)? Running the same test on it would let the two results be compared on equal
terms. I would credit it and send you results before posting.

The project in one page: https://github.com/Weptune/nematica/blob/main/docs/SUMMARY_FOR_LABS.md.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev
