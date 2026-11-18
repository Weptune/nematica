# DRAFTS, NOT SENT. Emails to labs whose data could unblock NEMATICA (18 Nov 2026)

Sent by the project owner personally, from their own address. Nothing here is sent by Claude.
Fill in the bracketed parts. Addresses are the corresponding-author addresses printed in each lab's
papers or dataset pages; check them before sending. The Leifer email replaces
`atlas_authors_email_DRAFT.md`.

Suggested order of value: 1 Leifer, 2 Kato, 3 Häusser, 4 Flavell, then 5 to 7.

A line worth keeping in every email, because the repository shows it anyway: "I did this work with the
help of an AI research assistant; all code, pre-registrations and logs are public."

---

## 1. Leifer lab (Princeton): new stimulated worms, and the repeat-stimulation decline

To: Andrew Leifer (address as published in Randi et al. 2023)
Subject: Held-out test of a whole-brain worm model on the signal-propagation atlas

Dear Dr Leifer,

I have been using the public signal-propagation atlas (Randi et al. 2023) to test whole-brain models of
C. elegans against worm-to-worm variation, with every test pre-registered. A model built on the 113
wild-type worms now passes both resting activity and responses to stimulation on those worms, but every
public stimulated worm has been used in building it, so I cannot confirm it on unseen animals.

1. Are there stimulated whole-brain recordings beyond the 113 wild-type and 18 unc-31 worms in the OSF
   archive (newer wild-type worms, other strains, or recordings set aside)? Even 15 to 20 unseen worms
   would allow a clean held-out test. I would credit the data in any write-up and share results first.
2. A smaller point you may know already: when the same neuron is stimulated again 0.6 to 2 minutes
   later, its response is about half of the first (56 pairs, 37 worms, gap-matched controls), recovering
   after about 5 minutes, also in unc-31 worms. Is this known for GUR-3/PRDX-2, or is it the neuron?

Code, pre-registrations and results: github.com/Weptune/nematica. A preprint draft is available on
request.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 2. Kato lab (UCSF): stimulation times for DANDI 000565

To: Saul Kato (saul.kato@ucsf.edu); cc Raymond Dunn
Subject: Optogenetic stimulation times for the whole-brain recordings in DANDI 000565

Dear Dr Kato,

I am testing whole-brain models of C. elegans on how they respond to stimulation of single neurons,
measured against worm-to-worm variation. The only public data of this kind is the Leifer lab atlas,
and I have used all of it, so I am looking for stimulation data from a second lab.

Your DANDI set 000565 describes its sessions as "NeuroPAL and calcium imaging of immobilized worm with
optogenetic stimulus", but the `stimulus` groups in the files I checked are empty, so I cannot tell when
or where light was delivered. (The dandiset description also says the calcium data are unstimulated, so
I may be misreading it.)

Could you share the stimulation times and targeted neurons for those sessions, or point me to any
whole-brain recordings with targeted single-neuron stimulation from your lab that could be shared?
I would credit the data, share every result with you before posting, and keep the data local.

Code and pre-registered tests: github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 3. Häusser lab (UCL): target-to-cell mapping in Dalgleish et al. 2020

To: Michael Häusser (m.hausser@ucl.ac.uk)
Subject: Mapping stimulation targets to imaged cells in the Dalgleish et al. 2020 data

Dear Professor Häusser,

I have been using the public data from Dalgleish et al. (eLife 2020, figshare 13128950) to test whether
models fitted to ongoing cortical activity predict responses to targeted stimulation, measured against
animal-to-animal variation.

One step failed: I could not map the 200 target coordinates onto the imaged cells. Under every shift,
flip and scaling I tried, the best alignment put only about 20% of targets within 2.5 pixels of a cell,
against about 7.5% by chance. I therefore had to identify targets from their own responses, which left
too few per session for a clean test.

Is there a target-to-cell mapping (or a coordinate convention I have missed) that you could share or
point me to? With it, the same test could be run properly on your data. I would credit it and share the
results with you first.

Code and pre-registered tests: github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 4. Flavell lab (MIT): freely moving worms with targeted stimulation

To: Steven Flavell (flavell@mit.edu)
Subject: Whole-brain recordings in moving worms with targeted neuron stimulation?

Dear Dr Flavell,

I have been using your public whole-brain recordings of freely moving worms (Atanas et al. 2023) in a
pre-registered benchmark of whole-brain models of C. elegans. A model built on immobilised, stimulated
worms (the Leifer atlas) fails badly on your freely moving worms at rest, which suggests that what an
artificial worm brain needs depends on whether the worm is moving.

To test that properly, I would need whole-brain recordings of freely moving worms in which identified
neurons were stimulated optogenetically. Do any exist in your lab that could be shared, now or when
published? I would also be glad to know whether the heat pulses in some Atanas recordings have a
documented protocol beyond the NWB files.

I would credit any data and share results with you first. Code and pre-registrations:
github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 5. Kimura lab (Nagoya City University): more semi-restricted recordings (lower priority)

To: Koutarou D. Kimura (address as published); cc Chentao Wen
Subject: More whole-brain recordings like DANDI 000692?

Dear Dr Kimura,

I am testing whole-brain models of C. elegans on worms from labs other than the one they were built on.
Your DANDI set 000692 (spontaneous whole-brain activity in semi-restricted worms with NeuroPAL identities)
is close to ideal, but with 9 recordings from 7 worms it falls below the 12 worms my pre-registered test
needs. Do you have further recordings of the same kind that could be shared or deposited? I would credit
them and share results first.

Code and pre-registrations: github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 6. Yemini lab (UMass Chan): longer unstimulated recordings (lower priority)

To: Eviatar Yemini (eviatar.yemini@umassmed.edu)
Subject: Longer unstimulated whole-brain recordings with NeuroPAL identities?

Dear Dr Yemini,

I am testing whole-brain models of C. elegans on worms from several labs, scored against worm-to-worm
variation. The NeuroPAL recordings in DANDI 000541 are about 4 minutes each, and my pre-registered test
needs at least about 8 minutes without stimulation per worm. Do you have longer unstimulated whole-brain
recordings with NeuroPAL identities that could be shared? I would credit them and share results first.

Code and pre-registrations: github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev

---

## 7. Bellec lab (TU Wien): comparing on the same data (optional)

To: Guillaume Bellec (address as published in Sourmpis et al., eLife 2026)
Subject: Calibrated comparison of fitted networks under optogenetic perturbation

Dear Dr Bellec,

Your eLife paper with Sourmpis, Petersen and Gerstner shows that generic fitted RNNs predict optogenetic
perturbations poorly in mouse cortex. I have found a related result in C. elegans, scored animal by animal
against worm-to-worm variation, and I am preparing the same test in mouse using the optogenetic block of the
public Allen Neuropixels sessions.

Is the in vivo dataset from your paper available (I may have missed it on the Petersen lab's Zenodo
page)? Running the same calibrated test on it would let the two results be compared directly. I would
credit it and share results first.

Code and pre-registrations: github.com/Weptune/nematica.

Best wishes,
Abhinav Krishna
[affiliation] · weptune.dev
