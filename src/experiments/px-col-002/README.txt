PX-COL-002: finite-prefix selection with charged screening

Project: https://proofx.org
Completed 3 November 2026. This is a finite selection study, not a proof of Collatz.
The existing anchor-policy result (PX-COL-001) remains a separate negative result.

Python 3.13.13, NumPy 2.4.6. Install the pinned core dependency, then extract bundle.zip
into a new directory. Scripts use only the standard library and NumPy.

  python -m unittest -v test_policy
  python verify_study.py development
  python verify_study.py test

Reproduce development (writes to a NEW directory; does not overwrite the archive):
  python run_study.py development --output development-reproduced --legacy-reference legacy-reference.csv.gz

Reproduce the frozen fresh evaluation:
  python run_study.py test --output test-reproduced --freeze-commit 52ebace40ca20ca27446172c1dab6ae443f3cd51
The selected inputs and scientific values are deterministic with the pinned
environment. Wall-clock timings and manifests containing timing will differ.
The verifier checks exact arithmetic, selections, quotas, labels and cost counts;
it validates reported timing aggregation but cannot independently recreate elapsed
times. No external mathematical peer review is claimed.

Development code: private research commit 7c6cb199fc48e7896765493a88370065a22bdc79.
Freeze committed/pushed before fresh computation: 52ebace40ca20ca27446172c1dab6ae443f3cd51.
The complete frozen sources, development results and source hashes are included
here so access to the private history is not required for reproduction.

Development selected h=32 from {8,16,32}; oversampling factor fixed at 4.
Fresh starting intervals: 2097152..2197151, 33554432..33654431,
536870912..536970911. Each contains 100000 inputs and 5008 top-stratum targets.
Budgets 64/256/1024; seeds 0..31; seven methods; 2016 policy realizations.

At B=1024 growth mean hits are 121.594 / 112.500 / 107.531, vs exact uniform
expected hits 51.28192. Charged-transition rate ratios are 1.264 / 1.262 / 1.251.
This meets the predeclared all-three-ranges criterion against uniform expectation.
Odd-count ranking performs better in all three ranges. Ascending selection has
higher charged-transition yield in two ranges. Growth's local elapsed times
are higher; no general wall-time speedup is established. All controls and budgets
are retained. The ablation is not promoted to a separately validated new method.

The independent checker recounts 300000 development and 300000 fresh reference
values, 196608 development and 903168 fresh selected records, all ranks and work
charges, plus a deliberately corrupted-record rejection test.

No frozen policy/source hash or scientific result was changed after seeing
fresh outcomes. Reproduction compares scientific values separately from elapsed
times, which depend on hardware and local process scheduling.

The prior million-input table is included as legacy-reference.csv.gz solely to
reproduce development. The historical personal Word/Excel attachments are not
included; no private email is part of this experiment.
Code is covered by the repository MIT license (included). Integer data are
released with the same repository terms. See protocol.md and freeze.json for
the full design and limits.
