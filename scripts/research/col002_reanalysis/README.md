# PX-COL-002 reanalysis (2026-11-16)

Post-hoc checks behind `docs/research/2026-11-literature-review.md`. They read the
published bundle and change nothing in it. Extract
`src/experiments/px-col-002/bundle.zip` into a new empty directory, then run each
script from outside that directory with `python -I`:

| Script | Arguments | What it measures |
| --- | --- | --- |
| `ties.py` | bundle dir | Targets decided by the smaller-input tie rule; hits under strict and tie-fair credit |
| `paired.py` | bundle dir, `test` | Charged-transition yield under label and tie-fair credit; paired seed differences |
| `model.py` | bundle dir | Mean total stopping time vs the stochastic-model constant; slope of tau on prefix odd count; within-stratum quartile shares |
| `modelpred.py` | none | Parameter-free random-parity model prediction of odd-count enrichment |
| `gradient.py` | number of windows | Quartile target shares in fresh random windows (spatial heterogeneity) |
| `policies.py` | bundle dir, `test` or `development` | Exploratory policy scan, including successive-halving screening |
| `horner.py` | none | Brute-force check of the sharp ordinary-map Horner bound |
| `gap.py` | windows, seed (30, 4242 used) | Observed vs random-parity-model enrichment in fresh windows at 2^23/27/31 |
| `scatter.py` | windows, directory holding `gap.py` | The same with scattered (non-contiguous) inputs |
| `hybrid.py` | CUT (4, 8, 12, 16 used) | Model walk to 2^CUT, exact tau below |

Tie-fair credit: inside each stratum, inputs strictly above the 313th largest
total stopping time count 1; inputs equal to it share the remaining target
slots equally. Expected uniform hits are unchanged (313 per stratum).

`policies.py` and the tie-fair numbers use windows whose labels were already
published. They choose what to test next; they are not prospective evidence.
