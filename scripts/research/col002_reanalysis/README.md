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

Tie-fair credit: inside each stratum, inputs strictly above the 313th largest
total stopping time count 1; inputs equal to it share the remaining target
slots equally. Expected uniform hits are unchanged (313 per stratum).

`policies.py` and the tie-fair numbers use windows whose labels were already
published. They choose what to test next; they are not prospective evidence.
