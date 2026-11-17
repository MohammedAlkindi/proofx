# Draft correction for the PX-COL-002 preprint

**Applied 17 November 2026** at Mohammed's request. The revised PDF is
`ProofX - Research Preprint (revised 2026-11-17).pdf` in Drive `Research/ProofX/`,
and its source is `ProofX - arXiv source and evidence (revised 2026-11-17).zip` in
`Research/Archive/Collatz and ProofX - originals and source/`. The originals are
unchanged. The revision adds Section 7.4 and its table, and edits the abstract,
introduction, Section 2.2, limitations and conclusion. It builds with TeX Live 2025
with no undefined references. Nothing was uploaded to arXiv.

The text below is the draft the revision was based on. It targets "Finite-prefix selection of long Collatz
trajectories with ProofX" (Drive copy of 10 November 2026), Sections 7.3, 9 and
10. Numbers come from `scripts/research/col002_reanalysis/` run on the
published bundle, and from PX-COL-004.

## Proposed new paragraph for Section 7.3 (after Table 5)

> Total stopping times are small integers with many ties. In the 48 fresh
> strata, the 313th largest value is shared by 306 inputs on average, so
> 5,935 of the 15,024 targets (39.5%) are assigned by the smaller-input
> tie rule. Odd-count, growth and ascending selection also prefer smaller
> inputs on ties, so part of their measured advantage reflects the labelling
> rule. Under tie-fair credit, in which inputs tied at the threshold share the
> remaining target slots equally, the uniform expectation is unchanged. Ascending
> selection's transition-yield ratios fall from 1.243, 1.666 and 1.610 to 1.066,
> 1.136 and 1.072. Growth's become 1.279, 1.319 and 1.293, and odd count's
> 1.314, 1.392 and 1.355. Odd count still exceeds growth on paired seeds, by
> 3.5, 7.6 and 5.7 hits, about half the label-based margin.

## Proposed replacement for the ascending-selection sentences

Section 9 currently says "consecutive size strata do not eliminate local
arithmetic or spatial effects". Section 10 says to "investigate the local
structure exposed by ascending selection". Replace both with:

> Ascending selection's apparent efficiency is mostly an artifact of
> tie-breaking toward smaller inputs. Across twelve further windows the
> lowest-quarter target share averages 0.256 (SD 0.027), with no systematic
> gradient. Target density does vary between windows about 4.5 times more than
> independent sampling would give, because nearby inputs share trajectory
> suffixes. Three windows are therefore weaker evidence than their 300,000
> inputs suggest.

## Proposed addition to Section 10

> A prospective follow-up (PX-COL-004) froze a successive-halving variant:
> screen eight proposals per selection for 16 steps, keep half at 32 and a
> quarter at 64 steps. Tested against the odd-count ablation on 24 fresh windows
> from 3.5e7 to 2.5e11, with tie-fair credit, it had higher yield per charged
> transition in all 24 (median ratio 1.196). Step counts do not price
> overhead, so no wall-time claim follows.

## Context worth one sentence in Section 2.2

> The slope of total stopping time on prefix odd count, 18.2 to 20.4 steps per
> extra odd step, matches the 18.7 implied by the Kontorovich-Lagarias random-walk
> constant converted to the ordinary map. The prefix effect is therefore an
> instance of known drift behavior, not new structure.
