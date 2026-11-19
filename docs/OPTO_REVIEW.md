# Study O: independent review before freeze (19 Nov 2026, 18:20 UTC)

Reviewer: a separate Claude agent that had not seen the work being produced, given the registration, the
amendments A1 to A9 and the code; told not to read any data or run the real test. Summary of its
findings, with what was done about each (A10 in docs/OPTO.md).

**Code that would have made the result wrong**
1. Copies and profile in different units: the profile is in per-unit spontaneous-SD units, the copies'
   predictions in class-mean z units, so each class had its own scale and Pearson r could mislead. *Fixed
   (A10.1).*
2. NaN agreements would silently turn claims into "not supported". *Fixed (A10.2).*
3. O3's "10 of 13" became "10 of however many are left". *Fixed as a fraction (A10.3).*
4. The ceiling is a raw split-half r; a perfect copy can only reach sqrt(2c/(1+c)), so in noisy mice the
   gap was inflated (up to 1.6x), in O4's favour. *Fixed (A10.4).*
5. Fine as written: class remapping, tagging rule, onsets and baseline bins, class order, pairing within
   line, FIR construction; the FROZEN guard fails closed.

**Code vs text**: classes absent from wild-type mice were unhandled (*A10.5*); "at least 0.45 s" is 0.44 s
in one wild-type mouse (*corrected*); units with no area, "grey" or "root" made meaningless classes
(*A10.6*).

**Design**
- Most serious: O4 can be supported without silent links if W is simply the wrong kind of model for real
  cortex (shared state, more than one lag, nonlinearity, untagged cells driven directly by the light,
  state drift between the spontaneous blocks and the end-of-session light block). The calibration's
  visible-links generator lies inside W's own model class. *Addressed by a misspecified-visible
  calibration population, a W positive control at rest, and robustness runs (A10.7 to A10.9).*
- The 10 Hz train is close to the test condition; report how well its own profile predicts the test
  profile as a trivial baseline (*A10.10*).
- Light artefacts could tag units: run tagging on the wild-type mice (*A10.11*).
- Calibration used one draw per condition, so false-positive rates were never estimated (*A10.12*).
- The amendments are tuning on synthetic data (threshold 3 to 4, primary claim switched to O4, thresholds
  picked from pilots, two analysis changes after calibration failures). Defensible since no real response
  was read, but the write-up must say so, and must frame O4 as "the copy fitted at rest fails under
  drive", not as proof of silent links; O4 also drops the between-mouse comparison the question was built
  on. *Accepted; framing rule in A10.13.*
