# DRAFT, NOT SENT. Email to the signal-propagation atlas authors (8 Nov 2026)

Nothing here is sent without the project owner's explicit go-ahead.

To: Andrew Leifer (corresponding author, Randi et al. 2023; address as published in the paper)
Subject: Repeat stimulations in the signal-propagation atlas recover over ~5 min: actuator or neuron?

Dear Dr Leifer,

I have been using the public signal-propagation atlas (Randi et al. 2023) to benchmark whole-brain
models of C. elegans, and found something in the data that you may already know about, or may want to.

When the same neuron is stimulated again within 2 minutes, its own response is about 40% of its
first response (gap-matched controls subtracted; 81 pairs, 47 worms). After 2 to 5 minutes it is
about 64%, and by 5 to 10 minutes it has recovered. About 40% of repeat stimulations of a neuron in
the atlas fall within 5 minutes of the previous one. The decline is as large in the unc-31 recordings,
so it does not seem to need dense-core-vesicle release.

What I cannot settle from the atlas is whether this is the GUR-3/PRDX-2 actuator desensitising or
the neuron itself. Two pre-registered attempts to separate light from the activity it causes failed
their checks on synthetic data: every direct stimulation delivers both. There is a modest hint that
activity without light also lowers a neuron's next response (about 10% per SD of drive from other
neurons), so probably both contribute.

Two questions:
1. Have you seen this decline, or a recovery time for GUR-3/PRDX-2, in your own characterisation
   (for example, repeated stimulation of one neuron at fixed intervals)?
2. Would an experiment along these lines be feasible in your setup: drive a neuron strongly through
   its inputs without light on it, then stimulate it with light, against light followed by light
   at matched activity? That would separate the actuator from the neuron directly.

The analysis, pre-registration and code are public (github.com/Weptune/nematica; the relevant
section is "Light or activity: what tires a worm neuron?"), and I am writing up the benchmark as a
preprint. I would be glad to share anything that is useful.

Best wishes,
Abhinav Krishna
weptune.dev
