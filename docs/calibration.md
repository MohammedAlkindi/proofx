# Calibration of annotations

Calibration estimates `P(label = 1 | score)` for a documented annotation task.
For example, a reviewer might label a trajectory that exceeds a prespecified
stopping-time threshold. That label does not represent a counterexample, and
the estimate is not a probability that a conjecture is false.

Supply at least ten rows with finite `near_miss_score` values in `[0, 1]`,
binary `label` values, and at least two examples of each class. Record the
label definition, reviewer procedure, sampling method, and source runs beside
the labelled ledger. Do not mix different conjectures or score definitions.

`calibrate fit` reserves approximately 20% of each class using the supplied
seed. Brier score, log loss, and ten-bin expected calibration error are measured
on that holdout. The saved model uses only the training subset. The final ECE
bin includes probability 1. Reports include training and evaluation counts.

```sh
python -m codebase.cli calibrate fit --ledger labelled.jsonl --method isotonic --seed 42 --output results/calibrator.pkl
python -m codebase.cli calibrate annotate --ledger results/ledger.jsonl --calibrator results/calibrator.pkl
```

Annotated rows retain `calibrated_prob` for compatibility and add
`calibration_target: "user_defined_label_1"`. Load only locally trusted pickle
models; pickle deserialization can execute code.

This split measures performance on held-out rows, not independent research
validation. Related Collatz trajectories can share suffixes, and candidates
from one search can be dependent. A publishable calibration study should split
by run or family, reserve an external evaluation set, report class prevalence,
and inspect sample sizes and uncertainty. Small holdouts are unstable; a low
error on them does not establish generalization.
