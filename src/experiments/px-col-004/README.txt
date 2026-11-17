PX-COL-004: successive-halving prefix screening versus single-stage odd count.
Protocol: docs/experiments/px-col-004-protocol.md. Python 3.13, NumPy only.

  python -m unittest -v test_study
  python study.py development --output DIR
  python study.py test --output DIR --freeze-commit <freeze SHA>
  python verify.py DIR            (and: python verify.py DIR --corrupt, which must FAIL)

development/ holds the frozen development run. The test run is added after the
freeze commit, together with its verification log and results.
