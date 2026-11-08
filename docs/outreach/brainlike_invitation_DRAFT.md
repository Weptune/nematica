# DRAFT, not sent: invitation to submit to the brain-likeness test

Status: draft for the project owner. Nothing here has been sent. Fill in the site address once it is hosted.

**Who it is for:** groups that build whole-brain or circuit models of *C. elegans* (data-driven, connectome-based,
biophysical), groups building neuromorphic or spiking systems, and people working on brain-inspired recurrent
architectures. Candidates to consider: the authors of the published models already scored in the project
(Creamer, Leifer and Pillow; Kunert, Shlizerman and Kutz), whole-worm simulation projects (OpenWorm, BAAIWorm),
and whole-brain imaging labs who may want to see their own models placed. Pick names and addresses yourself.

---

**Subject:** A perturbation test for how brain-like a network is, built on the signal propagation atlas

Hello [name],

I have been working on a question that I think overlaps with your work: what measurably differentiates
artificial neural networks from real ones. As part of it I built an open test that places any network relative
to real *C. elegans* nervous systems, using the signal propagation atlas (Randi et al. 2023).

The test reruns the atlas experiment on the submitted system: 30 runs of about 32 minutes, a 2 s push to one
unit every 30 s, the same measurement noise for every system. It measures eight signatures (how few patterns
resting activity uses, how much of it is slow, how strongly units move together, timescale, how widely a push
spreads beyond ongoing change, how much a push stands out, tiring on a second push, and how well a model built
only from watching predicts the push responses) and reports each against the range spanned by groups of real
worms.

Calibration: groups of real worms the reference never saw sit at a distance of 0.36 to 0.65 from the
real-worm median; a worm emulator fitted to the atlas at 0.86 to 1.08; a network with hidden slow drives at
the worm's timescale at 2.37 and a small trained transformer at 2.48; untrained recurrent, spiking, gated and
transformer networks at 3.8 to 5.4. The distance ranking was chosen after seeing these results, so the first
submitted systems are its first real test.

Any system can take it: rate-network weights, a recurrent model exported to ONNX (any internal state), Python
run locally, or, for systems on special hardware or in a lab, recordings made by following a published schedule.
Nothing about the model has to be shared beyond what it needs to run. The site is [address]; the code and the full
pre-registered log are at github.com/Weptune/nematica.

If you have a model you would be willing to put through it, I would be glad to help with the export, and I would
value your view on whether the signatures measure what they should.

Best,
Abhinav Krishna
